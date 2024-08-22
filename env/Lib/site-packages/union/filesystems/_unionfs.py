import asyncio
import collections.abc
import gc
import io
import logging
import math
import os
import shutil
import typing
from asyncio import StreamReader
from random import random
from typing import Optional

import aiofiles
import fsspec
import grpc
from aiofiles.threadpool.binary import AsyncBufferedReader
from flytekit.core.utils import timeit
from fsspec.asyn import AbstractAsyncStreamedFile, AsyncFileSystem
from fsspec.callbacks import _DEFAULT_CALLBACK
from fsspec.spec import AbstractBufferedFile

from union.filesystems._async_utils import if_coro, mirror_sync_methods
from union.filesystems._endpoint import _create_channel
from union.internal.common import list_pb2
from union.internal.objectstore.definition_pb2 import (
    Key,
    Metadata,
    Object,
)
from union.internal.objectstore.objectstore_service_pb2_grpc import (
    ObjectStoreServiceStub,
)
from union.internal.objectstore.payload_pb2 import (
    DeleteRequest,
    DownloadPartRequest,
    GetRequest,
    HeadRequest,
    HeadResponse,
    ListRequest,
    ListResponse,
    MetadataResponse,
    PutRequest,
    StartMultipartUploadRequest,
    SuccessfulUploadRequest,
    TerminateMultipartUploadRequest,
    UploadPartRequest,
    UploadPartResponse,
)

_DEFAULT_LOGGER = logging.getLogger(__name__)

_FS_PREFIX = "union://"

# Shorter default protocol for unionfs
_FS_PREFIX_SHORT = "ufs://"


def _prefix_path(path: str) -> str:
    if path.startswith(_FS_PREFIX):
        return path

    if path.startswith(_FS_PREFIX_SHORT):
        return path
    return f"{_FS_PREFIX}{path.rstrip('/')}"


async def _fetch_range(client: ObjectStoreServiceStub, max_attempts: int, path: str, start: int, end: int) -> bytes:
    out = io.BytesIO()
    attempt = 0
    path = _prefix_path(path)
    while True:
        try:
            async for resp in client.DownloadPart(
                DownloadPartRequest(key=Key(key=path), start_pos=start, size_bytes=end - start)
            ):
                chunk_contents = resp.object.contents
                out.write(chunk_contents)
            return out.getvalue()
        except grpc.RpcError as e:
            if e.Code() == grpc.StatusCode.RESOURCE_EXHAUSTED:
                attempt += 1
            last_exception = e

        if attempt > max_attempts:
            raise last_exception
        else:
            # TODO(haytham): Make configurable
            await asyncio.sleep(math.pow(2, attempt) * 10 * (random() + 0.5))  # exponential backoff of 10s to 30s


