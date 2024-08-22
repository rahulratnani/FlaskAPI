import base64
import importlib
import os
import sys
import textwrap
from dataclasses import dataclass
from functools import lru_cache, partial
from importlib.metadata import version
from os import getenv
from pathlib import Path
from string import Template
from typing import List, Optional, Union

import click
import grpc
from flyteidl.service.identity_pb2 import UserInfoRequest
from flyteidl.service.identity_pb2_grpc import IdentityServiceStub
from flytekit.clients.auth_helper import get_authenticated_channel
from flytekit.configuration import AuthType, Config, PlatformConfig, get_config_file
from flytekit.configuration.default_images import DefaultImages

_DEFAULT_GCP_SERVERLESS_ENDPOINT: str = "serverless-1.us-east-2.s.union.ai"
_SERVERLESS_ENDPOINTS = {
    "serverless-1.us-east-2.s.union.ai",
    "serverless-gcp.cloud-staging.union.ai",
    "utt-srv-staging-1.cloud-staging.union.ai",
    "serverless-preview.canary.unionai.cloud",
    "utt-srv-canary-1.canary.unionai.cloud",
}

_UNION_CONFIG_ENV_VARS: List[str] = ["UNION_CONFIG", "UNIONAI_CONFIG"]
_UNION_SERVERLESS_ENDPOINT_ENV_VAR: str = "UNION_SERVERLESS_ENDPOINT"
_UNION_API_KEY_ENV_VARS: List[str] = [
    "UNION_API_KEY",
    "UNION_SERVERLESS_API_KEY",
    "UNIONAI_SERVERLESS_API_KEY",
]
_UNION_ENABLE_IMAGE_BUILDER_ENV_VAR: str = "UNION_ENABLE_REGISTER_IMAGE_BUILDER"
_UNION_DEFAULT_CONFIG_PATHS: List[Path] = [
    Path.home() / ".union" / "config.yaml",
    Path.home() / ".uctl" / "config.yaml",
]
_UNION_DEFAULT_CONFIG_PATH: Path = _UNION_DEFAULT_CONFIG_PATHS[0]


@dataclass
class _UnionConfig:
    serverless_endpoint: str = getenv(
        _UNION_SERVERLESS_ENDPOINT_ENV_VAR,
        _DEFAULT_GCP_SERVERLESS_ENDPOINT,
    )
    org: Optional[str] = None
    config: Optional[str] = None
    is_direct_union_cli_call: bool = False


_UNION_CONFIG = _UnionConfig()


def _is_serverless_endpoint(endpoint: str) -> str:
    """Check if endpoint is serverless."""
    return endpoint in (endpoint, f"dns:///{endpoint}") and endpoint in _SERVERLESS_ENDPOINTS


def _should_enable_image_builder(endpoint: str) -> bool:
    """Enable image builder when either holds:

    - `endpoint` is a serverless endpoint
    - UNIONAI_ENABLE_REGISTER_IMAGE_BUILDER=1

    """
    is_serverless = _is_serverless_endpoint(endpoint)
    enable_with_env = os.getenv(_UNION_ENABLE_IMAGE_BUILDER_ENV_VAR, "0") == "1"
    return is_serverless or enable_with_env


@dataclass
class AppClientCredentials:
    endpoint: str
    client_id: str
    client_secret: str
    org: str


def _encode_app_client_credentials(app_credentials: AppClientCredentials) -> str:
    """Encode app_credentials with base64."""
    data = (
        f"{app_credentials.endpoint}:{app_credentials.client_id}:{app_credentials.client_secret}:{app_credentials.org}"
    )
    return base64.b64encode(data.encode("utf-8")).decode("utf-8")


def _decode_app_client_credentials(encoded_str: str) -> AppClientCredentials:
    """Decode encoded base64 string into app credentials."""
    endpoint, client_id, client_secret, org = base64.b64decode(encoded_str.encode("utf-8")).decode("utf-8").split(":")
    return AppClientCredentials(endpoint=endpoint, client_id=client_id, client_secret=client_secret, org=org)


@lru_cache(maxsize=1)
def _unionmeta_byoc_is_installed() -> bool:
    """Check if unionmeta_byoc is installed."""
    try:
        importlib.import_module("unionmeta_byoc")
        return True
    except ModuleNotFoundError:
        return False


def _clean_endpoint(endpoint: str) -> str:
    """Clean endpoint."""
    prefixes = ("dns:///", "http://", "https://")

    for prefix in prefixes:
        if endpoint.startswith(prefix):
            n_prefix = len(prefix)
            endpoint = endpoint[n_prefix:]
            break

    return endpoint.rstrip("/")


def _get_endpoint_for_login(endpoint: Optional[str]) -> str:
    """Get endpoint for login."""
    if _unionmeta_byoc_is_installed():
        # byoc
        if endpoint is None:
            msg = "--host must be passed in for login"
            raise click.ClickException(msg)
        return _clean_endpoint(endpoint)
    else:
        if endpoint is not None:
            return _clean_endpoint(endpoint)
        return _UNION_CONFIG.serverless_endpoint


