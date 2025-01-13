import asyncio
import json
from typing import Any

from nonebot.compat import type_validate_python
from nonebot.drivers import (
    URL,
    Driver,
    HTTPClientMixin,
    Request,
    WebSocket,
    WebSocketClientMixin,
)
from nonebot.exception import WebSocketClosed
from nonebot.message import handle_event
from nonebot.utils import escape_tag
from typing_extensions import override

from nonebot import get_plugin_config
from nonebot.adapters import Adapter as BaseAdapter

from .bot import Bot
from .config import BotInfo, Config
from .event import EVENT_CLASSES, Event, HeartbeatMetaEvent
from .exception import ApiNotAvailable
from .model import MessageDict
from .utils import API, log

RECONNECT_INTERVAL = 10.0
HEARTBEAT_INTERVAL = 20.0


class Adapter(BaseAdapter):
    @override
    def __init__(self, driver: Driver, **kwargs: Any):
        super().__init__(driver, **kwargs)
        self.heybox_config: Config = get_plugin_config(Config)
        self.tasks: set[asyncio.Task] = set()
        self.setup()

    @classmethod
    @override
    def get_name(cls) -> str:
        return "Heybox"

    def setup(self) -> None:
        if not isinstance(self.driver, HTTPClientMixin):
            raise RuntimeError(
                f"Current driver {self.config.driver} does not support "
                "http client requests! "
                f"{self.get_name()} Adapter need a HTTPClient Driver to work."
            )
        if not isinstance(self.driver, WebSocketClientMixin):
            raise RuntimeError(
                f"Current driver {self.config.driver} does not support "
                "websocket client! "
                f"{self.get_name()} Adapter need a WebSocketClient Driver to work."
            )
        self.on_ready(self.start_forward)
        self.driver.on_shutdown(self.stop_forward)

    @override
    async def _call_api(self, bot: Bot, api: str, **data: Any) -> Any:
        log("DEBUG", f"Bot {bot.bot_info.id} calling API <y>{api}</y>")
        api_handler: API | None = getattr(bot.__class__, api, None)
        if api_handler is None:
            raise ApiNotAvailable
        return await api_handler(bot, **data)

    async def start_forward(self) -> None:
        for bot_info in self.heybox_config.heybox_bots:
            task = asyncio.create_task(self.run_bot(bot_info))
            task.add_done_callback(self.tasks.discard)
            self.tasks.add(task)

    async def stop_forward(self) -> None:
        for task in self.tasks:
            if not task.done():
                task.cancel()

        await asyncio.gather(
            *(asyncio.wait_for(task, timeout=10) for task in self.tasks),
            return_exceptions=True,
        )

    async def run_bot(self, bot_info: BotInfo):
        bot = Bot(self, bot_info.id, bot_info)
        ws_url = URL(
            f"wss://chat.xiaoheihe.cn/chatroom/ws/connect?chat_os_type=bot&client_type=heybox_chat&chat_version=1.22.2&token={bot_info.token}"
        )

        task = asyncio.create_task(self._forward_ws(bot, ws_url))
        task.add_done_callback(self.tasks.discard)
        self.tasks.add(task)

    async def _forward_ws(self, bot: Bot, ws_url: URL) -> None:
        request = Request("GET", ws_url, timeout=30.0)
        heartbeat_task: asyncio.Task | None = None

        while True:
            try:
                async with self.websocket(request) as ws:
                    log(
                        "DEBUG",
                        f"WebSocket Connection to {escape_tag(str(ws_url))} established",
                    )

                    if bot.self_id not in self.bots:
                        self.bot_connect(bot)
                        log(
                            "INFO",
                            f"<y>Bot {escape_tag(bot.self_id)}</y> connected",
                        )

                    try:
                        heartbeat_task = asyncio.create_task(self._heartbeat(ws))
                        await self._loop(bot, ws)

                    except WebSocketClosed as e:
                        log(
                            "ERROR",
                            "<r><bg #f8bbd0>WebSocket Closed</bg #f8bbd0></r>",
                            e,
                        )
                    except Exception as e:
                        log(
                            "ERROR",
                            (
                                "<r><bg #f8bbd0>"
                                "Error while process data from websocket "
                                f"{escape_tag(str(ws_url))}. Trying to reconnect..."
                                "</bg #f8bbd0></r>"
                            ),
                            e,
                        )
                    finally:
                        if heartbeat_task:
                            heartbeat_task.cancel()
                            heartbeat_task = None
                        if bot.self_id in self.bots:
                            self.bot_disconnect(bot)

            except Exception as e:
                log(
                    "ERROR",
                    (
                        "<r><bg #f8bbd0>"
                        "Error while setup websocket to "
                        f"{escape_tag(str(ws_url))}. Trying to reconnect..."
                        "</bg #f8bbd0></r>"
                    ),
                    e,
                )

            await asyncio.sleep(RECONNECT_INTERVAL)

    @staticmethod
    def data_to_event(data: str) -> Event | None:
        if data == "PONG":
            return HeartbeatMetaEvent()

        json_data: MessageDict = json.loads(data)
        if not (notify_type := json_data.get("notify_type")):
            return None
        event_class = EVENT_CLASSES.get(notify_type)

        return type_validate_python(event_class, json_data["data"])

    async def _heartbeat(self, ws: WebSocket) -> None:
        """心跳"""
        while True:
            log("TRACE", f"Send Heartbeat")
            try:
                await ws.send("PING")
            except Exception as e:
                log("WARNING", "Error while sending heartbeat, Ignored!", e)
            await asyncio.sleep(HEARTBEAT_INTERVAL)

    async def _loop(self, bot: Bot, ws: WebSocket):
        """接收并处理事件"""
        while True:
            data = await ws.receive()
            log(
                "TRACE",
                f"Received data: {escape_tag(repr(data))}",
            )

            try:
                event = self.data_to_event(data)
            except Exception as e:
                log(
                    "ERROR",
                    "<r><bg #f8bbd0>Failed to parse event. "
                    f"Raw: {escape_tag(data)}</bg #f8bbd0></r>",
                    e,
                )
                continue
            if not event:
                continue
            await handle_event(bot, event)
