"""Fan-level control for Oxygen Easy controllers."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .coordinator import OxygenCoordinator
from .entity import OxygenEntity
from .mqtt import OxygenMqttError

OPTION_TO_VALUE = {
    "low": 3,
    "medium": 4,
    "high": 5,
    "paused": 6,
}
VALUE_TO_OPTION = {value: option for option, value in OPTION_TO_VALUE.items()}

FAN_LEVEL = SelectEntityDescription(
    key="fan_level",
    translation_key="fan_level",
    icon="mdi:fan-speed-3",
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up controller fan-level selects."""
    coordinator: OxygenCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        OxygenFanLevelSelect(coordinator, serial)
        for serial, values in coordinator.data.values.items()
        if "u81" in values
    )


class OxygenFanLevelSelect(OxygenEntity, SelectEntity):
    """Select the controller's low/medium/high/pause state."""

    entity_description = FAN_LEVEL
    _attr_options = list(OPTION_TO_VALUE)

    def __init__(self, coordinator: OxygenCoordinator, serial: str) -> None:
        super().__init__(coordinator, serial, "u81")

    @property
    def current_option(self) -> str | None:
        """Return the option represented by the controller bit mask."""
        try:
            return VALUE_TO_OPTION.get(int(self.parameter_value))
        except (TypeError, ValueError):
            return None

    async def async_select_option(self, option: str) -> None:
        """Set a fan level and require a successful device response."""
        try:
            value = OPTION_TO_VALUE[option]
            await self.coordinator.async_write_parameter(self.serial, self.uid, value)
        except KeyError as err:
            raise HomeAssistantError(f"Unknown Oxygen fan level: {option}") from err
        except OxygenMqttError as err:
            raise HomeAssistantError(str(err)) from err
