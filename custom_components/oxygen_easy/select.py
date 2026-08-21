"""Select controls for Oxygen Easy controllers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .coordinator import OxygenCoordinator
from .entity import OxygenEntity
from .mqtt import OxygenMqttError


@dataclass(frozen=True, kw_only=True)
class OxygenSelectDescription(SelectEntityDescription):
    """Describe an Oxygen option parameter."""

    uid: str
    option_to_write_value: Mapping[str, Any]
    read_value_to_option: Mapping[Any, str]


OPTION_TO_WRITE_VALUE = {
    "low": "H3L252",
    "medium": "H4L251",
    "high": "H5L250",
    "paused": "H6L249",
}
READ_VALUE_TO_OPTION = {
    3: "low",
    4: "medium",
    5: "high",
    6: "paused",
}
OPTION_TO_READ_VALUE = {option: value for value, option in READ_VALUE_TO_OPTION.items()}

OPERATING_MODE_OPTION_TO_WRITE_VALUE = {
    "manual": "H0L1",
    "schedule": "H1L0",
}
OPERATING_MODE_READ_VALUE_TO_OPTION = {
    0: "manual",
    1: "schedule",
}

COMFORT_MODE_OPTION_TO_WRITE_VALUE = {
    "schedule": "H0L255",
    "day": "H1L254",
    "night": "H2L253",
}
COMFORT_MODE_READ_VALUE_TO_OPTION = {
    0: "schedule",
    1: "day",
    2: "night",
}

TIMED_MODE_OPTION_TO_WRITE_VALUE = {
    "off": "H0L255",
    "away": "H1L254",
    "party": "H2L253",
    "airing": "H4L251",
}
TIMED_MODE_READ_VALUE_TO_OPTION = {
    0: "off",
    1: "away",
    2: "party",
    4: "airing",
}

TIMEZONE_MODE_OPTION_TO_WRITE_VALUE = {
    "automatic": "0",
    "manual": "1",
}
TIMEZONE_MODE_READ_VALUE_TO_OPTION = {
    0: "automatic",
    1: "manual",
}

SELECTS: tuple[OxygenSelectDescription, ...] = (
    OxygenSelectDescription(
        key="fan_level",
        translation_key="fan_level",
        uid="u81",
        icon="mdi:fan-speed-3",
        option_to_write_value=OPTION_TO_WRITE_VALUE,
        read_value_to_option=READ_VALUE_TO_OPTION,
    ),
    OxygenSelectDescription(
        key="operating_mode",
        translation_key="operating_mode",
        uid="u6630",
        icon="mdi:calendar-sync",
        option_to_write_value=OPERATING_MODE_OPTION_TO_WRITE_VALUE,
        read_value_to_option=OPERATING_MODE_READ_VALUE_TO_OPTION,
    ),
    OxygenSelectDescription(
        key="comfort_mode",
        translation_key="comfort_mode",
        uid="u7124",
        icon="mdi:sun-thermometer",
        option_to_write_value=COMFORT_MODE_OPTION_TO_WRITE_VALUE,
        read_value_to_option=COMFORT_MODE_READ_VALUE_TO_OPTION,
    ),
    OxygenSelectDescription(
        key="timed_mode",
        translation_key="timed_mode",
        uid="u84",
        icon="mdi:timer-cog-outline",
        option_to_write_value=TIMED_MODE_OPTION_TO_WRITE_VALUE,
        read_value_to_option=TIMED_MODE_READ_VALUE_TO_OPTION,
    ),
    OxygenSelectDescription(
        key="gateway_timezone_mode",
        translation_key="gateway_timezone_mode",
        uid="u9848",
        icon="mdi:map-clock-outline",
        option_to_write_value=TIMEZONE_MODE_OPTION_TO_WRITE_VALUE,
        read_value_to_option=TIMEZONE_MODE_READ_VALUE_TO_OPTION,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up controller select entities."""
    coordinator: OxygenCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        OxygenSelect(coordinator, serial, description)
        for serial, values in coordinator.data.values.items()
        for description in SELECTS
        if description.uid in values
    )


class OxygenSelect(OxygenEntity, SelectEntity):
    """Select an option encoded by an Oxygen controller mask."""

    entity_description: OxygenSelectDescription

    def __init__(
        self,
        coordinator: OxygenCoordinator,
        serial: str,
        description: OxygenSelectDescription,
    ) -> None:
        super().__init__(coordinator, serial, description.uid)
        self.entity_description = description
        self._attr_options = list(description.option_to_write_value)

    @property
    def current_option(self) -> str | None:
        """Return the option represented by the controller value."""
        try:
            value = int(self.parameter_value)
        except (TypeError, ValueError):
            return None
        return self.entity_description.read_value_to_option.get(value)

    async def async_select_option(self, option: str) -> None:
        """Set an option and require a successful device response."""
        try:
            write_value = self.entity_description.option_to_write_value[option]
            read_value = next(
                value
                for value, candidate in (
                    self.entity_description.read_value_to_option.items()
                )
                if candidate == option
            )
            await self.coordinator.async_write_parameter(
                self.serial,
                self.uid,
                write_value,
                cached_value=read_value,
            )
        except (KeyError, StopIteration) as err:
            raise HomeAssistantError(
                f"Unknown Oxygen {self.entity_description.key}: {option}"
            ) from err
        except OxygenMqttError as err:
            raise HomeAssistantError(str(err)) from err
