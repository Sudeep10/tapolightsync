from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class DeviceType(str, Enum):
    L530 = "L530"
    L535 = "L535"
    L630 = "L630"
    L900 = "L900"
    L920 = "L920"
    L930 = "L930"


class PlayerState(str, Enum):
    Playing = "playing"
    Paused = "paused"
    Stopped = "stopped"


class Device(BaseModel):
    type: DeviceType
    ip: str


class SpotifyLoginType(str, Enum):
    Oauth = "oauth"
    Connect = "connect"


class SpotifyOauthDetails(BaseModel):
    login_type: Literal[SpotifyLoginType.Oauth]
    client_id: str
    redirect_uri: str


class SpotifyConnectDetails(BaseModel):
    login_type: Literal[SpotifyLoginType.Connect]
    email: str
    sp_dc: str
    sp_t: str


SpotifyDetails = SpotifyOauthDetails | SpotifyConnectDetails


class AppConfig(BaseModel):
    off_on_pause: bool = True
    off_on_stop: bool = True


class Config(BaseModel):
    email: str
    password: str
    devices: list[Device]
    spotify: SpotifyDetails
    app_config: AppConfig = Field(default_factory=AppConfig)

    model_config = {"extra": "forbid", "frozen": True}
