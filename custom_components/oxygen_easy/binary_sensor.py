"""Binary sensors exposed by Oxygen Easy controllers."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
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
    bit_mask: int | None = None
    unique_id_suffix: str | None = None


BINARY_SENSORS = (
    OxygenBinarySensorDescription(
        key="bypass_active",
        translation_key="bypass_active",
        uid="u6322",
        icon="mdi:valve-open",
    ),
    OxygenBinarySensorDescription(
        key="supply_filter_replacement",
        translation_key="supply_filter_replacement",
        uid="u6832",
        bit_mask=16,
        unique_id_suffix="supply_filter_replacement",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:air-filter",
    ),
    OxygenBinarySensorDescription(
        key="extract_filter_replacement",
        translation_key="extract_filter_replacement",
        uid="u6832",
        bit_mask=32,
        unique_id_suffix="extract_filter_replacement",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:air-filter",
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
        if description.unique_id_suffix is not None:
            self._attr_unique_id = f"{serial}_{description.unique_id_suffix}"

    @property
    def is_on(self) -> bool | None:
        """Return the latest boolean or bit state."""
        value = self.parameter_value
        if value is None:
            return None
        if self.entity_description.bit_mask is None:
            return bool(value)
        try:
            return bool(int(value) & self.entity_description.bit_mask)
        except (TypeError, ValueError):
            return None