class AsyncUnionFS(AsyncFileSystem):
    mirror_sync_methods = False
    async_impl = True
    cachable = False
    _metadata: Optional[MetadataResponse] = None

    def __init__(self, logger: logging.Logger = _DEFAULT_LOGGER, *args, **kwargs):
        channel = _create_channel()
        self._client = ObjectStoreServiceStub(channel)
        loop = channel._loop
        asyncio.set_event_loop(loop)
        asyncio.events.set_event_loop(loop)
        if kwargs.get("batch_size") is None:
            batch_size = self.max_concurrent_tasks
        else:
            batch_size = kwargs["batch_size"]
        super().__init__(loop=loop, batch_size=batch_size, *args, **kwargs)
        self._loop = loop
        self._metadata = None
        self.blocksize = 2**18  # 2MB
        self._logger = logger
        mirror_sync_methods(self)

    @property
    def retries(self) -> int:
        return 3

    @property
    def max_concurrent_tasks(self) -> int:
        return 10

    @property
    def max_attempts(self) -> int:
        return 3

    async def _ensure_metadata(self) -> MetadataResponse:
        if self._metadata is not None:
            return self._metadata

        self._metadata = await self._client.Metadata(Metadata())
        return self._metadata

    async def _rm_file(self, path: str, **kwargs):
        path = _prefix_path(path)
        self._logger.debug(f"Deleting {path}")
        self._client.Delete(DeleteRequest(key=Key(key=path)))

    async def _cp_file(self, path1: str, path2: str, **kwargs):
        raise NotImplementedError("cp_file is not supported for UnionFS")

    async def _get_file(self, rpath: str, lpath: str, callback=_DEFAULT_CALLBACK, **kwargs):
        if os.path.isdir(lpath):
            return
        rpath = _prefix_path(rpath)
        self._logger.debug(f"Getting file async: {rpath}")
        metadata = await self._ensure_metadata()

        head_resp = await self._client.Head(HeadRequest(key=Key(key=rpath)))
        callback.set_size(head_resp.size_bytes)

        if head_resp.size_bytes <= metadata.max_single_part_object_size_bytes:
            # Download the whole file
            resp = await self._client.Get(GetRequest(key=Key(key=rpath)))
            async with aiofiles.open(lpath, "wb") as f0:
                await f0.write(resp.object.contents)
            callback.relative_update(head_resp.size_bytes)
            return

        # Directory to store downloaded chunks
        output_directory = f"{lpath}.chunks"

        # Create the output directory if it doesn't exist
        os.makedirs(output_directory, exist_ok=True)

        # num_chunks is the number of chunks that the file is split into. It'll be used to name the files
        num_chunks = math.ceil(head_resp.size_bytes / metadata.max_part_size_bytes)

        semaphore = asyncio.Semaphore(self.max_concurrent_tasks)

        async def _download_chunks(start_pos: int = 0, size_bytes: int = -1) -> collections.abc.AsyncIterable[bytes]:
            async for resp in self._client.DownloadPart(
                DownloadPartRequest(key=Key(key=rpath), start_pos=start_pos, size_bytes=size_bytes)
            ):
                chunk_contents = resp.object.contents
                yield chunk_contents
                callback.relative_update(len(chunk_contents))

        async def _download_part(part_number: int = 0):
            file_path = os.path.join(output_directory, f"chunk_{part_number}.dat")
            async with aiofiles.open(file_path, "wb") as local_file:
                async with semaphore:
                    async for chunk in _download_chunks(
                        start_pos=part_number * metadata.max_part_size_bytes,
                        size_bytes=metadata.max_part_size_bytes,
                    ):
                        await local_file.write(chunk)

        # Download and save each chunk to a separate file
        out = []
        for chunk_id in range(0, num_chunks):
            out.append(_download_part(part_number=chunk_id))

        await asyncio.gather(*out)

        # Merge the downloaded chunks into a single file
        async with aiofiles.open(lpath, "wb") as merged_file:
            for chunk_id in range(0, num_chunks):
                file_path = os.path.join(output_directory, f"chunk_{chunk_id}.dat")
                async with aiofiles.open(file_path, "rb") as chunk_file:
                    await merged_file.write(await chunk_file.read())

        # TODO: Delete the downloaded chunks
        # TODO: Logging
        self._logger.debug(f"Merged file saved: {lpath}")
        shutil.rmtree(output_directory)

    async def _cat_file(
        self,
        path: str,
        start: Optional[int] = None,
        end: Optional[int] = None,
        **kwargs,
    ):
        path = _prefix_path(path)
        metadata = await self._ensure_metadata()

        head_resp = await self._client.Head(HeadRequest(key=Key(key=path)))
        if head_resp.size_bytes <= metadata.max_single_part_object_size_bytes:
            # Download the whole file
            resp = await self._client.Get(GetRequest(key=Key(key=path)))
            return resp.object.contents

        if start is None and end is None:
            # Download the whole file
            # TODO: Check file size to decide if we should do multipart download
            resp = await self._client.Get(GetRequest(key=Key(key=path)))
            return resp.object.contents

        raise "Not implemented"

    async def _pipe_file(self, path: str, data: bytes, callback=_DEFAULT_CALLBACK, **kwargs):
        path = _prefix_path(path)
        ret = await self._upload_data(path, io.BytesIO(data), size=len(data), callback=callback)
        gc.collect()
        return ret

    @timeit("Upload a single part")
    async def _upload_chunk(
        self,
        operation_id: str,
        rpath: str,
        chunk: typing.Union[io.BytesIO, StreamReader, AsyncBufferedReader],
        max_upload_size: int,
        part_number: int,
        callback=_DEFAULT_CALLBACK,
    ) -> (UploadPartResponse, bool):
        rpath = _prefix_path(rpath)
        while True:
            attempt = 0
            try:
                result = await self._client.UploadPart(
                    upload_part_request_iter(
                        operation_id=operation_id,
                        key=rpath,
                        buffer=chunk,
                        block_size=self.blocksize,
                        max_upload_size=max_upload_size,
                        logger=self._logger,
                        part_number=part_number,
                        callback=callback,
                    )
                )
                return result, False
            except grpc.RpcError as e:
                self._logger.warning(f"UploadPart: Failed [{e.code()}]. Error: {e.details()}")
                attempt += 1
                last_exception = e
            except EOFError:
                self._logger.warning("UploadPart: EOFError. Returning...")
                return None, True
            except Exception:
                return None, True
            except asyncio.CancelledError:
                return None, True

            if attempt > self.max_attempts:
                self._logger.error("UploadPart: Max attempts reached. Raising exception...")
                raise last_exception
            else:
                # TODO(haytham): Make configurable
                sleep_time = math.pow(2, attempt) * 10 * (random() + 0.5)
                self._logger.warning(f"UploadPart: Retrying in {sleep_time} seconds...")
                await asyncio.sleep(sleep_time)  # exponential backoff of 10s to 30s

    async def _upload_data(
        self,
        path: str,
        data: typing.Union[io.BytesIO, StreamReader, AsyncBufferedReader],
        size: int,
        callback=_DEFAULT_CALLBACK,
    ):
        path = _prefix_path(path)
        metadata = await self._ensure_metadata()

        if size <= metadata.max_single_part_object_size_bytes:
            self._logger.debug("Uploading a single part")
            await self._client.Put(
                PutRequest(
                    key=Key(key=path),
                    object=Object(contents=await if_coro(data.read())),
                )
            )
            callback.relative_update(size)
            return

        self._logger.debug("Uploading a large object")
        resp = await self._client.StartMultipartUpload(
            StartMultipartUploadRequest(
                key=Key(key=path),
                metadata=Metadata(),
            )
        )

        out = []
        part_number = 0

        async def upload_chunks():
            nonlocal part_number
            while True:
                part_number += 1
                self._logger.debug(f"Uploading {path}: part {part_number}")
                # Do not await here, just append the task to the list and we will await all of them later
                upload_task, done = await self._upload_chunk(
                    operation_id=resp.operation_id,
                    rpath=path,
                    chunk=data,
                    max_upload_size=metadata.max_part_size_bytes,
                    part_number=part_number,
                    callback=callback,
                )
                if done:
                    break
                out.append(upload_task)

            # out.extend(await asyncio.gather(*tasks))  # Wait for all upload tasks to complete

        await upload_chunks()

        # part numbers are 1-based
        parts = {o.etag: i + 1 for i, o in enumerate(out)}

        if len(parts) == 0:
            if size > 0:
                raise ValueError(f"No parts uploaded, but size is not zero [{size}]")
            self._logger.debug("No parts uploaded, returning")
            return

        await self._client.TerminateMultipartUpload(
            TerminateMultipartUploadRequest(
                operation_id=resp.operation_id,
                key=Key(key=path),
                successful_upload=SuccessfulUploadRequest(
                    etags_parts=parts,
                ),
            )
        )

    async def _put_file(self, lpath: str, rpath: str, callback=_DEFAULT_CALLBACK, **kwargs):
        if os.path.isdir(lpath):
            raise ValueError("Can't upload a directory")

        rpath = _prefix_path(rpath)
        size = os.path.getsize(lpath)
        callback.set_size(size)
        self._logger.debug(f"Uploading file: {lpath}")
        async with aiofiles.open(lpath, "rb") as f0:
            ret = await self._upload_data(path=rpath, data=f0, size=size, callback=callback)
            gc.collect()
            return ret

    async def _info(self, path: str, **kwargs):
        path = _prefix_path(path)
        req = HeadRequest(key=Key(key=path))
        try:
            res: HeadResponse = await self._client.Head(req)
        except grpc.RpcError as e:
            if e.code() == grpc.StatusCode.NOT_FOUND:
                # If there is no key at that location, check if it's a prefix
                nested_keys = await self._ls(path=path, detail=False)
                self._logger.debug(f"Nested Keys: {len(nested_keys)}")
                if len(nested_keys) > 0:
                    return {
                        "name": path,
                        "type": "directory",
                        "size": 0,
                        "StorageClass": "DIRECTORY",
                    }
                raise FileNotFoundError(path)
            raise
        return {
            "size": res.size_bytes,
            "etag": res.etag,
            "tags": res.metadata.tag if res.metadata and res.metadata.tag else {},
            "type": "file",
        }

    async def _ls(self, path: str, detail: bool = True, **kwargs):
        self._logger.debug(f"Listing: {path}")
        has_prefix = path.startswith(_FS_PREFIX)
        path = _prefix_path(path)
        if path.endswith("*"):
            path = path.strip("*")

        if not path.endswith("/"):
            # Ensure we have a trailing prefix as in fsspec/gcsfs
            # https://github.com/fsspec/gcsfs/blob/5cb4479b0ac9737ed99b906befc88c9250cbd21c/gcsfs/core.py#L611
            path = path + "/"

        req = ListRequest(
            request=list_pb2.ListRequest(
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
                        "name": k.key if has_prefix else k.key[len(_FS_PREFIX) :],
                        "type": "file",
                        # The API doesn't return information about the object sizes for now.
                        "size": 0,
                    }
                )
            for d in res.directories:
                items.append(
                    {
                        "name": d.key if has_prefix else d.key[len(_FS_PREFIX) :],
                        "type": "directory",
                        # The API doesn't return information about the object sizes for now.
                        "size": 0,
                    }
                )

            if not res.next_token or res.next_token == "":
                break
            req.request.token = res.next_token
        self._logger.debug(f"Items from ls: {items}")
        return items

    async def open_async(self, path: str, mode="rb", **kwargs) -> AbstractAsyncStreamedFile:
        if "b" not in mode or kwargs.get("compression"):
            raise ValueError
        path = _prefix_path(path)
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


