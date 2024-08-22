import asyncio
import logging
import traceback

import aiofiles
import fsspec
import grpc
from fsspec.asyn import AbstractAsyncStreamedFile, AsyncFileSystem
from fsspec.spec import AbstractBufferedFile

from union.filesystems._async_utils import mirror_sync_methods
from union.filesystems._endpoint import _create_channel
from union.internal.common import list_pb2
from union.internal.objectstore.definition_pb2 import Key, Metadata, Object
from union.internal.objectstore.metadata_service_pb2_grpc import MetadataStoreServiceStub
from union.internal.objectstore.payload_pb2 import (
    DeleteRequest,
    GetRequest,
    GetResponse,
    HeadRequest,
    HeadResponse,
    ListRequest,
    ListResponse,
    MetadataResponse,
    PutRequest,
)

_DEFAULT_LOGGER = logging.getLogger(__name__)


_FS_PREFIX = "unionmeta://"

# Shorter default protocol for unionmeta
_FS_PREFIX_SHORT = "ums://"


def _prefix_path(path: str) -> str:
    if path.startswith(_FS_PREFIX):
        return path

    if path.startswith(_FS_PREFIX_SHORT):
        return path

    return f"{_FS_PREFIX}{path.rstrip('/')}"


class AsyncUnionMetaFS(AsyncFileSystem):
    mirror_sync_methods = False
    cachable = False

    def __init__(self, logger: logging.Logger = _DEFAULT_LOGGER, *args, **kwargs):
        channel = _create_channel()
        self._client = MetadataStoreServiceStub(channel)
        loop = channel._loop
        asyncio.set_event_loop(loop)
        asyncio.events.set_event_loop(loop)
        super().__init__(loop=loop, *args, **kwargs)
        self._loop = loop
        self._metadata = None
        self.blocksize = 2**18  # 2MB
        self._logger = logger
        mirror_sync_methods(self)

    def _prefix_path(self, path):
        if path.startswith(f"{self.protocol}://"):
            return path
        return f"{self.protocol}://{path}"

    async def _ensure_metadata(self) -> MetadataResponse:
        if self._metadata is not None:
            return self._metadata

        self._metadata = await self._client.Metadata(Metadata())
        return self._metadata

    async def _rm_file(self, path, **kwargs):
        path = self._prefix_path(path)
        self._logger.info(f"Deleting {path}")
        await self._client.Delete(DeleteRequest(key=Key(key=path)))

    async def _cp_file(self, path1, path2, **kwargs):
        # TODO: Implement cp in remote metadata store
        _, temp_filename = await aiofiles.tempfile.TemporaryFile(suffix=".yaml")
        await self._get_file(path1, temp_filename, **kwargs)
        await self._put_file(temp_filename, path2, **kwargs)

    async def _pipe_file(self, path, value, **kwargs):
        path = self._prefix_path(path)
        req = PutRequest(metadata=Metadata(), key=Key(key=path), object=Object(contents=value))
        try:
            await self._client.Put(req)
        except Exception as e:
            traceback.print_exception(e)
            raise

    async def _cat_file(self, path, start=None, end=None, **kwargs):
        path = self._prefix_path(path)
        req = GetRequest(key=Key(key=path))
        try:
            res: GetResponse = await self._client.Get(req)
            return res.object.contents
        except grpc.RpcError as e:
            if e.code() == grpc.StatusCode.NOT_FOUND:
                raise FileNotFoundError(path)
            traceback.print_exception(e)
            raise e
        except Exception as e:
            traceback.print_exception(e)
            raise

    async def _put_file(self, lpath, rpath, **kwargs):
        rpath = self._prefix_path(rpath)
        async with aiofiles.open(lpath, "rb") as f:
            await self._pipe_file(rpath, await f.read(), **kwargs)

    async def _get_file(self, rpath, lpath, **kwargs):
        rpath = self._prefix_path(rpath)
        async with aiofiles.open(lpath, "wb") as f:
            await f.write(await self._cat_file(rpath, **kwargs))

    async def _info(self, path, **kwargs):
        self._logger.info(f"Info: {path}")
        path = self._prefix_path(path)
        req = HeadRequest(key=Key(key=path))
        try:
            res: HeadResponse = await self._client.Head(req)
        except grpc.RpcError as e:
            if e.code() == grpc.StatusCode.NOT_FOUND:
                # If there is no key at that location, check if it's a prefix
                nested_keys = await self._ls(path=path, detail=False)
                if len(nested_keys) > 0:
                    return {
                        "name": path,
                        "type": "directory",
                        "size": 0,
                        "StorageClass": "DIRECTORY",
                    }
                raise FileNotFoundError(path)
            traceback.print_exception(e)
            raise
        except Exception as e:
            traceback.print_exception(e)
            raise

        return {
            "size": res.size_bytes,
            "etag": res.etag,
            "tags": res.metadata.tag if res.metadata and res.metadata.tag else {},
            "type": "file",
        }

    async def _ls(self, path, detail=True, **kwargs):
        path = self._prefix_path(path)
        if not path.endswith("*"):
            path = f"{path}*"

        req = ListRequest(
            request=list_pb2.ListRequest(
                limit=1000,
                filters=[
                    list_pb2.Filter(
                        field="prefix",
                        function=list_pb2.Filter.GREATER_THAN_OR_EQUAL,
                        values=[path],
                    )
                ],
            )
        )

        items = []
        while True:
            res: ListResponse = await self._client.List(req)
            for k in res.keys:
                items.append(
                    {
                        "name": k.key,
                        "type": "file",
                        # The API doesn't return information about the object sizes for now.
                        "size": 0,
                    }
                )
            for d in res.directories:
                items.append(
                    {
                        "name": d.key,
                        "type": "directory",
                        # The API doesn't return information about the object sizes for now.
                        "size": 0,
                    }
                )
            if not res.next_token or res.next_token == "":
                break

        return items

    async def open_async(self, path: str, mode="rb", **kwargs) -> AbstractAsyncStreamedFile:
        if "b" not in mode or kwargs.get("compression"):
            raise ValueError
        path = self._prefix_path(path)
        self._logger.debug(f"Opening file async: {path}")
        m = await self._ensure_metadata()
        return AsyncUnionStreamFile(self, self._client, path, mode, block_size=m.max_part_size_bytes, **kwargs)

    def _open(
        self,
        path,
        mode="rb",
        block_size=None,
        autocommit=True,
        cache_options=None,
        **kwargs,
    ):
        if "b" not in mode or kwargs.get("compression"):
            raise ValueError
        path = _prefix_path(path)
        self._logger.debug(f"Opening file: {path}")
        m = self.loop.run_until_complete(self._ensure_metadata())
        return UnionStreamFile(
            self._client,
            fs=self,
            path=path,
            mode=mode,
            block_size=m.max_part_size_bytes,
            autocommit=autocommit,
            cache_options=cache_options,
            **kwargs,
        )


