"""Sensors exposed by Oxygen Easy controllers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_MILLION,
    PERCENTAGE,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .coordinator import OxygenCoordinator
from .entity import OxygenEntity


@dataclass(frozen=True, kw_only=True)
class OxygenSensorDescription(SensorEntityDescription):
    """Describe an Oxygen parameter sensor."""

    uid: str
    transform: Callable[[Any], Any] | None = None


SENSORS: tuple[OxygenSensorDescription, ...] = (
    OxygenSensorDescription(
        key="outdoor_temperature",
        translation_key="outdoor_temperature",
        uid="u6209",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    OxygenSensorDescription(
        key="exhaust_temperature",
        translation_key="exhaust_temperature",
        uid="u6208",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    OxygenSensorDescription(
        key="supply_temperature",
        translation_key="supply_temperature",
        uid="u6205",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    OxygenSensorDescription(
        key="extract_temperature",
        translation_key="extract_temperature",
        uid="u6207",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    OxygenSensorDescription(
        key="humidity",
        translation_key="humidity",
        uid="u6273",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    OxygenSensorDescription(
        key="co2",
        translation_key="co2",
        uid="u6265",
        device_class=SensorDeviceClass.CO2,
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    OxygenSensorDescription(
        key="supply_airflow",
        translation_key="supply_airflow",
        uid="u6828",
        icon="mdi:weather-windy",
        native_unit_of_measurement="m³/h",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    OxygenSensorDescription(
        key="extract_airflow",
        translation_key="extract_airflow",
        uid="u6829",
        icon="mdi:weather-windy",
        native_unit_of_measurement="m³/h",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    OxygenSensorDescription(
        key="supply_fan",
        translation_key="supply_fan",
        uid="u6202",
        icon="mdi:fan",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    OxygenSensorDescription(
        key="extract_fan",
        translation_key="extract_fan",
        uid="u6203",
        icon="mdi:fan",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    OxygenSensorDescription(
        key="supply_filter",
        translation_key="supply_filter",
        uid="u6938",
        icon="mdi:air-filter",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    OxygenSensorDescription(
        key="extract_filter",
        translation_key="extract_filter",
        uid="u6939",
        icon="mdi:air-filter",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    OxygenSensorDescription(
        key="bypass_opening",
        translation_key="bypass_opening",
        uid="u6332",
        icon="mdi:valve",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up supported Oxygen parameter sensors."""
    coordinator: OxygenCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        OxygenSensor(coordinator, serial, description)
        for serial, values in coordinator.data.values.items()
        for description in SENSORS
        if description.uid in values
    )


class OxygenSensor(OxygenEntity, SensorEntity):
    """A read-only Oxygen controller parameter."""

    entity_description: OxygenSensorDescription

    def __init__(
        self,
        coordinator: OxygenCoordinator,
        serial: str,
        description: OxygenSensorDescription,
    ) -> None:
        super().__init__(coordinator, serial, description.uid)
        self.entity_description = description

    @property
    def native_value(self):
        """Return the latest value."""
        value = self.parameter_value
        if self.entity_description.transform is not None and value is not None:
            return self.entity_description.transform(value)
        return value
