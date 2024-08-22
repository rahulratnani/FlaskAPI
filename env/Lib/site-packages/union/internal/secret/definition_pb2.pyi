from google.protobuf import timestamp_pb2 as _timestamp_pb2
from union.internal.validate.validate import validate_pb2 as _validate_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class SecretSpec(_message.Message):
    __slots__ = ["string_value", "binary_value"]
    STRING_VALUE_FIELD_NUMBER: _ClassVar[int]
    BINARY_VALUE_FIELD_NUMBER: _ClassVar[int]
    string_value: str
    binary_value: bytes
    def __init__(self, string_value: _Optional[str] = ..., binary_value: _Optional[bytes] = ...) -> None: ...

class SecretIdentifier(_message.Message):
    __slots__ = ["name", "organization", "domain", "project"]
    NAME_FIELD_NUMBER: _ClassVar[int]
    ORGANIZATION_FIELD_NUMBER: _ClassVar[int]
    DOMAIN_FIELD_NUMBER: _ClassVar[int]
    PROJECT_FIELD_NUMBER: _ClassVar[int]
    name: str
    organization: str
    domain: str
    project: str
    def __init__(self, name: _Optional[str] = ..., organization: _Optional[str] = ..., domain: _Optional[str] = ..., project: _Optional[str] = ...) -> None: ...

class SecretMetadata(_message.Message):
    __slots__ = ["created_time"]
    CREATED_TIME_FIELD_NUMBER: _ClassVar[int]
    created_time: _timestamp_pb2.Timestamp
    def __init__(self, created_time: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class Secret(_message.Message):
    __slots__ = ["id", "secret_metadata"]
    ID_FIELD_NUMBER: _ClassVar[int]
    SECRET_METADATA_FIELD_NUMBER: _ClassVar[int]
    id: SecretIdentifier
    secret_metadata: SecretMetadata
    def __init__(self, id: _Optional[_Union[SecretIdentifier, _Mapping]] = ..., secret_metadata: _Optional[_Union[SecretMetadata, _Mapping]] = ...) -> None: ...
