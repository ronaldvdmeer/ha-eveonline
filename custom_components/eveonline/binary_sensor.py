"""Binary sensor platform for Eve Online integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import EveOnlineConfigEntry, EveOnlineCoordinator, EveOnlineData
from .const import DOMAIN


@dataclass(frozen=True, kw_only=True)
class EveOnlineBinarySensorDescription(BinarySensorEntityDescription):
    """Describe an Eve Online binary sensor."""

    is_on_fn: Callable[[EveOnlineData], bool | None]
    available_fn: Callable[[EveOnlineData], bool] = lambda _: True


# ---------------------------------------------------------------------------
# Server binary sensors (shared "Tranquility" device)
# ---------------------------------------------------------------------------
SERVER_BINARY_SENSORS: tuple[EveOnlineBinarySensorDescription, ...] = (
    EveOnlineBinarySensorDescription(
        key="server_status",
        translation_key="server_status",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        is_on_fn=lambda data: data.server_status.players > 0,
    ),
)

# ---------------------------------------------------------------------------
# Character binary sensors (per-character device)
# ---------------------------------------------------------------------------
CHARACTER_BINARY_SENSORS: tuple[EveOnlineBinarySensorDescription, ...] = (
    EveOnlineBinarySensorDescription(
        key="character_online",
        translation_key="character_online",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        is_on_fn=lambda data: (
            data.character_online.online
            if data.character_online
            else None
        ),
        available_fn=lambda data: data.character_online is not None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EveOnlineConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Eve Online binary sensors from a config entry."""
    coordinator = entry.runtime_data
    entities: list[EveOnlineBinarySensor] = []

    for description in SERVER_BINARY_SENSORS:
        entities.append(EveOnlineServerBinarySensor(coordinator, description))

    for description in CHARACTER_BINARY_SENSORS:
        entities.append(
            EveOnlineCharacterBinarySensor(coordinator, description)
        )

    async_add_entities(entities)


class EveOnlineBinarySensor(
    CoordinatorEntity[EveOnlineCoordinator], BinarySensorEntity
):
    """Base class for Eve Online binary sensors."""

    entity_description: EveOnlineBinarySensorDescription
    _attr_has_entity_name = True

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return self.entity_description.is_on_fn(self.coordinator.data)


class EveOnlineServerBinarySensor(EveOnlineBinarySensor):
    """Eve Online server binary sensor (shared Tranquility device)."""

    def __init__(
        self,
        coordinator: EveOnlineCoordinator,
        description: EveOnlineBinarySensorDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "tranquility")},
            name="Eve Online (Tranquility)",
            manufacturer="CCP Games",
            model="ESI API",
            sw_version=coordinator.data.server_status.server_version,
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://esi.evetech.net/ui/",
        )


class EveOnlineCharacterBinarySensor(EveOnlineBinarySensor):
    """Eve Online character binary sensor (per-character device)."""

    def __init__(
        self,
        coordinator: EveOnlineCoordinator,
        description: EveOnlineBinarySensorDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = (
            f"{DOMAIN}_{coordinator.character_id}_{description.key}"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(coordinator.character_id))},
            name=coordinator.character_name,
            manufacturer="CCP Games",
            model="Eve Online Character",
            entry_type=DeviceEntryType.SERVICE,
            via_device=(DOMAIN, "tranquility"),
            configuration_url=(
                f"https://evewho.com/character/{coordinator.character_id}"
            ),
        )

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return super().available and self.entity_description.available_fn(
            self.coordinator.data
        )
