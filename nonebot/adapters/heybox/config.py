from pydantic import BaseModel


class BotInfo(BaseModel):
    id: str
    token: str


class Config(BaseModel):
    heybox_bots: list[BotInfo]
