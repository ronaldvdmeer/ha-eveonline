"""The Eve Online integration."""

from __future__ import annotations

import logging
from datetime import timedelta

import aiohttp
from eveonline import EveOnlineClient, EveOnlineError
from eveonline.models import ServerStatus
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

type EveOnlineConfigEntry = ConfigEntry[EveOnlineCoordinator]


class EveOnlineCoordinator(DataUpdateCoordinator[ServerStatus]):
    """Coordinator to poll Eve Online server status."""

    config_entry: EveOnlineConfigEntry

    def __init__(self, hass: HomeAssistant, entry: EveOnlineConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
            config_entry=entry,
        )
        session = async_get_clientsession(hass)
        self.client = EveOnlineClient(session=session)

    async def _async_update_data(self) -> ServerStatus:
        """Fetch server status from Eve Online ESI API."""
        try:
            return await self.client.async_get_server_status()
        except EveOnlineError as err:
            raise UpdateFailed(f"Error communicating with Eve Online API: {err}") from err
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Connection error: {err}") from err


async def async_setup_entry(hass: HomeAssistant, entry: EveOnlineConfigEntry) -> bool:
    """Set up Eve Online from a config entry."""
    coordinator = EveOnlineCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: EveOnlineConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
