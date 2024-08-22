import logging
import random
import string
from collections import namedtuple
from collections.abc import MutableMapping, Sequence
from contextlib import suppress
from typing import Any

import grpc
from flyteidl.service.admin_pb2_grpc import AdminServiceStub
from flyteidl.service.dataproxy_pb2_grpc import DataProxyServiceStub
from flyteidl.service.signal_pb2_grpc import SignalServiceStub
from flytekit.clients.friendly import SynchronousFlyteClient

logger = logging.getLogger(__name__)


class ConcreteClientCallDetails(
    namedtuple(
        "ConcreteClientCallDetails",
        (
            "method",
            "timeout",
            "metadata",
            "credentials",
            "wait_for_ready",
            "compression",
        ),
    ),
    grpc.ClientCallDetails,
):
    """Concrete implementation for ClientCallDetails."""


def set_org(obj: Any, org: str):
    """Recursively set the org in obj."""
    with suppress(AttributeError):
        obj.org = org

    with suppress(AttributeError):
        for _, value in obj.ListFields():
            set_org(value, org=org)

    if isinstance(obj, Sequence) and not isinstance(obj, str):
        for value in obj:
            set_org(value, org=org)

    if isinstance(obj, MutableMapping):
        for value in obj.values():
            set_org(value, org=org)


def generate_random_str(N):
    return "".join(random.choice(string.ascii_letters) for _ in range(N))


class OrgInterceptor(grpc.UnaryUnaryClientInterceptor):
    """Interceptor that adds org metadata into the grpc call."""

    def __init__(self, org: str):
        self.org = org

    def intercept_unary_unary(self, continuation, client_call_details, request):
        request_id = f"u-{generate_random_str(20)}"
        old_metadata = client_call_details.metadata or []
        new_metadata = old_metadata + [("x-user-active-org", self.org), ("x-request-id", request_id)]
        new_details = ConcreteClientCallDetails(
            method=client_call_details.method,
            timeout=client_call_details.timeout,
            metadata=new_metadata,
            credentials=client_call_details.credentials,
            wait_for_ready=client_call_details.wait_for_ready,
            compression=client_call_details.compression,
        )

        # Inject org into every IDL requests
        set_org(request, org=self.org)
        logger.debug(f"request: {type(request)}, x-request-id: {request_id}, contents:\n{request}")
        return continuation(new_details, request)


def update_client_with_interceptor(client: SynchronousFlyteClient, org: str) -> SynchronousFlyteClient:
    """Updates SynchronousFlyteClient inplace with an interceptor with org."""
    if org == "":
        # There is no org, so no need to intercept
        return client

    # Intercept calls to FlyteRemote and add org to grpc metadata
    org_interceptor = OrgInterceptor(org=org)
    previous_channel = client._channel
    new_channel = grpc.intercept_channel(previous_channel, org_interceptor)

    client._channel = new_channel
    client._stub = AdminServiceStub(new_channel)
    client._signal = SignalServiceStub(new_channel)
    client._dataproxy_stub = DataProxyServiceStub(new_channel)

    return client


def intercept_channel_with_org(org: str, channel: grpc.Channel):
    if org == "":
        return channel

    org_interceptor = OrgInterceptor(org=org)
    return grpc.intercept_channel(channel, org_interceptor)
