from union.internal.common import list_pb2 as _list_pb2
from google.protobuf import duration_pb2 as _duration_pb2
from google.protobuf import timestamp_pb2 as _timestamp_pb2
from union.internal.objectstore import definition_pb2 as _definition_pb2
from union.internal.validate.validate import validate_pb2 as _validate_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class MetadataRequest(_message.Message):
    __slots__ = []
    def __init__(self) -> None: ...

class MetadataResponse(_message.Message):
    __slots__ = ["max_single_part_object_size_bytes", "min_part_size_bytes", "max_part_size_bytes"]
    MAX_SINGLE_PART_OBJECT_SIZE_BYTES_FIELD_NUMBER: _ClassVar[int]
    MIN_PART_SIZE_BYTES_FIELD_NUMBER: _ClassVar[int]
    MAX_PART_SIZE_BYTES_FIELD_NUMBER: _ClassVar[int]
    max_single_part_object_size_bytes: int
    min_part_size_bytes: int
    max_part_size_bytes: int
    def __init__(self, max_single_part_object_size_bytes: _Optional[int] = ..., min_part_size_bytes: _Optional[int] = ..., max_part_size_bytes: _Optional[int] = ...) -> None: ...

class PutRequest(_message.Message):
    __slots__ = ["key", "metadata", "object"]
    KEY_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    OBJECT_FIELD_NUMBER: _ClassVar[int]
    key: _definition_pb2.Key
    metadata: _definition_pb2.Metadata
    object: _definition_pb2.Object
    def __init__(self, key: _Optional[_Union[_definition_pb2.Key, _Mapping]] = ..., metadata: _Optional[_Union[_definition_pb2.Metadata, _Mapping]] = ..., object: _Optional[_Union[_definition_pb2.Object, _Mapping]] = ...) -> None: ...

class PutResponse(_message.Message):
    __slots__ = ["size_bytes", "etag"]
    SIZE_BYTES_FIELD_NUMBER: _ClassVar[int]
    ETAG_FIELD_NUMBER: _ClassVar[int]
    size_bytes: int
    etag: str
    def __init__(self, size_bytes: _Optional[int] = ..., etag: _Optional[str] = ...) -> None: ...

class GetRequest(_message.Message):
    __slots__ = ["key"]
    KEY_FIELD_NUMBER: _ClassVar[int]
    key: _definition_pb2.Key
    def __init__(self, key: _Optional[_Union[_definition_pb2.Key, _Mapping]] = ...) -> None: ...

class GetResponse(_message.Message):
    __slots__ = ["object", "metadata", "size_bytes", "etag"]
    OBJECT_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    SIZE_BYTES_FIELD_NUMBER: _ClassVar[int]
    ETAG_FIELD_NUMBER: _ClassVar[int]
    object: _definition_pb2.Object
    metadata: _definition_pb2.Metadata
    size_bytes: int
    etag: str
    def __init__(self, object: _Optional[_Union[_definition_pb2.Object, _Mapping]] = ..., metadata: _Optional[_Union[_definition_pb2.Metadata, _Mapping]] = ..., size_bytes: _Optional[int] = ..., etag: _Optional[str] = ...) -> None: ...

class ListRequest(_message.Message):
    __slots__ = ["request"]
    REQUEST_FIELD_NUMBER: _ClassVar[int]
    request: _list_pb2.ListRequest
    def __init__(self, request: _Optional[_Union[_list_pb2.ListRequest, _Mapping]] = ...) -> None: ...

class ListResponse(_message.Message):
    __slots__ = ["keys", "next_token", "directories"]
    KEYS_FIELD_NUMBER: _ClassVar[int]
    NEXT_TOKEN_FIELD_NUMBER: _ClassVar[int]
    DIRECTORIES_FIELD_NUMBER: _ClassVar[int]
    keys: _containers.RepeatedCompositeFieldContainer[_definition_pb2.Key]
    next_token: str
    directories: _containers.RepeatedCompositeFieldContainer[_definition_pb2.Key]
    def __init__(self, keys: _Optional[_Iterable[_Union[_definition_pb2.Key, _Mapping]]] = ..., next_token: _Optional[str] = ..., directories: _Optional[_Iterable[_Union[_definition_pb2.Key, _Mapping]]] = ...) -> None: ...

