"""Diagnostics support for Oxygen Easy."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_PASSWORD, CONF_USERNAME, DOMAIN
from .coordinator import OxygenCoordinator


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return useful state without passwords, tokens, or AWS credentials."""
    coordinator: OxygenCoordinator = hass.data[DOMAIN][entry.entry_id]
    data = coordinator.data
    return {
        "config_entry": {
            key: "**REDACTED**" if key in (CONF_PASSWORD, CONF_USERNAME) else value
            for key, value in entry.data.items()
        },
        "installations": {
            installation_id: {
                "name": item.name,
                "custom_name": item.custom_name,
                "connected_at_discovery": item.connected,
                "hardware_version": item.hardware_version,
                "software_version": item.software_version,
            }
            for installation_id, item in data.installations.items()
        },
        "components": {
            serial: {
                "installation_id": component.installation_id,
                "type": component.component_type,
                "hardware_version": component.hardware_version,
                "software_version": component.software_version,
                "available_parameters": sorted(data.values.get(serial, {})),
            }
            for serial, component in data.components.items()
        },
        "last_update_success": coordinator.last_update_success,
    }
