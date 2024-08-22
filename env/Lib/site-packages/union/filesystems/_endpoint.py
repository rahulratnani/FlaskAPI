import os

import grpc

from union.filesystems._middleware import (
    StreamStreamClientAuthInterceptor,
    StreamUnaryClientAuthInterceptor,
    UnaryStreamClientAuthInterceptor,
    UnaryUnaryClientAuthInterceptor,
)

_ENDPOINT = "localhost:8080"
MAX_MESSAGE_LENGTH = 10 * 1024 * 1024


def _get_endpoint() -> str:
    endpoint = os.environ.get("OBJECT_STORE_ENDPOINT")
    if endpoint is not None and endpoint != "":
        return endpoint

    endpoint = os.environ.get("object_store_endpoint")
    if endpoint is not None and endpoint != "":
        return endpoint

    return _ENDPOINT


def _is_remote(endpoint: str) -> bool:
    return endpoint != _ENDPOINT


def _create_channel():
    endpoint = _get_endpoint()

    interceptors = None
    if _is_remote(endpoint):
        unary_unary_auth_interceptor = UnaryUnaryClientAuthInterceptor()
        unary_stream_auth_interceptor = UnaryStreamClientAuthInterceptor()
        stream_unary_auth_interceptor = StreamUnaryClientAuthInterceptor()
        stream_stream_auth_interceptor = StreamStreamClientAuthInterceptor()
        interceptors = [
            unary_unary_auth_interceptor,
            unary_stream_auth_interceptor,
            stream_unary_auth_interceptor,
            stream_stream_auth_interceptor,
        ]

    channel = grpc.aio.insecure_channel(
        endpoint,
        options=[
            ("grpc.max_message_length", MAX_MESSAGE_LENGTH),
            ("grpc.max_send_message_length", MAX_MESSAGE_LENGTH),
            ("grpc.max_receive_message_length", MAX_MESSAGE_LENGTH),
        ],
        interceptors=interceptors,
    )
    return channel
