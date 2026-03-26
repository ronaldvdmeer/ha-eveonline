"""The Eve Online integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta

import aiohttp
from eveonline import EveOnlineClient, EveOnlineError
from eveonline.models import (
    CharacterOnlineStatus,
    ServerStatus,
    SkillQueueEntry,
    WalletBalance,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.config_entry_oauth2_flow import (
    OAuth2Session,
    async_get_config_entry_implementation,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import EveOnlineOAuth2Auth
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


@dataclass
class EveOnlineData:
    """Combined server and character data."""

    server_status: ServerStatus
    character_id: int
    character_name: str
    character_online: CharacterOnlineStatus | None = None
    wallet_balance: WalletBalance | None = None
    skill_queue: list[SkillQueueEntry] = field(default_factory=list)


type EveOnlineConfigEntry = ConfigEntry[EveOnlineCoordinator]


class EveOnlineCoordinator(DataUpdateCoordinator[EveOnlineData]):
    """Coordinator to poll Eve Online server and character data."""

    config_entry: EveOnlineConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: EveOnlineConfigEntry,
        client: EveOnlineClient,
        character_id: int,
        character_name: str,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
            config_entry=entry,
        )
        self.client = client
        self.character_id = character_id
        self.character_name = character_name

    async def _async_update_data(self) -> EveOnlineData:
        """Fetch server status and character data from ESI."""
        try:
            server_status = await self.client.async_get_server_status()
        except (EveOnlineError, aiohttp.ClientError) as err:
            raise UpdateFailed(
                f"Error communicating with Eve Online API: {err}"
            ) from err

        # Fetch character data individually — don't fail coordinator on
        # individual endpoint errors (e.g. token scope issues)
        character_online = await self._fetch_character_online()
        wallet_balance = await self._fetch_wallet_balance()
        skill_queue = await self._fetch_skill_queue()

        return EveOnlineData(
            server_status=server_status,
            character_id=self.character_id,
            character_name=self.character_name,
            character_online=character_online,
            wallet_balance=wallet_balance,
            skill_queue=skill_queue,
        )

    async def _fetch_character_online(self) -> CharacterOnlineStatus | None:
        """Fetch character online status, returning None on failure."""
        try:
            return await self.client.async_get_character_online(self.character_id)
        except EveOnlineError as err:
            _LOGGER.debug("Failed to fetch character online status: %s", err)
            return None

    async def _fetch_wallet_balance(self) -> WalletBalance | None:
        """Fetch wallet balance, returning None on failure."""
        try:
            return await self.client.async_get_wallet_balance(self.character_id)
        except EveOnlineError as err:
            _LOGGER.debug("Failed to fetch wallet balance: %s", err)
            return None

    async def _fetch_skill_queue(self) -> list[SkillQueueEntry]:
        """Fetch skill queue, returning empty list on failure."""
        try:
            return await self.client.async_get_skill_queue(self.character_id)
        except EveOnlineError as err:
            _LOGGER.debug("Failed to fetch skill queue: %s", err)
            return []


async def async_setup_entry(hass: HomeAssistant, entry: EveOnlineConfigEntry) -> bool:
    """Set up Eve Online from a config entry."""
    implementation = await async_get_config_entry_implementation(hass, entry)
    oauth_session = OAuth2Session(hass, entry, implementation)

    session = async_get_clientsession(hass)
    auth = EveOnlineOAuth2Auth(session, oauth_session)
    client = EveOnlineClient(auth=auth)

    character_id: int = entry.data["character_id"]
    character_name: str = entry.data["character_name"]

    coordinator = EveOnlineCoordinator(
        hass, entry, client, character_id, character_name
    )
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: EveOnlineConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
