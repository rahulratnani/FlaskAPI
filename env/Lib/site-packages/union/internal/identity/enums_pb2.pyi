from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from typing import ClassVar as _ClassVar

DESCRIPTOR: _descriptor.FileDescriptor

class ResponseTypes(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []
    CODE: _ClassVar[ResponseTypes]
    TOKEN: _ClassVar[ResponseTypes]
    ID_TOKEN: _ClassVar[ResponseTypes]

class ApplicationType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []
    WEB: _ClassVar[ApplicationType]
    NATIVE: _ClassVar[ApplicationType]

class GrantTypes(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []
    AUTHORIZATION_CODE: _ClassVar[GrantTypes]
    IMPLICIT: _ClassVar[GrantTypes]
    PASSWORD: _ClassVar[GrantTypes]
    CLIENT_CREDENTIALS: _ClassVar[GrantTypes]
    REFRESH_TOKEN: _ClassVar[GrantTypes]
    DEVICE_CODE: _ClassVar[GrantTypes]

class TokenEndpointAuthMethod(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []
    NONE: _ClassVar[TokenEndpointAuthMethod]
    CLIENT_SECRET_POST: _ClassVar[TokenEndpointAuthMethod]
    CLIENT_SECRET_BASIC: _ClassVar[TokenEndpointAuthMethod]

class ConsentMethod(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []
    CONSENT_METHOD_NONE: _ClassVar[ConsentMethod]
    CONSENT_METHOD_TRUSTED: _ClassVar[ConsentMethod]
    CONSENT_METHOD_REQUIRED: _ClassVar[ConsentMethod]
CODE: ResponseTypes
TOKEN: ResponseTypes
ID_TOKEN: ResponseTypes
WEB: ApplicationType
NATIVE: ApplicationType
AUTHORIZATION_CODE: GrantTypes
IMPLICIT: GrantTypes
PASSWORD: GrantTypes
CLIENT_CREDENTIALS: GrantTypes
REFRESH_TOKEN: GrantTypes
DEVICE_CODE: GrantTypes
NONE: TokenEndpointAuthMethod
CLIENT_SECRET_POST: TokenEndpointAuthMethod
CLIENT_SECRET_BASIC: TokenEndpointAuthMethod
CONSENT_METHOD_NONE: ConsentMethod
CONSENT_METHOD_TRUSTED: ConsentMethod
CONSENT_METHOD_REQUIRED: ConsentMethod
