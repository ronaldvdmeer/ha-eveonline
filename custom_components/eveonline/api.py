"""API helpers for Eve Online integration."""

from __future__ import annotations

from typing import cast

from aiohttp import ClientSession
from eveonline.auth import AbstractAuth

from homeassistant.helpers.config_entry_oauth2_flow import OAuth2Session


class EveOnlineOAuth2Auth(AbstractAuth):
    """Eve Online authentication using Home Assistant OAuth2 session.

    Bridges HA's OAuth2 token management to python-eveonline's AbstractAuth
    interface. HA handles token refresh automatically.
    """

    def __init__(
        self,
        websession: ClientSession,
        oauth_session: OAuth2Session,
    ) -> None:
        """Initialize the auth."""
        super().__init__(websession)
        self._oauth_session = oauth_session

    async def async_get_access_token(self) -> str:
        """Return a valid access token."""
        await self._oauth_session.async_ensure_token_valid()
        return cast(str, self._oauth_session.token["access_token"])