class DeleteRequest(_message.Message):
    __slots__ = ["key"]
    KEY_FIELD_NUMBER: _ClassVar[int]
    key: _definition_pb2.Key
    def __init__(self, key: _Optional[_Union[_definition_pb2.Key, _Mapping]] = ...) -> None: ...

class DeleteResponse(_message.Message):
    __slots__ = []
    def __init__(self) -> None: ...

class HeadRequest(_message.Message):
    __slots__ = ["key"]
    KEY_FIELD_NUMBER: _ClassVar[int]
    key: _definition_pb2.Key
    def __init__(self, key: _Optional[_Union[_definition_pb2.Key, _Mapping]] = ...) -> None: ...

class HeadResponse(_message.Message):
    __slots__ = ["metadata", "etag", "size_bytes"]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    ETAG_FIELD_NUMBER: _ClassVar[int]
    SIZE_BYTES_FIELD_NUMBER: _ClassVar[int]
    metadata: _definition_pb2.Metadata
    etag: str
    size_bytes: int
    def __init__(self, metadata: _Optional[_Union[_definition_pb2.Metadata, _Mapping]] = ..., etag: _Optional[str] = ..., size_bytes: _Optional[int] = ...) -> None: ...

class SuccessfulUploadRequest(_message.Message):
    __slots__ = ["etags_parts"]
    class EtagsPartsEntry(_message.Message):
        __slots__ = ["key", "value"]
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: int
        def __init__(self, key: _Optional[str] = ..., value: _Optional[int] = ...) -> None: ...
    ETAGS_PARTS_FIELD_NUMBER: _ClassVar[int]
    etags_parts: _containers.ScalarMap[str, int]
    def __init__(self, etags_parts: _Optional[_Mapping[str, int]] = ...) -> None: ...

class AbortUploadRequest(_message.Message):
    __slots__ = []
    def __init__(self) -> None: ...

class TerminateMultipartUploadRequest(_message.Message):
    __slots__ = ["operation_id", "key", "successful_upload", "abort_upload"]
    OPERATION_ID_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_NUMBER: _ClassVar[int]
    SUCCESSFUL_UPLOAD_FIELD_NUMBER: _ClassVar[int]
    ABORT_UPLOAD_FIELD_NUMBER: _ClassVar[int]
    operation_id: str
    key: _definition_pb2.Key
    successful_upload: SuccessfulUploadRequest
    abort_upload: AbortUploadRequest
    def __init__(self, operation_id: _Optional[str] = ..., key: _Optional[_Union[_definition_pb2.Key, _Mapping]] = ..., successful_upload: _Optional[_Union[SuccessfulUploadRequest, _Mapping]] = ..., abort_upload: _Optional[_Union[AbortUploadRequest, _Mapping]] = ...) -> None: ...

class TerminateMultipartUploadResponse(_message.Message):
    __slots__ = ["key", "etag"]
    KEY_FIELD_NUMBER: _ClassVar[int]
    ETAG_FIELD_NUMBER: _ClassVar[int]
    key: _definition_pb2.Key
    etag: str
    def __init__(self, key: _Optional[_Union[_definition_pb2.Key, _Mapping]] = ..., etag: _Optional[str] = ...) -> None: ...

class StartMultipartUploadRequest(_message.Message):
    __slots__ = ["key", "metadata"]
    KEY_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    key: _definition_pb2.Key
    metadata: _definition_pb2.Metadata
    def __init__(self, key: _Optional[_Union[_definition_pb2.Key, _Mapping]] = ..., metadata: _Optional[_Union[_definition_pb2.Metadata, _Mapping]] = ...) -> None: ...

