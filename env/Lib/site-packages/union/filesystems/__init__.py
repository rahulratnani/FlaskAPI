"""Module for fsspec implementations."""

from union._logging import _init_global_loggers
from union.filesystems._unionfs import AsyncUnionFS
from union.filesystems._unionmetafs import AsyncUnionMetaFS

__all__ = ["AsyncUnionFS", "AsyncUnionMetaFS"]

# Configure loggers when our fsspec protocol is called, but union is not imported yet
_init_global_loggers()
