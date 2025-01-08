from typing import Literal, TypedDict

from pydantic import BaseModel


class MessageData(BaseModel):
    im_seq: str

    room_id: str
    channel_id: str
    user_id: int

    channel_name: str
    nickname: str

    msg: str
    send_time: int


class MessageDataDict(TypedDict):
    addition: str
    avatar: str
    avatar_decoration: dict
    bot: bool
    channel_id: str
    channel_name: str
    channel_type: int
    chatmobile_ack_id: str
    heybox_ack_id: str
    heychat_ack_id: str
    im_seq: str
    img: str
    img_info: dict
    level: int
    msg: str
    msg_type: int
    nickname: str
    receive_type: int
    roles: list[str]
    room_id: str
    room_nickname: str
    send_time: int
    state: int
    user_id: int


class MessageDict(TypedDict):
    sequence: int
    type: str
    notify_type: str
    data: MessageDataDict
    timestamp: int


class MessageSendDataDict(TypedDict):
    room_id: str
    channel_id: str
    msg_type: Literal[1, 3, 10]

    heychat_ack_id: int
    msg: str | None
    img: str | None

    reply_id: str | None
    at_user_id: str | None
    addition: str | None


class MessageSendData(BaseModel):
    room_id: str
    channel_id: str
    msg_type: Literal[1, 3, 10]

    heychat_ack_id: int
    msg: str | None
    img: str | None

    reply_id: str | None
    at_user_id: str | None
    addition: str | None
