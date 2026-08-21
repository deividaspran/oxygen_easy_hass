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
    UnitOfTime,
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


UNIT_STATUS_TO_STATE = {
    0: "no_status",
    1: "off",
    2: "standby",
    3: "normal",
    4: "heating",
    5: "cooling",
    6: "exchanger_dewatering",
    7: "exchanger_cleaning",
    8: "airing",
    9: "heater_cooling",
    10: "filter_test",
    11: "boost",
    12: "defrosting",
    13: "start_delay",
    14: "heat_recovery",
    15: "cold_recovery",
    16: "service_stop",
}


def _unit_status(value: Any) -> str | None:
    """Translate a unit status code into a stable entity state."""
    try:
        return UNIT_STATUS_TO_STATE.get(int(value), "no_status")
    except (TypeError, ValueError):
        return None


def _nonnegative(value: Any) -> Any:
    """Hide the controller's negative inactive-duration sentinel."""
    try:
        is_negative = float(value) < 0
    except (TypeError, ValueError):
        return None
    return None if is_negative else value


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
        key="after_heat_exchanger_temperature",
        translation_key="after_heat_exchanger_temperature",
        uid="u6206",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    OxygenSensorDescription(
        key="ground_heat_exchanger_temperature",
        translation_key="ground_heat_exchanger_temperature",
        uid="u6350",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    OxygenSensorDescription(
        key="lead_temperature",
        translation_key="lead_temperature",
        uid="u6338",
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
        key="supply_airflow_setpoint",
        translation_key="supply_airflow_setpoint",
        uid="u6812",
        icon="mdi:weather-windy",
        native_unit_of_measurement="m³/h",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    OxygenSensorDescription(
        key="extract_airflow_setpoint",
        translation_key="extract_airflow_setpoint",
        uid="u6813",
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
    OxygenSensorDescription(
        key="gateway_date_time",
        translation_key="gateway_date_time",
        uid="u9849",
        icon="mdi:clock-outline",
    ),
    OxygenSensorDescription(
        key="gateway_temperature",
        translation_key="gateway_temperature",
        uid="u3286",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    OxygenSensorDescription(
        key="gateway_humidity",
        translation_key="gateway_humidity",
        uid="u3287",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    OxygenSensorDescription(
        key="unit_status",
        translation_key="unit_status",
        uid="u7151",
        device_class=SensorDeviceClass.ENUM,
        options=list(UNIT_STATUS_TO_STATE.values()),
        icon="mdi:hvac",
        transform=_unit_status,
    ),
    OxygenSensorDescription(
        key="party_time_remaining",
        translation_key="party_time_remaining",
        uid="u6429",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:timer-sand",
        transform=_nonnegative,
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
