import typing
from logging import getLogger
from typing import AsyncIterable, Callable

import grpc

DEFAULT_KUBERNETES_TOKEN_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/token"

logger = getLogger(__name__)


# See https://github.com/grpc/grpc/issues/34537 and proposed fix https://github.com/grpc/grpc/pull/36487
# Unfortunately we can't use one interceptor for unary and streaming endpoints
class ServiceAccountMetadataInterceptor:
    def __init__(self):
        self._service_account_token = self._read_service_account_token()

    def _read_service_account_token(self) -> typing.Optional[None]:
        try:
            with open(DEFAULT_KUBERNETES_TOKEN_PATH, "r") as token_file:
                token = token_file.read()
            return token
        except Exception as e:
            logger.debug(f"Error reading service account token: {e}, not adding to request")
            return None

    def _inject_default_metadata(self, client_call_details: grpc.aio.ClientCallDetails) -> grpc.aio.ClientCallDetails:
        if self._service_account_token is None:
            return client_call_details

        old_metadata = client_call_details.metadata or []
        new_metadata = old_metadata + [("authorization", f"Bearer {self._service_account_token}")]

        new_details = grpc.aio.ClientCallDetails(
            method=client_call_details.method,
            timeout=client_call_details.timeout,
            metadata=new_metadata,
            credentials=client_call_details.credentials,
            wait_for_ready=client_call_details.wait_for_ready,
        )
        return new_details


class UnaryUnaryClientAuthInterceptor(grpc.aio.UnaryUnaryClientInterceptor, ServiceAccountMetadataInterceptor):
    async def intercept_unary_unary(
        self, continuation: Callable, client_call_details: grpc.aio.ClientCallDetails, request: typing.Any
    ) -> typing.Any:
        new_client_call_details = super()._inject_default_metadata(client_call_details)
        return await continuation(new_client_call_details, request)


class UnaryStreamClientAuthInterceptor(grpc.aio.UnaryStreamClientInterceptor, ServiceAccountMetadataInterceptor):
    async def intercept_unary_stream(
        self, continuation: Callable, client_call_details: grpc.aio.ClientCallDetails, request: any
    ) -> AsyncIterable:
        new_client_call_details = super()._inject_default_metadata(client_call_details)
        return await continuation(new_client_call_details, request)


class StreamUnaryClientAuthInterceptor(grpc.aio.StreamUnaryClientInterceptor, ServiceAccountMetadataInterceptor):
    async def intercept_stream_unary(
        self,
        continuation: Callable,
        client_call_details: grpc.aio.ClientCallDetails,
        request_iterator: any,
    ) -> grpc.aio.StreamUnaryCall:
        new_client_call_details = super()._inject_default_metadata(client_call_details)
        return await continuation(new_client_call_details, request_iterator)


class StreamStreamClientAuthInterceptor(grpc.aio.StreamStreamClientInterceptor, ServiceAccountMetadataInterceptor):
    async def intercept_stream_stream(
        self,
        continuation: Callable,
        client_call_details: grpc.aio.ClientCallDetails,
        request_iterator: typing.AsyncIterator[any],
    ) -> grpc.aio.Call:
        new_client_call_details = super()._inject_default_metadata(client_call_details)
        return await continuation(new_client_call_details, request_iterator)