class AsyncUnionStreamFile(AbstractAsyncStreamedFile):
    """
    AsyncUnionStreamFile implements the AbstractAsyncStreamedFile interface for the UnionMetaFS.
    It can be used to read and write files using async.io apis.
    """

    def __init__(
        self,
        fs: AsyncUnionMetaFS,
        object_store_client: MetadataStoreServiceStub,
        path: str,
        mode: str,
        **kwargs,
    ):
        super().__init__(fs, path, mode, **kwargs)
        self._client = object_store_client
        self._part_number = 1
        self._bytes = b""

    async def _fetch_range(self, start: int, end: int) -> bytes:
        if not self._bytes:
            get_response = await self._client.Get(GetRequest(key=Key(key=_prefix_path(self.path))))
            self._bytes = get_response.object.contents

        return self._bytes[start:end]

    async def _initiate_upload(self):
        if self.autocommit and self.tell() < self.blocksize:
            # only happens when closing small file, use on-shot PUT
            return

        raise ValueError("The file is too big to be uploaded to union meta store. Please use a smaller file.")

    async def _upload_chunk(self, final: bool = False):
        if self.autocommit and final and self.tell() < self.blocksize:
            # only happens when closing small file, use on-shot PUT
            self.buffer.seek(0, 0)
            await self._client.Put(
                PutRequest(key=Key(key=_prefix_path(self.path)), object=Object(contents=self.buffer.getvalue()))
            )
            return True


class UnionStreamFile(AbstractBufferedFile):
    def __init__(
        self,
        client: MetadataStoreServiceStub,
        fs: AsyncUnionMetaFS,
        path,
        mode="rb",
        block_size="default",
        autocommit=True,
        cache_type="readahead",
        cache_options=None,
        size=None,
        **kwargs,
    ):
        super().__init__(
            fs,
            path,
            mode,
            block_size,
            autocommit,
            cache_type,
            cache_options,
            size,
            **kwargs,
        )
        self._client = client
        self._bytes = b""

    def _upload_chunk(self, final=False):
        if self.autocommit and final and self.tell() < self.blocksize:
            # only happens when closing small file, use on-shot PUT
            self.buffer.seek(0, 0)
            self.fs.loop.run_until_complete(
                self._client.Put(
                    PutRequest(key=Key(key=_prefix_path(self.path)), object=Object(contents=self.buffer.getvalue()))
                )
            )
            return True

    def _initiate_upload(self):
        if self.autocommit and self.tell() < self.blocksize:
            # only happens when closing small file, use on-shot PUT
            return

        raise ValueError("The file is too big to be uploaded to union meta store. Please use a smaller file.")

    def _fetch_range(self, start, end):
        if not self._bytes:
            get_response = self.fs.loop.run_until_complete(
                self._client.Get(GetRequest(key=Key(key=_prefix_path(self.path))))
            )
            self._bytes = get_response.object.contents

        return self._bytes[start:end]


fsspec.register_implementation(name="unionmeta", cls=AsyncUnionMetaFS, clobber=True)

# Shorter default protocol for unionmeta
fsspec.register_implementation(name="ums", cls=AsyncUnionMetaFS, clobber=True)