async def upload_part_request_iter(
    logger: logging.Logger,
    operation_id: str,
    key: str,
    buffer: typing.Union[StreamReader, AsyncBufferedReader],
    part_number: int,
    max_upload_size: int,
    callback=_DEFAULT_CALLBACK,
    block_size: int = 2**24,  # 16MB
) -> UploadPartRequest:
    total_read = 0
    while total_read < max_upload_size:
        raw = await if_coro(buffer.read(block_size))
        if not raw or len(raw) == 0:
            if total_read == 0:
                raise EOFError("No data to upload")
            return
        callback.relative_update(len(raw))
        req = UploadPartRequest(
            operation_id=operation_id,
            key=Key(key=key),
            part_number=part_number,
            object=Object(contents=raw),
        )
        yield req
        total_read += len(raw)
    logger.debug(f"Uploaded: {total_read}")


class AsyncUnionStreamFile(AbstractAsyncStreamedFile):
    """
    AsyncUnionStreamFile implements the AbstractAsyncStreamedFile interface for the UnionFS.
    It can be used to read and write files using async.io apis.
    """

    def __init__(
        self,
        fs: AsyncUnionFS,
        object_store_client: ObjectStoreServiceStub,
        path: str,
        mode: str,
        **kwargs,
    ):
        super().__init__(fs, path, mode, **kwargs)
        self._client = object_store_client
        self._part_number = 1

    async def _fetch_range(self, start: int, end: int) -> bytes:
        return await _fetch_range(self._client, self.fs.max_attempts, _prefix_path(self.path), start, end)

    async def _initiate_upload(self):
        resp = await self._client.StartMultipartUpload(
            StartMultipartUploadRequest(key=Key(key=_prefix_path(self.path)), metadata=None)
        )

        self._operation_id = resp.operation_id

    async def _upload_chunk(self, final: bool = False):
        metadata = await self.fs._ensure_metadata()
        await self._client.UploadPart(
            upload_part_request_iter(
                operation_id=self._operation_id,
                logger=self.fs._logger,
                key=_prefix_path(self.path),
                buffer=self.buffer,
                max_upload_size=metadata.max_part_size_bytes,
                block_size=self.blocksize,
                part_number=self._part_number,
            )
        )
        self._part_number = self._part_number + 1
        return True


