"""Switch controls for Oxygen Easy controllers."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .coordinator import OxygenCoordinator
from .entity import OxygenEntity
from .mqtt import OxygenMqttError

POWER = SwitchEntityDescription(
    key="power",
    translation_key="power",
    icon="mdi:power",
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the controller power switches."""
    coordinator: OxygenCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        OxygenPowerSwitch(coordinator, serial)
        for serial, values in coordinator.data.values.items()
        if "u7074" in values
    )


class OxygenPowerSwitch(OxygenEntity, SwitchEntity):
    """Turn the ventilation controller on or off."""

    entity_description = POWER

    def __init__(self, coordinator: OxygenCoordinator, serial: str) -> None:
        super().__init__(coordinator, serial, "u7074")

    @property
    def is_on(self) -> bool | None:
        """Return the current power state."""
        value = self.parameter_value
        return bool(value) if value is not None else None

    async def async_turn_on(self, **kwargs) -> None:
        """Turn ventilation on."""
        await self._async_set_power(1)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn ventilation off."""
        await self._async_set_power(0)

    async def _async_set_power(self, value: int) -> None:
        try:
            await self.coordinator.async_write_parameter(self.serial, self.uid, value)
        except OxygenMqttError as err:
            raise HomeAssistantError(str(err)) from err
