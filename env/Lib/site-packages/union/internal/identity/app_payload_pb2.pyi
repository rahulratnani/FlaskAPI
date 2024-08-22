from union.internal.common import list_pb2 as _list_pb2
from union.internal.identity import app_definition_pb2 as _app_definition_pb2
from union.internal.identity import enums_pb2 as _enums_pb2
from union.internal.validate.validate import validate_pb2 as _validate_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class CreateAppRequest(_message.Message):
    __slots__ = ["organization", "client_id", "redirect_uris", "response_types", "grant_types", "application_type", "contacts", "client_name", "logo_uri", "client_uri", "policy_uri", "tos_uri", "jwks_uri", "token_endpoint_auth_method", "consent_method"]
    ORGANIZATION_FIELD_NUMBER: _ClassVar[int]
    CLIENT_ID_FIELD_NUMBER: _ClassVar[int]
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
    CONSENT_METHOD_FIELD_NUMBER: _ClassVar[int]
    organization: str
    client_id: str
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
    consent_method: _enums_pb2.ConsentMethod
    def __init__(self, organization: _Optional[str] = ..., client_id: _Optional[str] = ..., redirect_uris: _Optional[_Iterable[str]] = ..., response_types: _Optional[_Iterable[_Union[_enums_pb2.ResponseTypes, str]]] = ..., grant_types: _Optional[_Iterable[_Union[_enums_pb2.GrantTypes, str]]] = ..., application_type: _Optional[_Union[_enums_pb2.ApplicationType, str]] = ..., contacts: _Optional[_Iterable[str]] = ..., client_name: _Optional[str] = ..., logo_uri: _Optional[str] = ..., client_uri: _Optional[str] = ..., policy_uri: _Optional[str] = ..., tos_uri: _Optional[str] = ..., jwks_uri: _Optional[str] = ..., token_endpoint_auth_method: _Optional[_Union[_enums_pb2.TokenEndpointAuthMethod, str]] = ..., consent_method: _Optional[_Union[_enums_pb2.ConsentMethod, str]] = ...) -> None: ...

class CreateAppResponse(_message.Message):
    __slots__ = ["app"]
    APP_FIELD_NUMBER: _ClassVar[int]
    app: _app_definition_pb2.App
    def __init__(self, app: _Optional[_Union[_app_definition_pb2.App, _Mapping]] = ...) -> None: ...

class GetAppRequest(_message.Message):
    __slots__ = ["organization", "client_id"]
    ORGANIZATION_FIELD_NUMBER: _ClassVar[int]
    CLIENT_ID_FIELD_NUMBER: _ClassVar[int]
    organization: str
    client_id: str
    def __init__(self, organization: _Optional[str] = ..., client_id: _Optional[str] = ...) -> None: ...

class GetAppResponse(_message.Message):
    __slots__ = ["app"]
    APP_FIELD_NUMBER: _ClassVar[int]
    app: _app_definition_pb2.App
    def __init__(self, app: _Optional[_Union[_app_definition_pb2.App, _Mapping]] = ...) -> None: ...

class UpdateAppRequest(_message.Message):
    __slots__ = ["organization", "client_id", "redirect_uris", "response_types", "grant_types", "application_type", "contacts", "client_name", "logo_uri", "client_uri", "policy_uri", "tos_uri", "jwks_uri", "token_endpoint_auth_method"]
    ORGANIZATION_FIELD_NUMBER: _ClassVar[int]
    CLIENT_ID_FIELD_NUMBER: _ClassVar[int]
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
    organization: str
    client_id: str
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
    def __init__(self, organization: _Optional[str] = ..., client_id: _Optional[str] = ..., redirect_uris: _Optional[_Iterable[str]] = ..., response_types: _Optional[_Iterable[_Union[_enums_pb2.ResponseTypes, str]]] = ..., grant_types: _Optional[_Iterable[_Union[_enums_pb2.GrantTypes, str]]] = ..., application_type: _Optional[_Union[_enums_pb2.ApplicationType, str]] = ..., contacts: _Optional[_Iterable[str]] = ..., client_name: _Optional[str] = ..., logo_uri: _Optional[str] = ..., client_uri: _Optional[str] = ..., policy_uri: _Optional[str] = ..., tos_uri: _Optional[str] = ..., jwks_uri: _Optional[str] = ..., token_endpoint_auth_method: _Optional[_Union[_enums_pb2.TokenEndpointAuthMethod, str]] = ...) -> None: ...

class UpdateAppResponse(_message.Message):
    __slots__ = ["app"]
    APP_FIELD_NUMBER: _ClassVar[int]
    app: _app_definition_pb2.App
    def __init__(self, app: _Optional[_Union[_app_definition_pb2.App, _Mapping]] = ...) -> None: ...

class DeleteAppRequest(_message.Message):
    __slots__ = ["organization", "client_id"]
    ORGANIZATION_FIELD_NUMBER: _ClassVar[int]
    CLIENT_ID_FIELD_NUMBER: _ClassVar[int]
    organization: str
    client_id: str
    def __init__(self, organization: _Optional[str] = ..., client_id: _Optional[str] = ...) -> None: ...

class DeleteAppResponse(_message.Message):
    __slots__ = []
    def __init__(self) -> None: ...

class ListAppsRequest(_message.Message):
    __slots__ = ["organization", "request"]
    ORGANIZATION_FIELD_NUMBER: _ClassVar[int]
    REQUEST_FIELD_NUMBER: _ClassVar[int]
    organization: str
    request: _list_pb2.ListRequest
    def __init__(self, organization: _Optional[str] = ..., request: _Optional[_Union[_list_pb2.ListRequest, _Mapping]] = ...) -> None: ...

class ListAppsResponse(_message.Message):
    __slots__ = ["apps", "token"]
    APPS_FIELD_NUMBER: _ClassVar[int]
    TOKEN_FIELD_NUMBER: _ClassVar[int]
    apps: _containers.RepeatedCompositeFieldContainer[_app_definition_pb2.App]
    token: str
    def __init__(self, apps: _Optional[_Iterable[_Union[_app_definition_pb2.App, _Mapping]]] = ..., token: _Optional[str] = ...) -> None: ...
