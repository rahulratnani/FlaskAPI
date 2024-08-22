from typing import Tuple

import grpc
from flytekit.clients.auth_helper import get_authenticated_channel
from flytekit.configuration import PlatformConfig

from union._config import _get_organization
from union._interceptor import intercept_channel_with_org


def _get_channel_with_org(platform_config: PlatformConfig) -> Tuple[grpc.Channel, str]:
    """Construct authenticated channel that injects the org."""
    channel = get_authenticated_channel(platform_config)

    org = _get_organization(platform_config, channel)
    channel = intercept_channel_with_org(org, channel)
    return channel, org
