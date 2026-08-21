"""Number controls for Oxygen Easy controllers."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .coordinator import OxygenCoordinator
from .entity import OxygenEntity
from .mqtt import OxygenMqttError


@dataclass(frozen=True, kw_only=True)
class OxygenNumberDescription(NumberEntityDescription):
    """Describe a writable numeric Oxygen parameter."""

    uid: str


NUMBERS: tuple[OxygenNumberDescription, ...] = (
    OxygenNumberDescription(
        key="day_comfort_temperature",
        translation_key="day_comfort_temperature",
        uid="u7125",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=8,
        native_max_value=30,
        native_step=1,
        mode=NumberMode.BOX,
        icon="mdi:white-balance-sunny",
    ),
    OxygenNumberDescription(
        key="night_comfort_temperature",
        translation_key="night_comfort_temperature",
        uid="u7126",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=8,
        native_max_value=30,
        native_step=1,
        mode=NumberMode.BOX,
        icon="mdi:weather-night",
    ),
    OxygenNumberDescription(
        key="party_mode_duration",
        translation_key="party_mode_duration",
        uid="u6425",
        device_class=NumberDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        native_min_value=1,
        native_max_value=15,
        native_step=1,
        mode=NumberMode.BOX,
        icon="mdi:timer-cog-outline",
    ),
    OxygenNumberDescription(
        key="gateway_button_brightness",
        translation_key="gateway_button_brightness",
        uid="u3263",
        native_min_value=1,
        native_max_value=3,
        native_step=1,
        mode=NumberMode.SLIDER,
        icon="mdi:brightness-6",
    ),
    OxygenNumberDescription(
        key="gateway_button_volume",
        translation_key="gateway_button_volume",
        uid="u3282",
        native_min_value=0,
        native_max_value=50,
        native_step=1,
        mode=NumberMode.SLIDER,
        icon="mdi:volume-medium",
    ),
    OxygenNumberDescription(
        key="gateway_alarm_volume",
        translation_key="gateway_alarm_volume",
        uid="u3283",
        native_min_value=0,
        native_max_value=50,
        native_step=1,
        mode=NumberMode.SLIDER,
        icon="mdi:alarm-bell",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up controller number entities."""
    coordinator: OxygenCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        OxygenNumber(coordinator, serial, description)
        for serial, values in coordinator.data.values.items()
        for description in NUMBERS
        if description.uid in values
    )


class OxygenNumber(OxygenEntity, NumberEntity):
    """Control a numeric Oxygen controller parameter."""

    entity_description: OxygenNumberDescription

    def __init__(
        self,
        coordinator: OxygenCoordinator,
        serial: str,
        description: OxygenNumberDescription,
    ) -> None:
        super().__init__(coordinator, serial, description.uid)
        self.entity_description = description

    @property
    def native_value(self) -> float | None:
        """Return the current numeric value."""
        try:
            return float(self.parameter_value)
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        """Set a numeric value using the cloud protocol's string encoding."""
        cached_value = int(value) if value.is_integer() else value
        try:
            await self.coordinator.async_write_parameter(
                self.serial,
                self.uid,
                encode_number_write_value(value),
                cached_value=cached_value,
            )
        except OxygenMqttError as err:
            raise HomeAssistantError(str(err)) from err


def encode_number_write_value(value: float) -> str:
    """Encode a number as expected by Oxygen PARAMS_MODIFICATION."""
    return str(int(value)) if value.is_integer() else str(value)
