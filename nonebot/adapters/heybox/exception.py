import json

from nonebot.drivers import Response
from nonebot.exception import ActionFailed as BaseActionFailed
from nonebot.exception import AdapterException
from nonebot.exception import ApiNotAvailable as BaseApiNotAvailable
from nonebot.exception import NetworkError as BaseNetworkError
from nonebot.exception import NoLogException as BaseNoLogException


class HeyboxAdapterException(AdapterException):
    def __init__(self, *args: object):
        super().__init__("Heybox", *args)


class NoLogException(BaseNoLogException, HeyboxAdapterException): ...


class ActionFailed(BaseActionFailed, HeyboxAdapterException):
    def __init__(self, response: Response):
        self.response = response

        self.body: dict | None = None
        if response.content:
            try:
                self.body = json.loads(response.content)
            except Exception:
                ...

    @property
    def status_code(self) -> int:
        return self.response.status_code

    @property
    def msg(self) -> int | None:
        return None if self.body is None else self.body.get("msg", None)

    def __repr__(self) -> str:
        args = ("msg",)
        return (
            f"<ActionFailed: {self.status_code}, "
            + ", ".join(f"{k}={v}" for k in args if (v := getattr(self, k)) is not None)
            + ">"
        )


class PermissionDenied(ActionFailed):
    def __repr__(self) -> str:
        return f"<PermissionDenied: {self.msg}>"


class NetworkError(BaseNetworkError, HeyboxAdapterException):
    def __init__(self, msg: str | None = None):
        super().__init__()
        self.msg: str = msg or ""

    def __repr__(self):
        return f"<NetWorkError message={self.msg}>"

    def __str__(self):
        return self.__repr__()


class ApiNotAvailable(BaseApiNotAvailable, HeyboxAdapterException):
    pass
