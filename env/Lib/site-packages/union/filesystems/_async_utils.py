import asyncio
import functools
import inspect

from fsspec.asyn import AsyncFileSystem, async_methods, private


def sync(loop, func, *args, timeout=None, **kwargs):
    """
    Make loop run coroutine until it returns. Runs in other thread

    Examples
    --------
    >>> sync(fsspec.asyn.get_loop(), func, *args,
             timeout=timeout, **kwargs)
    """
    timeout = timeout if timeout else None  # convert 0 or 0.0 to None
    # NB: if the loop is not running *yet*, it is OK to submit work
    # and we will wait for it
    if loop is None or loop.is_closed():
        raise RuntimeError("Loop is not running")
    coro = func(*args, **kwargs)
    return loop.run_until_complete(coro)


def sync_wrapper(func, obj=None):
    """Given a function, make so can be called in async or blocking contexts

    Leave obj=None if defining within a class. Pass the instance if attaching
    as an attribute of the instance.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        self = obj or args[0]
        return sync(self.loop, func, *args, **kwargs)

    return wrapper


def mirror_sync_methods(obj):
    """Populate sync and async methods for obj

    For each method will create a sync version if the name refers to an async method
    (coroutine) and there is no override in the child class; will create an async
    method for the corresponding sync method if there is no implementation.

    Uses the methods specified in
    - async_methods: the set that an implementation is expected to provide
    - default_async_methods: that can be derived from their sync version in
      AbstractFileSystem
    - AsyncFileSystem: async-specific default coroutines
    """
    from fsspec import AbstractFileSystem

    for method in async_methods + dir(AsyncFileSystem):
        if not method.startswith("_"):
            continue
        smethod = method[1:]
        if private.match(method):
            isco = inspect.iscoroutinefunction(getattr(obj, method, None))
            unsync = getattr(getattr(obj, smethod, False), "__func__", None)
            is_default = unsync is getattr(AbstractFileSystem, smethod, "")
            if isco and is_default:
                mth = sync_wrapper(getattr(obj, method), obj=obj)
                setattr(obj, smethod, mth)
                if not mth.__doc__:
                    mth.__doc__ = getattr(getattr(AbstractFileSystem, smethod, None), "__doc__", "")


async def if_coro(result):
    if asyncio.iscoroutine(result):  # or inspect.iscoroutine,... and so on
        return await result
    else:
        return result
