import os
from dataclasses import dataclass
from typing import Protocol

import spotipy
from spotapi import Config as SpotApiConfig
from spotapi import JSONSaver, Login, NoopLogger, PlayerStatus, WebSocketError
from spotipy.oauth2 import SpotifyPKCE

from console import console
from model import SpotifyDetails, SpotifyLoginType


class NotLoggedIn(Exception):
    """Raised when SpotifyClient methods are used before login"""


@dataclass(frozen=True)
class TrackDetails:
    uri: str
    image_url: str
    is_playing: bool


class SpotifyClient(Protocol):
    def login(self) -> None:
        pass

    @property
    def current_playback(self) -> TrackDetails | None:
        pass


@dataclass()
class SpotifyOauthClient:
    client_id: str
    redirect_uri: str
    _logged_in: bool = False
    _client: spotipy.Spotify | None = None

    def login(self):
        self._client = spotipy.Spotify(
            auth_manager=SpotifyPKCE(
                client_id=self.client_id,
                redirect_uri=self.redirect_uri,
                scope=["user-read-playback-state"],
            )
        )
        self._logged_in = True

    @property
    def current_playback(self) -> TrackDetails | None:
        if not self._logged_in or self._client is None:
            raise NotLoggedIn("Call login() before current_playback")
        playback_state = self._client.current_playback()
        if playback_state is None:
            return None
        track = playback_state["item"]
        if track is None:
            return None
        uri = track["uri"]
        image_url = playback_state["item"]["album"]["images"][0]["url"]
        if image_url is None:
            # fallback image
            image_url = "https://placehold.co/600x400/3366ff/FFFFFF/png"
        is_playing = playback_state["is_playing"]
        return TrackDetails(uri, image_url, is_playing)


@dataclass()
class SpotifyConnectClient:
    email: str
    sp_dc: str
    sp_t: str
    _logged_in: bool = False
    _client: Login | None = None
    _player_status: PlayerStatus | None = None

    def login(self):
        cfg = SpotApiConfig(logger=NoopLogger())
        cookies = {"sp_dc": self.sp_dc, "sp_t": self.sp_t}
        session_data = {
            "identifier": self.email,
            "cookies": cookies,
        }
        if os.path.exists("./sessions.json"):
            self._client = Login.from_saver(JSONSaver(), cfg, self.email)
        else:
            self._client = Login.from_cookies(session_data, cfg)
            self._client.save(JSONSaver())
        self._logged_in = True
        self._player_status = PlayerStatus(self._client)

    @property
    def current_playback(self) -> TrackDetails | None:
        if not self._logged_in or self._client is None or self._player_status is None:
            raise NotLoggedIn("Call login() before current_playback")
        try:
            self._player_status.active_device_id
        except ValueError:
            return None
        except (WebSocketError, KeyError, TimeoutError):
            self._player_status = PlayerStatus(self._client)
            console.log("Reconnecting")
        except Exception as e:
            raise e
        playback_state = self._player_status.state
        if playback_state.track is None:
            return None
        uri = playback_state.track.uri
        image_url = None
        if playback_state.track.metadata is not None:
            image_url = playback_state.track.metadata.image_large_url
        if image_url and image_url.startswith("spotify"):
            image_url = "https://i.scdn.co/image/" + image_url.split(":")[-1]
        if image_url is None:
            # fallback image
            image_url = "https://placehold.co/600x400/3366ff/FFFFFF/png"
        is_playing = not playback_state.is_paused
        return TrackDetails(uri, image_url, is_playing)


def get_spotify_client(config: SpotifyDetails) -> SpotifyClient:
    if config.login_type == SpotifyLoginType.Oauth:
        return SpotifyOauthClient(config.client_id, config.redirect_uri)
    else:
        return SpotifyConnectClient(config.email, config.sp_dc, config.sp_t)
