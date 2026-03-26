"""Sensor platform for Eve Online integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import EveOnlineConfigEntry, EveOnlineCoordinator, EveOnlineData
from .const import DOMAIN


@dataclass(frozen=True, kw_only=True)
class EveOnlineSensorDescription(SensorEntityDescription):
    """Describe an Eve Online sensor."""

    value_fn: Callable[[EveOnlineData], str | int | float | datetime | None]
    available_fn: Callable[[EveOnlineData], bool] = lambda _: True


# ---------------------------------------------------------------------------
# Server sensors (shared "Tranquility" device)
# ---------------------------------------------------------------------------
SERVER_SENSORS: tuple[EveOnlineSensorDescription, ...] = (
    EveOnlineSensorDescription(
        key="server_status",
        translation_key="server_status",
        icon="mdi:server",
        value_fn=lambda data: "online" if data.server_status.players > 0 else "offline",
    ),
    EveOnlineSensorDescription(
        key="players_online",
        translation_key="players_online",
        icon="mdi:account-group",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="players",
        value_fn=lambda data: data.server_status.players,
    ),
    EveOnlineSensorDescription(
        key="server_version",
        translation_key="server_version",
        icon="mdi:information-outline",
        entity_registry_enabled_default=False,
        value_fn=lambda data: data.server_status.server_version,
    ),
)

# ---------------------------------------------------------------------------
# Character sensors (per-character device)
# ---------------------------------------------------------------------------
CHARACTER_SENSORS: tuple[EveOnlineSensorDescription, ...] = (
    EveOnlineSensorDescription(
        key="character_online",
        translation_key="character_online",
        icon="mdi:account-check",
        value_fn=lambda data: (
            "online"
            if data.character_online and data.character_online.online
            else "offline"
        ),
        available_fn=lambda data: data.character_online is not None,
    ),
    EveOnlineSensorDescription(
        key="wallet_balance",
        translation_key="wallet_balance",
        icon="mdi:wallet",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="ISK",
        suggested_display_precision=2,
        value_fn=lambda data: (
            data.wallet_balance.balance if data.wallet_balance else None
        ),
        available_fn=lambda data: data.wallet_balance is not None,
    ),
    EveOnlineSensorDescription(
        key="skill_queue_count",
        translation_key="skill_queue_count",
        icon="mdi:school",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="skills",
        value_fn=lambda data: len(data.skill_queue),
    ),
    EveOnlineSensorDescription(
        key="current_skill_finish",
        translation_key="current_skill_finish",
        icon="mdi:clock-end",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: (
            data.skill_queue[0].finish_date
            if data.skill_queue and data.skill_queue[0].finish_date
            else None
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EveOnlineConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Eve Online sensors from a config entry."""
    coordinator = entry.runtime_data
    entities: list[EveOnlineSensor] = []

    for description in SERVER_SENSORS:
        entities.append(EveOnlineServerSensor(coordinator, description))

    for description in CHARACTER_SENSORS:
        entities.append(EveOnlineCharacterSensor(coordinator, description))

    async_add_entities(entities)


class EveOnlineSensor(CoordinatorEntity[EveOnlineCoordinator], SensorEntity):
    """Base class for Eve Online sensors."""

    entity_description: EveOnlineSensorDescription
    _attr_has_entity_name = True

    @property
    def native_value(self) -> str | int | float | datetime | None:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.coordinator.data)


class EveOnlineServerSensor(EveOnlineSensor):
    """Eve Online server sensor (shared Tranquility device)."""

    def __init__(
        self,
        coordinator: EveOnlineCoordinator,
        description: EveOnlineSensorDescription,
    ) -> None:
        """Initialize the sensor."""
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


class EveOnlineCharacterSensor(EveOnlineSensor):
    """Eve Online character sensor (per-character device)."""

    def __init__(
        self,
        coordinator: EveOnlineCoordinator,
        description: EveOnlineSensorDescription,
    ) -> None:
        """Initialize the sensor."""
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
