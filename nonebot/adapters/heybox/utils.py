import random
import string
import time
from functools import partial
from typing import (
    TYPE_CHECKING,
    Awaitable,
    Callable,
    Concatenate,
    Generic,
    ParamSpec,
    TypeVar,
    overload,
)

from nonebot.utils import logger_wrapper

if TYPE_CHECKING:
    from .bot import Bot

B = TypeVar("B", bound="Bot")
R = TypeVar("R")
P = ParamSpec("P")

log = logger_wrapper("Heybox")


def escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def unescape(s: str) -> str:
    return s.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")


def gen_nonce():
    return str(time.time()).split(".")[0] + "".join(
        random.choices(string.ascii_letters + string.digits, k=16)
    )


class API(Generic[B, P, R]):
    def __init__(self, func: Callable[Concatenate[B, P], Awaitable[R]]) -> None:
        self.func = func

    def __set_name__(self, owner: B, name: str) -> None:
        self.name = name

    @overload
    def __get__(self, obj: None, objtype: B) -> "API[B, P, R]": ...

    @overload
    def __get__(self, obj: B, objtype: B | None) -> Callable[P, Awaitable[R]]: ...

    def __get__(
        self, obj: B | None, objtype: B | None = None
    ) -> "API[B, P, R] | Callable[P, Awaitable[R]]":
        if obj is None:
            return self

        return partial(obj.call_api, self.name)  # type: ignore

    async def __call__(self, inst: B, *args: P.args, **kwds: P.kwargs) -> R:
        return await self.func(inst, *args, **kwds)
