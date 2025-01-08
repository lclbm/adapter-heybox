from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterable, Self, Type, TypedDict, Union

from typing_extensions import override

from nonebot.adapters import Message as BaseMessage
from nonebot.adapters import MessageSegment as BaseMessageSegment

from .model import MessageData
from .utils import unescape


class MessageSegment(BaseMessageSegment["Message"]):
    @classmethod
    @override
    def get_message_class(cls) -> Type["Message"]:
        return Message

    @staticmethod
    def text(content: str) -> "Text":
        return Text("text", {"text": content})

    @staticmethod
    def image(url: str, width: int, height: int) -> "Image":
        return Image("image", {"url": url, "width": width, "height": height})

    @staticmethod
    def local_image(
        bytes: bytes, width: int, height: int, filename: str
    ) -> "LocalImage":
        return LocalImage(
            "local_image",
            {"bytes": bytes, "width": width, "height": height, "filename": filename},
        )

    @staticmethod
    def mention(user_id: str | int) -> "Mention":
        return Mention("mention", {"user_id": user_id})

    @override
    def __add__(
        self, other: Union[str, "MessageSegment", Iterable["MessageSegment"]]
    ) -> "Message":
        return Message(self) + (
            MessageSegment.text(other) if isinstance(other, str) else other
        )

    @override
    def __radd__(
        self, other: Union[str, "MessageSegment", Iterable["MessageSegment"]]
    ) -> "Message":
        return (
            MessageSegment.text(other) if isinstance(other, str) else Message(other)
        ) + self

    @override
    def is_text(self) -> bool:
        return self.type == "text"


class _TextData(TypedDict):
    text: str


@dataclass
class Text(MessageSegment):
    if TYPE_CHECKING:
        data: _TextData

    @override
    def __str__(self) -> str:
        return self.data["text"]


class _ImageData(TypedDict):
    url: str
    wdith: int
    height: int


@dataclass
class Image(MessageSegment):
    if TYPE_CHECKING:
        data: _ImageData

    @override
    def __str__(self) -> str:
        return f"![]({self.data['url']})"


class _LocalImageData(TypedDict):
    bytes: bytes
    width: int
    height: int
    filename: str


@dataclass
class LocalImage(MessageSegment):
    if TYPE_CHECKING:
        data: _LocalImageData

    @override
    def __str__(self) -> str:
        return f"<local_image[{self.type}]>"


class _MentionData(TypedDict):
    user_id: str | int


@dataclass
class Mention(MessageSegment):
    if TYPE_CHECKING:
        data: _MentionData

    @override
    def __str__(self) -> str:
        return "@{id:" + str(self.data["user_id"]) + "}"


class Message(BaseMessage[MessageSegment]):
    @classmethod
    @override
    def get_segment_class(cls) -> Type[MessageSegment]:
        return MessageSegment

    @staticmethod
    @override
    def _construct(msg: str) -> Iterable[MessageSegment]:
        yield Text("text", {"text": unescape(msg)})

    @override
    def __add__(
        self, other: Union[str, MessageSegment, Iterable[MessageSegment]]
    ) -> Self:
        return super().__add__(
            MessageSegment.text(other) if isinstance(other, str) else other
        )

    @override
    def __radd__(
        self, other: Union[str, MessageSegment, Iterable[MessageSegment]]
    ) -> Self:
        return super().__radd__(
            MessageSegment.text(other) if isinstance(other, str) else other
        )

    @classmethod
    def from_room_message(cls, message: MessageData) -> Self:
        msg = cls()
        if message.msg:
            msg.extend(Message(message.msg))
        return msg

    def extract_content(self) -> str:
        return "".join(
            str(seg) for seg in self if seg.type in ("text", "mention", "image")
        )
