import asyncio
import colorsys
from enum import Enum
from io import BytesIO

import spotipy
import yaml
from colorthief import ColorThief
from curl_cffi import requests
from pydantic import BaseModel
from rich.console import Console
from rich.progress import Progress
from spotipy.oauth2 import SpotifyPKCE
from tapo import (
    ApiClient,
    ColorLightHandler,
    RgbicLightStripHandler,
    RgbLightStripHandler,
)
from yaml.parser import ParserError

console = Console()


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


class SpotifyDetails(BaseModel):
    client_id: str
    redirect_uri: str


class Config(BaseModel):
    email: str
    password: str
    devices: list[Device]
    spotify: SpotifyDetails

    model_config = {"extra": "forbid", "frozen": True}


def load_config() -> Config:
    try:
        with open("config.yaml", "r") as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        console.print("Error config file missing", style="bold red")
        raise
    except ParserError:
        console.print("YAML file corrupted", style="bold red")
        raise
    except Exception:
        console.print("Unknown error", style="bold red")
        raise

    return Config.model_validate(data)


async def get_client(
    device_type: DeviceType, ip: str, client: ApiClient
) -> ColorLightHandler | RgbLightStripHandler | RgbicLightStripHandler:
    match device_type:
        case DeviceType.L530:
            return await client.l530(ip)
        case DeviceType.L535:
            return await client.l535(ip)
        case DeviceType.L630:
            return await client.l630(ip)
        case DeviceType.L900:
            return await client.l900(ip)
        case DeviceType.L920:
            return await client.l920(ip)
        case DeviceType.L930:
            return await client.l930(ip)


def get_color(file: BytesIO) -> tuple[int, int]:
    def get_hs(r: int, g: int, b: int) -> tuple[int, int]:
        h, s, _ = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        hue = max(0, int(round(h * 360)))
        sat = max(1, int(round(s * 100)))
        return (hue, sat)

    cf = ColorThief(file)
    r, g, b = cf.get_color(quality=1)
    hue, sat = get_hs(r, g, b)
    console.log(hue, sat)
    if sat <= 10:
        console.log("low sat, changing")
        palette = cf.get_palette(color_count=5)
        best = max(
            palette,
            key=lambda c: colorsys.rgb_to_hsv(c[0] / 255, c[1] / 255, c[2] / 255)[1],
        )
        r, g, b = best
        hue, sat = get_hs(r, g, b)
        console.log("Changed", hue, sat)
        return (hue, sat)
    return (hue, sat)


async def main():
    config = load_config()
    sp = spotipy.Spotify(
        auth_manager=SpotifyPKCE(
            client_id=config.spotify.client_id,
            redirect_uri=config.spotify.redirect_uri,
            scope=["user-read-playback-state"],
        )
    )
    client = ApiClient(config.email, config.password)
    devices: list[
        ColorLightHandler | RgbLightStripHandler | RgbicLightStripHandler
    ] = []
    for device in config.devices:
        devices.append(await get_client(device.type, device.ip, client))
    with Progress() as progress:
        task = progress.add_task("[yelllo] Testing devices", total=len(devices))
        for device in devices:
            await device.on()
            await asyncio.sleep(5)
            progress.update(task, advance=0.5)
            await device.off()
            await asyncio.sleep(5)
            progress.update(task, advance=0.5)
    console.print("Devices successfully tested", style="bold green")
    current_uri = None
    player_state = None
    while True:
        playback_state = sp.current_playback()
        if (
            playback_state
            and playback_state["item"]["uri"] != current_uri
            and playback_state["is_playing"]
        ):
            player_state = PlayerState.Playing
            console.print("Changing color", style="bold green")
            current_uri = playback_state["item"]["uri"]
            image_url = playback_state["item"]["album"]["images"][0]["url"]
            console.log(image_url)
            image_data = requests.get(image_url).content
            hue, sat = get_color(BytesIO(image_data))
            for device in devices:
                # Fix for paused music. Shouldn't be necessary according to docs of set_hue_saturation, but without this device doesn't power on when sending same hue, sat values.
                await device.on()
                await asyncio.sleep(2)
                await device.set_hue_saturation(hue, sat)
        elif (
            playback_state
            and not playback_state["is_playing"]
            and player_state is not PlayerState.Paused
        ):
            player_state = PlayerState.Paused
            console.print("Music paused", style="bold yellow")
            current_uri = None
            for device in devices:
                await device.off()
        elif playback_state is None and player_state is not PlayerState.Stopped:
            player_state = PlayerState.Stopped
            console.print("No music playing", style="bold yellow")
            for device in devices:
                await device.off()
        if player_state == PlayerState.Playing:
            await asyncio.sleep(2)
        else:
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
