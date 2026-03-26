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
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import EveOnlineConfigEntry, EveOnlineCoordinator, EveOnlineData
from .entity import EveOnlineCharacterEntity, EveOnlineServerEntity


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
    async_add_entities: AddConfigEntryEntitiesCallback,
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


class EveOnlineBinarySensor(BinarySensorEntity):
    """Base class for Eve Online binary sensors."""

    entity_description: EveOnlineBinarySensorDescription

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return self.entity_description.is_on_fn(self.coordinator.data)


class EveOnlineServerBinarySensor(EveOnlineServerEntity, EveOnlineBinarySensor):
    """Eve Online server binary sensor (shared Tranquility device)."""

    def __init__(
        self,
        coordinator: EveOnlineCoordinator,
        description: EveOnlineBinarySensorDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description


class EveOnlineCharacterBinarySensor(
    EveOnlineCharacterEntity, EveOnlineBinarySensor
):
    """Eve Online character binary sensor (per-character device)."""

    def __init__(
        self,
        coordinator: EveOnlineCoordinator,
        description: EveOnlineBinarySensorDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return super().available and self.entity_description.available_fn(
            self.coordinator.data
        )
