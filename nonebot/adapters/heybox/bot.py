import json
from typing import TYPE_CHECKING, Any, Union, cast

from nonebot.drivers import Request, Response
from typing_extensions import override

from nonebot.adapters import Bot as BaseBot

from .config import BotInfo
from .event import Event, UserIMMessageEvent
from .exception import MESSAGE_ERROR_MAP, ActionFailed, NetworkError, SendMessageError
from .message import Image, LocalImage, Mention, Message, MessageSegment
from .model import MessageSendDataDict
from .utils import API, gen_nonce, log

if TYPE_CHECKING:
    from .adapter import Adapter


class Bot(BaseBot):
    def __init__(self, adapter: "Adapter", self_id: str, bot_info: BotInfo):
        super().__init__(adapter, self_id)
        self.bot_info = bot_info

        self._heychat_ack_id = -1

    def add_heychat_ack_id(self) -> str:
        if self._heychat_ack_id >= 99999:
            self._heychat_ack_id = -1

        self._heychat_ack_id += 1
        return str(self._heychat_ack_id)

    async def _request(self, request: Request) -> Any:
        try:
            response = await self.adapter.request(request)
        except Exception as e:
            raise NetworkError(f"API request failed, {e}") from e

        return self._handle_response(response)

    def _handle_response(self, response: Response) -> Any:
        if 200 <= response.status_code < 300:
            resp = response.content and json.loads(response.content)

            if resp.get("status") != "ok":
                msg = resp.get("msg")
                raise MESSAGE_ERROR_MAP.get(msg, SendMessageError)(response)

            return resp
        else:
            raise ActionFailed(response)

    @staticmethod
    def _prepare_message(message: str | Message | MessageSegment) -> Message:
        _message = MessageSegment.text(message) if isinstance(message, str) else message
        _message = _message if isinstance(_message, Message) else Message(_message)
        return _message

    async def _prepare_image(self, message: Message) -> Message:
        for idx, seg in enumerate(message[:]):
            if isinstance(seg, LocalImage):
                width, height = seg.data["width"], seg.data["height"]
                url = await self.upload_image(
                    bytes=seg.data["bytes"], filename=seg.data["filename"]
                )

                message[idx] = Image(
                    "image", {"url": url, "width": width, "height": height}
                )

        return message

    @API
    async def send_channel_msg(
        self,
        *,
        data: MessageSendDataDict,
    ):
        request = Request(
            "POST",
            "https://chat.xiaoheihe.cn/chatroom/v2/channel_msg/send",
            params={
                "chat_os_type": "bot",
                "chat_version": "1.22.2",
                "nonce": gen_nonce(),
            },
            headers={"token": self.bot_info.token},
            json=data,
        )
        return await self._request(request)

    @API
    async def upload_image(self, *, bytes: bytes, filename: str) -> str:
        request = Request(
            "POST",
            "https://chat-upload.xiaoheihe.cn/upload",
            headers={"token": self.bot_info.token},
            files=[("file", (filename, bytes, None))],
        )
        resp = await self._request(request)
        return resp["result"]["url"]

    async def send_to_channel(
        self,
        room_id: str,
        channel_id: str,
        message: Union[str, Message, MessageSegment],
        reply_id: str | None = None,
    ):
        message = self._prepare_message(message)
        message = await self._prepare_image(message)

        kwargs: MessageSendDataDict = {
            "msg_type": 10,
            "room_id": room_id,
            "channel_id": channel_id,
            "heychat_ack_id": self.add_heychat_ack_id(),
        }

        if reply_id:
            kwargs["reply_id"] = reply_id

        # 处理@
        if mentions := message["mention"]:
            kwargs["at_user_id"] = ",".join(
                str(cast(Mention, mention).data["user_id"]) for mention in mentions
            )

        # 处理图片
        if images := message["image"]:
            d = {
                "img_files_info": [
                    {k: cast(Image, image).data[k] for k in ("url", "width", "height")}
                    for image in images
                ]
            }
            kwargs["addition"] = json.dumps(d)

        kwargs["msg"] = message.extract_content().replace("\n", "<br>")

        return await self.send_channel_msg(data=kwargs)

    @override
    async def send(
        self,
        event: Event,
        message: Union[str, Message, MessageSegment],
        is_reply: bool = True,
    ) -> Any:
        if isinstance(event, UserIMMessageEvent):
            return await self.send_to_channel(
                event.room_id,
                event.channel_id,
                message,
                reply_id=event.im_seq if is_reply else None,
            )

        raise RuntimeError("Event cannot be replied to!")