class UnionStreamFile(AbstractBufferedFile):
    def __init__(
        self,
        client: ObjectStoreServiceStub,
        fs: AsyncUnionFS,
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
        self._part_number = 1
        self._parts = {}
        self._operation_id = ""
        self._upload_initiated = False

    def _upload_chunk(self, final=False):
        async def internal():
            metadata = await self.fs._ensure_metadata()
            # buffer is at the last byte written, we need to seek to 0 to start uploading.
            await if_coro(self.buffer.seek(0))
            return await self._client.UploadPart(
                upload_part_request_iter(
                    operation_id=self._operation_id,
                    logger=self.fs._logger,
                    key=_prefix_path(self.path),
                    buffer=self.buffer,
                    max_upload_size=metadata.max_part_size_bytes,
                    block_size=self.blocksize,
                    part_number=self._part_number,
                )
            )

        self.fs._logger.debug(f"Uploading chunk {self._part_number}")
        resp = self.fs.loop.run_until_complete(internal())
        self._parts[resp.etag] = self._part_number
        self._part_number = self._part_number + 1
        return True

    def _initiate_upload(self):
        self.fs._logger.debug(f"Initiating upload {self.path}")
        resp = self.fs.loop.run_until_complete(
            self._client.StartMultipartUpload(
                StartMultipartUploadRequest(key=Key(key=_prefix_path(self.path)), metadata=None)
            )
        )

        self._operation_id = resp.operation_id
        self._upload_initiated = True

    def _fetch_range(self, start, end):
        return self.fs.loop.run_until_complete(
            _fetch_range(self._client, self.fs.max_attempts, _prefix_path(self.path), start, end)
        )

    def close(self):
        super().close()
        if self._upload_initiated:
            return self.fs.loop.run_until_complete(
                self._client.TerminateMultipartUpload(
                    TerminateMultipartUploadRequest(
                        operation_id=self._operation_id,
                        key=Key(key=_prefix_path(self.path)),
                        successful_upload=SuccessfulUploadRequest(
                            etags_parts=self._parts,
                        ),
                    )
                )
            )


fsspec.register_implementation(name="union", cls=AsyncUnionFS, clobber=True)
# Shorter default protocol for unionfs
fsspec.register_implementation(name="ufs", cls=AsyncUnionFS, clobber=True)
