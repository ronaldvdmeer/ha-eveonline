"""Sensor platform for Eve Online integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from eveonline.models import ServerStatus
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

from . import EveOnlineConfigEntry, EveOnlineCoordinator
from .const import DOMAIN


@dataclass(frozen=True, kw_only=True)
class EveOnlineSensorDescription(SensorEntityDescription):
    """Describe an Eve Online sensor."""

    value_fn: Callable[[ServerStatus], str | int | None]


SENSOR_DESCRIPTIONS: tuple[EveOnlineSensorDescription, ...] = (
    EveOnlineSensorDescription(
        key="server_status",
        translation_key="server_status",
        icon="mdi:server",
        value_fn=lambda data: "online" if data.players > 0 else "offline",
    ),
    EveOnlineSensorDescription(
        key="players_online",
        translation_key="players_online",
        icon="mdi:account-group",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="players",
        value_fn=lambda data: data.players,
    ),
    EveOnlineSensorDescription(
        key="server_version",
        translation_key="server_version",
        icon="mdi:information-outline",
        entity_registry_enabled_default=False,
        value_fn=lambda data: data.server_version,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EveOnlineConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Eve Online sensors from a config entry."""
    coordinator = entry.runtime_data

    async_add_entities(
        EveOnlineSensor(coordinator, description) for description in SENSOR_DESCRIPTIONS
    )


class EveOnlineSensor(CoordinatorEntity[EveOnlineCoordinator], SensorEntity):
    """Representation of an Eve Online sensor."""

    entity_description: EveOnlineSensorDescription
    _attr_has_entity_name = True

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
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://esi.evetech.net/ui/",
        )

    @property
    def native_value(self) -> str | int | None:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.coordinator.data)
