import asyncio
import colorsys
from io import BytesIO

import yaml
from colorthief import ColorThief
from requests_cache import CachedSession
from rich.progress import Progress
from tapo import (
    ApiClient,
    ColorLightHandler,
    RgbicLightStripHandler,
    RgbLightStripHandler,
)
from yaml.parser import ParserError

from console import console
from model import Config, DeviceType, PlayerState
from spotify import get_spotify_client

session = CachedSession(cache_control=True)


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
    console.log(f"Hue: {hue} Sat: {sat}, RGB: {(r, g, b)}")
    if sat <= 10:
        console.log("low sat, changing")
        palette = cf.get_palette(quality=1)
        best = max(
            palette,
            key=lambda c: colorsys.rgb_to_hsv(c[0] / 255, c[1] / 255, c[2] / 255)[1],
        )
        r, g, b = best
        hue, sat = get_hs(r, g, b)
        console.log(f"Hue: {hue} Sat: {sat}, RGB: {(r, g, b)}")
        return (hue, sat)
    return (hue, sat)


async def main():
    config = load_config()
    with console.status("Testing spotify credentials"):
        sp = get_spotify_client(config.spotify)
        try:
            sp.login()
        except Exception as e:
            console.log("Spotify Login Error", style="bold red")
            raise e

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
        playback_state = sp.current_playback
        if (
            playback_state
            and playback_state.uri != current_uri
            and playback_state.is_playing
        ):
            player_state = PlayerState.Playing
            console.print("Changing color", style="bold green")
            current_uri = playback_state.uri
            image_url = playback_state.image_url
            console.log(image_url)
            image_data = session.get(image_url).content
            hue, sat = get_color(BytesIO(image_data))
            for device in devices:
                # Fix for paused music. Shouldn't be necessary according to docs of set_hue_saturation, but without this device doesn't power on when sending same hue, sat values.
                await device.on()
                await asyncio.sleep(2)
                await device.set_hue_saturation(hue, sat)
        elif (
            playback_state
            and not playback_state.is_playing
            and player_state is not PlayerState.Paused
        ):
            player_state = PlayerState.Paused
            current_uri = None
            console.print("Music paused", style="bold yellow")
            if config.app_config.off_on_pause:
                for device in devices:
                    await device.off()
        elif playback_state is None and player_state is not PlayerState.Stopped:
            player_state = PlayerState.Stopped
            current_uri = None
            console.print("No music playing", style="bold yellow")
            if config.app_config.off_on_stop:
                for device in devices:
                    await device.off()
        if player_state == PlayerState.Playing:
            await asyncio.sleep(2)
        else:
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
