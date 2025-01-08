from enum import StrEnum
from typing import Literal, TypeVar

from nonebot.compat import model_dump
from nonebot.utils import escape_tag
from typing_extensions import override

from nonebot.adapters import Event as BaseEvent

from .exception import NoLogException
from .message import Message
from .model import MessageData


class EventType(StrEnum):
    HEARTBEAT = "HEARTBEAT"
    USER_IM_MESSAGE = "USER_IM_MESSAGE"


class Event(BaseEvent):
    __type__: EventType

    @override
    def get_event_name(self) -> str:
        return self.__type__

    @override
    def get_event_description(self) -> str:
        return escape_tag(str(model_dump(self)))

    @override
    def get_message(self) -> Message:
        raise ValueError("Event has no message!")

    @override
    def get_plaintext(self) -> str:
        raise ValueError("Event has no message!")

    @override
    def get_user_id(self) -> str:
        raise ValueError("Event has no message!")

    @override
    def get_session_id(self) -> str:
        raise ValueError("Event has no message!")

    @override
    def is_tome(self) -> bool:
        return False


EVENT_CLASSES: dict[str, Event] = {}
E = TypeVar("E", bound="Event")


def register_event_class(event_class: E) -> E:
    EVENT_CLASSES[event_class.__type__.value] = event_class
    return event_class


# Meta Event
class MetaEvent(Event):
    """元事件"""

    @override
    def get_type(self) -> str:
        return "meta_event"


@register_event_class
class HeartbeatMetaEvent(MetaEvent):
    """心跳事件"""

    __type__ = EventType.HEARTBEAT

    @override
    def get_log_string(self):
        raise NoLogException


# Message Event
class MessageEvent(Event):
    @override
    def get_type(self) -> str:
        return "message"

    @override
    def is_tome(self) -> bool:
        return True


@register_event_class
class UserIMMessageEvent(MessageEvent, MessageData):
    __type__ = EventType.USER_IM_MESSAGE

    @override
    def get_message(self) -> Message:
        # tmp fix to remove space before text due to at not in content
        msg = Message.from_room_message(self)
        if msg and msg[0].type == "text":
            msg[0].data["text"] = msg[0].data["text"].lstrip()
        if not hasattr(self, "_message"):
            setattr(self, "_message", msg)
        return getattr(self, "_message")

    @override
    def get_plaintext(self) -> str:
        return self.get_message().extract_plain_text()

    @override
    def get_user_id(self) -> str:
        return str(self.user_id)

    @override
    def get_session_id(self) -> str:
        return f"room_{self.room_id}_{self.user_id}"

    @override
    def get_event_description(self) -> str:
        return escape_tag(
            f"Message {self.im_seq} from "
            f"{self.user_id}({self.nickname})@[Room:{self.room_id}] "
            f"[Channel:{self.channel_id}({self.channel_name})]: "
            f"{self.get_message()!r}"
        )
