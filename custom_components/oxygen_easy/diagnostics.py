"""Diagnostics support for Oxygen Easy."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import OxygenCoordinator


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return useful state without account or device identifiers."""
    coordinator: OxygenCoordinator = hass.data[DOMAIN][entry.entry_id]
    data = coordinator.data
    return {
        "configured_fields": sorted(entry.data),
        "installations": [
            {
                "connected_at_discovery": item.connected,
                "hardware_version": item.hardware_version,
                "software_version": item.software_version,
            }
            for item in data.installations.values()
        ],
        "components": [
            {
                "type": component.component_type,
                "manufacturer": component.manufacturer,
                "hardware_version": component.hardware_version,
                "software_version": component.software_version,
                "available_parameters": sorted(data.values.get(component.serial, {})),
            }
            for component in data.components.values()
        ],
        "last_update_success": coordinator.last_update_success,
    }
