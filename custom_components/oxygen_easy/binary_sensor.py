"""Binary sensors exposed by Oxygen Easy controllers."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .coordinator import OxygenCoordinator
from .entity import OxygenEntity


@dataclass(frozen=True, kw_only=True)
class OxygenBinarySensorDescription(BinarySensorEntityDescription):
    """Describe a boolean Oxygen parameter."""

    uid: str


BINARY_SENSORS = (
    OxygenBinarySensorDescription(
        key="bypass_active",
        translation_key="bypass_active",
        uid="u6322",
        icon="mdi:valve-open",
    ),
    OxygenBinarySensorDescription(
        key="automatic_mode",
        translation_key="automatic_mode",
        uid="u7073",
        icon="mdi:autorenew",
    ),
    OxygenBinarySensorDescription(
        key="schedule_active",
        translation_key="schedule_active",
        uid="u6630",
        icon="mdi:calendar-clock",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Oxygen binary sensors."""
    coordinator: OxygenCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        OxygenBinarySensor(coordinator, serial, description)
        for serial, values in coordinator.data.values.items()
        for description in BINARY_SENSORS
        if description.uid in values
    )


class OxygenBinarySensor(OxygenEntity, BinarySensorEntity):
    """A boolean controller state."""

    entity_description: OxygenBinarySensorDescription

    def __init__(
        self,
        coordinator: OxygenCoordinator,
        serial: str,
        description: OxygenBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator, serial, description.uid)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return the latest boolean state."""
        value = self.parameter_value
        return bool(value) if value is not None else None
