from union.internal.validate.validate import validate_pb2 as _validate_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class HTTPMethod(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []
    UNSPECIFIED: _ClassVar[HTTPMethod]
    GET: _ClassVar[HTTPMethod]
    PUT: _ClassVar[HTTPMethod]
UNSPECIFIED: HTTPMethod
GET: HTTPMethod
PUT: HTTPMethod

class Metadata(_message.Message):
    __slots__ = ["tag"]
    class TagEntry(_message.Message):
        __slots__ = ["key", "value"]
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    TAG_FIELD_NUMBER: _ClassVar[int]
    tag: _containers.ScalarMap[str, str]
    def __init__(self, tag: _Optional[_Mapping[str, str]] = ...) -> None: ...

class Object(_message.Message):
    __slots__ = ["contents"]
    CONTENTS_FIELD_NUMBER: _ClassVar[int]
    contents: bytes
    def __init__(self, contents: _Optional[bytes] = ...) -> None: ...

class Key(_message.Message):
    __slots__ = ["key"]
    KEY_FIELD_NUMBER: _ClassVar[int]
    key: str
    def __init__(self, key: _Optional[str] = ...) -> None: ...

class PresignPutRequest(_message.Message):
    __slots__ = ["content_md5"]
    CONTENT_MD5_FIELD_NUMBER: _ClassVar[int]
    content_md5: bytes
    def __init__(self, content_md5: _Optional[bytes] = ...) -> None: ...

class PresignGetRequest(_message.Message):
    __slots__ = []
    def __init__(self) -> None: ...
