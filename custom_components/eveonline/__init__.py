"""The Eve Online integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta

import aiohttp
from eveonline import EveOnlineClient, EveOnlineError
from eveonline.models import (
    CharacterLocation,
    CharacterOnlineStatus,
    CharacterShip,
    CharacterSkillsSummary,
    IndustryJob,
    JumpFatigue,
    MailLabelsSummary,
    MarketOrder,
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

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]


@dataclass
class EveOnlineData:
    """Combined server and character data."""

    server_status: ServerStatus
    character_id: int
    character_name: str
    character_online: CharacterOnlineStatus | None = None
    wallet_balance: WalletBalance | None = None
    skill_queue: list[SkillQueueEntry] = field(default_factory=list)
    location: CharacterLocation | None = None
    ship: CharacterShip | None = None
    skills: CharacterSkillsSummary | None = None
    mail_labels: MailLabelsSummary | None = None
    industry_jobs: list[IndustryJob] = field(default_factory=list)
    market_orders: list[MarketOrder] = field(default_factory=list)
    jump_fatigue: JumpFatigue | None = None
    resolved_names: dict[int, str] = field(default_factory=dict)


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
        character_online = await self._fetch_optional(
            self.client.async_get_character_online, self.character_id
        )
        wallet_balance = await self._fetch_optional(
            self.client.async_get_wallet_balance, self.character_id
        )
        skill_queue = await self._fetch_list(
            self.client.async_get_skill_queue, self.character_id
        )
        location = await self._fetch_optional(
            self.client.async_get_character_location, self.character_id
        )
        ship = await self._fetch_optional(
            self.client.async_get_character_ship, self.character_id
        )
        skills = await self._fetch_optional(
            self.client.async_get_skills, self.character_id
        )
        mail_labels = await self._fetch_optional(
            self.client.async_get_mail_labels, self.character_id
        )
        industry_jobs = await self._fetch_list(
            self.client.async_get_industry_jobs, self.character_id
        )
        market_orders = await self._fetch_list(
            self.client.async_get_market_orders, self.character_id
        )
        jump_fatigue = await self._fetch_optional(
            self.client.async_get_jump_fatigue, self.character_id
        )

        # Batch-resolve numeric IDs → names via POST /universe/names/
        resolved_names = await self._resolve_names(
            location, ship, skill_queue, industry_jobs, market_orders
        )

        return EveOnlineData(
            server_status=server_status,
            character_id=self.character_id,
            character_name=self.character_name,
            character_online=character_online,
            wallet_balance=wallet_balance,
            skill_queue=skill_queue,
            location=location,
            ship=ship,
            skills=skills,
            mail_labels=mail_labels,
            industry_jobs=industry_jobs,
            market_orders=market_orders,
            jump_fatigue=jump_fatigue,
            resolved_names=resolved_names,
        )

    async def _fetch_optional(self, method, *args):
        """Fetch an optional endpoint, returning None on failure."""
        try:
            return await method(*args)
        except EveOnlineError as err:
            _LOGGER.debug("Failed to fetch %s: %s", method.__name__, err)
            return None

    async def _fetch_list(self, method, *args):
        """Fetch a list endpoint, returning empty list on failure."""
        try:
            return await method(*args)
        except EveOnlineError as err:
            _LOGGER.debug("Failed to fetch %s: %s", method.__name__, err)
            return []

    async def _resolve_names(
        self,
        location: CharacterLocation | None,
        ship: CharacterShip | None,
        skill_queue: list[SkillQueueEntry],
        industry_jobs: list[IndustryJob],
        market_orders: list[MarketOrder],
    ) -> dict[int, str]:
        """Resolve numeric IDs to human-readable names in a single API call."""
        ids: set[int] = set()

        if location:
            ids.add(location.solar_system_id)
        if ship:
            ids.add(ship.ship_type_id)
        if skill_queue:
            ids.add(skill_queue[0].skill_id)
        for job in industry_jobs:
            ids.add(job.blueprint_type_id)
            if job.product_type_id:
                ids.add(job.product_type_id)
        for order in market_orders:
            ids.add(order.type_id)

        if not ids:
            return {}

        try:
            resolved = await self.client.async_resolve_names(list(ids))
            return {entry.id: entry.name for entry in resolved}
        except EveOnlineError as err:
            _LOGGER.debug("Failed to resolve names: %s", err)
            return {}


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