class StartMultipartUploadResponse(_message.Message):
    __slots__ = ["operation_id", "expires_at"]
    OPERATION_ID_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_AT_FIELD_NUMBER: _ClassVar[int]
    operation_id: str
    expires_at: _timestamp_pb2.Timestamp
    def __init__(self, operation_id: _Optional[str] = ..., expires_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class UploadPartRequest(_message.Message):
    __slots__ = ["operation_id", "key", "part_number", "object", "content_length"]
    OPERATION_ID_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_NUMBER: _ClassVar[int]
    PART_NUMBER_FIELD_NUMBER: _ClassVar[int]
    OBJECT_FIELD_NUMBER: _ClassVar[int]
    CONTENT_LENGTH_FIELD_NUMBER: _ClassVar[int]
    operation_id: str
    key: _definition_pb2.Key
    part_number: int
    object: _definition_pb2.Object
    content_length: int
    def __init__(self, operation_id: _Optional[str] = ..., key: _Optional[_Union[_definition_pb2.Key, _Mapping]] = ..., part_number: _Optional[int] = ..., object: _Optional[_Union[_definition_pb2.Object, _Mapping]] = ..., content_length: _Optional[int] = ...) -> None: ...

class UploadPartResponse(_message.Message):
    __slots__ = ["etag"]
    ETAG_FIELD_NUMBER: _ClassVar[int]
    etag: str
    def __init__(self, etag: _Optional[str] = ...) -> None: ...

class ListInProgressMultipartUploadsRequest(_message.Message):
    __slots__ = ["request"]
    REQUEST_FIELD_NUMBER: _ClassVar[int]
    request: _list_pb2.ListRequest
    def __init__(self, request: _Optional[_Union[_list_pb2.ListRequest, _Mapping]] = ...) -> None: ...

class MultipartUpload(_message.Message):
    __slots__ = ["operation_id", "key"]
    OPERATION_ID_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_NUMBER: _ClassVar[int]
    operation_id: str
    key: _definition_pb2.Key
    def __init__(self, operation_id: _Optional[str] = ..., key: _Optional[_Union[_definition_pb2.Key, _Mapping]] = ...) -> None: ...

class ListInProgressMultipartUploadsResponse(_message.Message):
    __slots__ = ["operations"]
    OPERATIONS_FIELD_NUMBER: _ClassVar[int]
    operations: _containers.RepeatedCompositeFieldContainer[MultipartUpload]
    def __init__(self, operations: _Optional[_Iterable[_Union[MultipartUpload, _Mapping]]] = ...) -> None: ...

class DownloadPartRequest(_message.Message):
    __slots__ = ["key", "start_pos", "size_bytes"]
    KEY_FIELD_NUMBER: _ClassVar[int]
    START_POS_FIELD_NUMBER: _ClassVar[int]
    SIZE_BYTES_FIELD_NUMBER: _ClassVar[int]
    key: _definition_pb2.Key
    start_pos: int
    size_bytes: int
    def __init__(self, key: _Optional[_Union[_definition_pb2.Key, _Mapping]] = ..., start_pos: _Optional[int] = ..., size_bytes: _Optional[int] = ...) -> None: ...

class DownloadPartResponse(_message.Message):
    __slots__ = ["object"]
    OBJECT_FIELD_NUMBER: _ClassVar[int]
    object: _definition_pb2.Object
    def __init__(self, object: _Optional[_Union[_definition_pb2.Object, _Mapping]] = ...) -> None: ...

class CopyRequest(_message.Message):
    __slots__ = ["source_key", "destination_key"]
    SOURCE_KEY_FIELD_NUMBER: _ClassVar[int]
    DESTINATION_KEY_FIELD_NUMBER: _ClassVar[int]
    source_key: _definition_pb2.Key
    destination_key: _definition_pb2.Key
    def __init__(self, source_key: _Optional[_Union[_definition_pb2.Key, _Mapping]] = ..., destination_key: _Optional[_Union[_definition_pb2.Key, _Mapping]] = ...) -> None: ...

class CopyResponse(_message.Message):
    __slots__ = []
    def __init__(self) -> None: ...

class PresignRequest(_message.Message):
    __slots__ = ["key", "expires_in", "put_request", "get_request"]
    KEY_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_IN_FIELD_NUMBER: _ClassVar[int]
    PUT_REQUEST_FIELD_NUMBER: _ClassVar[int]
    GET_REQUEST_FIELD_NUMBER: _ClassVar[int]
    key: _definition_pb2.Key
    expires_in: _duration_pb2.Duration
    put_request: _definition_pb2.PresignPutRequest
    get_request: _definition_pb2.PresignGetRequest
    def __init__(self, key: _Optional[_Union[_definition_pb2.Key, _Mapping]] = ..., expires_in: _Optional[_Union[_duration_pb2.Duration, _Mapping]] = ..., put_request: _Optional[_Union[_definition_pb2.PresignPutRequest, _Mapping]] = ..., get_request: _Optional[_Union[_definition_pb2.PresignGetRequest, _Mapping]] = ...) -> None: ...

class PresignResponse(_message.Message):
    __slots__ = ["signed_url"]
    SIGNED_URL_FIELD_NUMBER: _ClassVar[int]
    signed_url: str
    def __init__(self, signed_url: _Optional[str] = ...) -> None: ...