def _get_env_var(env_vars: List[str]) -> Optional[str]:
    """Get environment variable from a list of env_vars. env_vars that are first"""
    for env_var in env_vars:
        if env_var in os.environ:
            return os.environ[env_var]
    return None


def _get_config_path(config_paths: List[Path] = _UNION_DEFAULT_CONFIG_PATHS) -> Optional[Path]:
    """Get configuration path."""
    for path in config_paths:
        if path.exists():
            return path
    return None


_get_union_config_env_var = partial(_get_env_var, env_vars=_UNION_CONFIG_ENV_VARS)
_get_union_api_env_var = partial(_get_env_var, env_vars=_UNION_API_KEY_ENV_VARS)


def _check_unionmeta_byoc(config: Optional[str]):
    """Check defaults for `pip install union[byoc]`

    - `--config` must be passed in
    - `UNION_CONFIG` must be set.
    """
    if not _unionmeta_byoc_is_installed():
        return

    if config is not None or _UNION_CONFIG.config is not None:
        # Config is passed in directly
        return

    union_env_var = _get_union_config_env_var()
    config_path = _get_config_path()

    if _UNION_CONFIG.is_direct_union_cli_call and union_env_var is None and config_path is None:
        msg = (
            "When using the union CLI, please pass in --config, set UNION_CONFIG or "
            "add a config to ~/.union/config.yaml"
        )

        raise click.ClickException(msg)


def _check_yaml_config_is_empty(config_file: Union[str, os.PathLike]):
    with open(config_file, "r") as f:
        contents = f.read().strip()

    if not contents:
        raise click.ClickException(
            f"Unable to load yaml at {config_file} because it is empty. "
            "Delete file or pass a config that is not empty"
        )


def _decode_union_api_key(serverless_api_value: str) -> Config:
    """Decode union serverless api key and return Config."""
    config = Config.auto()
    try:
        app_credentials = _decode_app_client_credentials(serverless_api_value)
    except Exception as e:
        raise ValueError("Unable to read UNION_API_KEY") from e

    if _UNION_CONFIG.org is None and app_credentials.org != "":
        _UNION_CONFIG.org = app_credentials.org

    return config.with_params(
        platform=PlatformConfig(
            endpoint=app_credentials.endpoint,
            insecure=False,
            auth_mode=AuthType.CLIENTSECRET,
            client_id=app_credentials.client_id,
            client_credentials_secret=app_credentials.client_secret,
        )
    )


def _get_config_obj(config: Optional[str] = None, default_to_union_semantics: bool = False) -> Config:
    """Get Config object.

    If `config` is not None, then it will be used as the Config file.

    If the `union` CLI is called directly or `default_to_union_semantics=True`, then the config is set
    in the following order:
        1. `UNION_SERVERLESS_ENDPOINT` environment variable (Used for development)
        2. `UNION_SERVERLESS_API_KEY` environment variable
        3. `UNION_CONFIG` environment variable
        4. ~/.union/config.yaml if it exists

    If `pyflyte` CLI is called and `flytekit`'s `get_config_file` did not return a `ConfigFile`,
    then serverless it the default endpoint.
    """
    if config is not None:
        return Config.auto(config)

    elif _UNION_CONFIG.is_direct_union_cli_call or default_to_union_semantics:
        _check_unionmeta_byoc(config)

        # CLI ran with `union` -> Config is _UNION_CONFIG.config and the default is serverless
        if getenv(_UNION_SERVERLESS_ENDPOINT_ENV_VAR) is not None:
            # If UNION_SERVERLESS_ENDPOINT is set in `_UnionConfig`, use it instead
            return Config.for_endpoint(endpoint=_UNION_CONFIG.serverless_endpoint)
        if (serverless_api_value := _get_union_api_env_var()) is not None and serverless_api_value != "":
            return _decode_union_api_key(serverless_api_value)
        elif _UNION_CONFIG.config is not None:
            return Config.auto(_UNION_CONFIG.config)
        elif (config_path := _get_config_path()) is not None:
            # Check if config is empty:
            _check_yaml_config_is_empty(config_path)
            # Read config from file system
            return Config.auto(str(config_path.absolute()))
        else:
            # Got to serverless
            return Config.for_endpoint(endpoint=_UNION_CONFIG.serverless_endpoint)
    else:
        # CLI ran with `pyflyte`, we use mostly the same semantics as `pyflyte`. The difference is:
        # - byoc => Go to localhost
        # - else => Go to serverless
        cfg_file = get_config_file(_UNION_CONFIG.config)

        if cfg_file is not None:
            return Config.auto(cfg_file)

        # At this point, cfg_file is None. For byoc, we keep the flytekit behavior and go to localhost
        if _unionmeta_byoc_is_installed():
            return Config.auto(cfg_file)

        # Without byoc, then go to serverless
        return Config.for_endpoint(endpoint=_UNION_CONFIG.serverless_endpoint)


