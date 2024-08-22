from google.protobuf import timestamp_pb2 as _timestamp_pb2
from union.internal.identity import enums_pb2 as _enums_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class App(_message.Message):
    __slots__ = ["organization", "client_id", "client_id_issued_at", "redirect_uris", "response_types", "grant_types", "application_type", "contacts", "client_name", "logo_uri", "client_uri", "policy_uri", "tos_uri", "jwks_uri", "token_endpoint_auth_method", "client_secret", "client_secret_expires_at"]
    ORGANIZATION_FIELD_NUMBER: _ClassVar[int]
    CLIENT_ID_FIELD_NUMBER: _ClassVar[int]
    CLIENT_ID_ISSUED_AT_FIELD_NUMBER: _ClassVar[int]
    REDIRECT_URIS_FIELD_NUMBER: _ClassVar[int]
    RESPONSE_TYPES_FIELD_NUMBER: _ClassVar[int]
    GRANT_TYPES_FIELD_NUMBER: _ClassVar[int]
    APPLICATION_TYPE_FIELD_NUMBER: _ClassVar[int]
    CONTACTS_FIELD_NUMBER: _ClassVar[int]
    CLIENT_NAME_FIELD_NUMBER: _ClassVar[int]
    LOGO_URI_FIELD_NUMBER: _ClassVar[int]
    CLIENT_URI_FIELD_NUMBER: _ClassVar[int]
    POLICY_URI_FIELD_NUMBER: _ClassVar[int]
    TOS_URI_FIELD_NUMBER: _ClassVar[int]
    JWKS_URI_FIELD_NUMBER: _ClassVar[int]
    TOKEN_ENDPOINT_AUTH_METHOD_FIELD_NUMBER: _ClassVar[int]
    CLIENT_SECRET_FIELD_NUMBER: _ClassVar[int]
    CLIENT_SECRET_EXPIRES_AT_FIELD_NUMBER: _ClassVar[int]
    organization: str
    client_id: str
    client_id_issued_at: _timestamp_pb2.Timestamp
    redirect_uris: _containers.RepeatedScalarFieldContainer[str]
    response_types: _containers.RepeatedScalarFieldContainer[_enums_pb2.ResponseTypes]
    grant_types: _containers.RepeatedScalarFieldContainer[_enums_pb2.GrantTypes]
    application_type: _enums_pb2.ApplicationType
    contacts: _containers.RepeatedScalarFieldContainer[str]
    client_name: str
    logo_uri: str
    client_uri: str
    policy_uri: str
    tos_uri: str
    jwks_uri: str
    token_endpoint_auth_method: _enums_pb2.TokenEndpointAuthMethod
    client_secret: str
    client_secret_expires_at: _timestamp_pb2.Timestamp
    def __init__(self, organization: _Optional[str] = ..., client_id: _Optional[str] = ..., client_id_issued_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., redirect_uris: _Optional[_Iterable[str]] = ..., response_types: _Optional[_Iterable[_Union[_enums_pb2.ResponseTypes, str]]] = ..., grant_types: _Optional[_Iterable[_Union[_enums_pb2.GrantTypes, str]]] = ..., application_type: _Optional[_Union[_enums_pb2.ApplicationType, str]] = ..., contacts: _Optional[_Iterable[str]] = ..., client_name: _Optional[str] = ..., logo_uri: _Optional[str] = ..., client_uri: _Optional[str] = ..., policy_uri: _Optional[str] = ..., tos_uri: _Optional[str] = ..., jwks_uri: _Optional[str] = ..., token_endpoint_auth_method: _Optional[_Union[_enums_pb2.TokenEndpointAuthMethod, str]] = ..., client_secret: _Optional[str] = ..., client_secret_expires_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...
