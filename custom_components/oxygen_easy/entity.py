"""Shared Oxygen Easy entity base."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import OxygenCoordinator


class OxygenEntity(CoordinatorEntity[OxygenCoordinator]):
    """Base entity backed by an Oxygen controller parameter."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: OxygenCoordinator, serial: str, uid: str) -> None:
        super().__init__(coordinator, context=(serial, uid))
        self.serial = serial
        self.uid = uid
        self._attr_unique_id = f"{serial}_{uid}"

    @property
    def device_info(self) -> DeviceInfo:
        """Describe the physical ventilation controller."""
        component = self.coordinator.data.components[self.serial]
        installation = self.coordinator.data.installations[component.installation_id]
        return DeviceInfo(
            identifiers={(DOMAIN, self.serial)},
            name=installation.custom_name or component.display_name,
            manufacturer=component.manufacturer,
            model=component.component_type,
            hw_version=component.hardware_version,
            sw_version=component.software_version,
            serial_number=self.serial,
        )

    @property
    def parameter_value(self):
        """Return the last value already held by the coordinator."""
        return self.coordinator.data.values.get(self.serial, {}).get(self.uid)