def _get_organization(platform_config: PlatformConfig, channel: Optional[grpc.Channel] = None) -> str:
    """Get organization based on endpoint."""
    if _UNION_CONFIG.org is not None:
        return _UNION_CONFIG.org
    elif _is_serverless_endpoint(platform_config.endpoint):
        org = _get_user_handle(platform_config, channel)
        _UNION_CONFIG.org = org
        return org
    else:
        # Managed+ users, the org is not required for requests and we set it ""
        # to replicate default flytekit behavior.
        return ""


def _get_user_handle(platform_config: PlatformConfig, channel: Optional[grpc.Channel] = None) -> str:
    """Get user_handle for PlatformConfig."""
    if channel is None:
        channel = get_authenticated_channel(platform_config)

    client = IdentityServiceStub(channel)
    user_info = client.UserInfo(UserInfoRequest())
    user_handle = user_info.additional_claims.fields["userhandle"]
    return user_handle.string_value


def _get_default_image() -> str:
    """Get default image version."""
    cfg_obj = _get_config_obj()

    # TODO: This is only temporary to support GCP endpoints. When the union images are public,
    # we will always use union images
    endpoint = cfg_obj.platform.endpoint
    if _is_serverless_endpoint(endpoint):
        major, minor = sys.version_info.major, sys.version_info.minor
        union_version = version("union")
        if "dev" in union_version:
            suffix = "latest"
        else:
            suffix = union_version

        return f"cr.union.ai/v1/unionai/union:py{major}.{minor}-{suffix}"

    return DefaultImages().find_image_for()


def _write_config_to_path(endpoint: str, auth_type: str, config_path: Path = _UNION_DEFAULT_CONFIG_PATH):
    """Write config to config directory."""
    config_dir = config_path.parent
    config_dir.mkdir(exist_ok=True, parents=True)

    config_template = Template(
        textwrap.dedent(
            """\
    admin:
      endpoint: $endpoint
      insecure: false
      authType: $auth_type
    logger:
      show-source: true
      level: 0
    union:
      connection:
        host: $endpoint
        insecure: false
      auth:
        type: $auth_type
    """
        )
    )
    config_path.write_text(config_template.substitute(endpoint=f"dns:///{endpoint}", auth_type=auth_type))
    return config_path


def _get_default_project(previous_default: str):
    cfg_obj = _get_config_obj()
    if _is_serverless_endpoint(cfg_obj.platform.endpoint):
        return "default"
    return previous_default


def _get_auth_success_html(endpoint: str) -> str:
    """Get default success html. Return None to use flytekit's default success html."""
    if endpoint.endswith("union.ai") or endpoint.endswith("unionai.cloud"):
        SUCCESS_HTML = textwrap.dedent(
            f"""
        <html>
        <head>
            <title>OAuth2 Authentication to Union Successful</title>
        </head>
        <body style="background:white;font-family:Arial">
            <div style="position: absolute;top:40%;left:50%;transform: translate(-50%, -50%);text-align:center;">
                <div style="margin:auto">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 65" fill="currentColor"
                        style="color:#fdb51e;width:360px;">
                        <title>Union.ai</title>
                        <path d="M32,64.8C14.4,64.8,0,51.5,0,34V3.6h17.6v41.3c0,1.9,1.1,3,3,3h23c1.9,0,3-1.1,3-3V3.6H64V34
                        C64,51.5,49.6,64.8,32,64.8z M69.9,30.9v30.4h17.6V20c0-1.9,1.1-3,3-3h23c1.9,0,3,1.1,3,3v41.3H134V30.9c0-17.5-14.4-30.8-32.1-30.8
                        S69.9,13.5,69.9,30.9z M236,30.9v30.4h17.6V20c0-1.9,1.1-3,3-3h23c1.9,0,3,1.1,3,3v41.3H300V30.9c0-17.5-14.4-30.8-32-30.8
                        S236,13.5,236,30.9L236,30.9z M230.1,32.4c0,18.2-14.2,32.5-32.2,32.5s-32-14.3-32-32.5s14-32.1,32-32.1S230.1,14.3,230.1,32.4
                        L230.1,32.4z M213.5,20.2c0-1.9-1.1-3-3-3h-24.8c-1.9,0-3,1.1-3,3v24.5c0,1.9,1.1,3,3,3h24.8c1.9,0,3-1.1,3-3V20.2z M158.9,3.6
                        h-17.6v57.8h17.6V3.6z"></path>
                    </svg>
                    <h2>You've successfully authenticated to Union!</h2>
                    <p style="font-size:20px;">Return to your terminal for next steps</p>
                </div>
            </div>
        </body>
        </html>
        """  # noqa
        )
        return SUCCESS_HTML
    return None
