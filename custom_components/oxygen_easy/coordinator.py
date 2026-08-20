"""Data coordinator for Oxygen Easy controllers."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    OxygenApiError,
    OxygenAuthenticationError,
    OxygenCloudSession,
)
from .const import CONTROLLER_TYPE, DOMAIN, MONITORED_UIDS, UPDATE_INTERVAL
from .models import OxygenComponent, OxygenCoordinatorData, OxygenInstallation
from .mqtt import OxygenMqttClient, OxygenMqttError, extract_values

_LOGGER = logging.getLogger(__name__)


class OxygenCoordinator(DataUpdateCoordinator[OxygenCoordinatorData]):
    """Coordinate REST discovery, MQTT reads, and MQTT push updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        session: OxygenCloudSession,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
            always_update=False,
        )
        self.session = session
        self.data = OxygenCoordinatorData()
        self.mqtt = OxygenMqttClient(session, self._handle_mqtt_values)

    async def _async_setup(self) -> None:
        """Discover installations and their ventilation controllers once."""
        try:
            raw_installations = await self.hass.async_add_executor_job(
                self.session.installations
            )
            if not raw_installations:
                raise UpdateFailed(
                    "No Oxygen installations are available to this account"
                )

            for raw in raw_installations:
                installation_id = str(raw.get("id", ""))
                if not installation_id:
                    continue
                installation = OxygenInstallation(
                    installation_id=installation_id,
                    name=str(raw.get("name") or "Oxygen gateway"),
                    serial=str(raw.get("factoryNumber") or installation_id),
                    custom_name=str(raw.get("customName") or ""),
                    hardware_version=_optional_string(raw.get("hardwareVersion")),
                    software_version=_optional_string(raw.get("softVersion")),
                    connected=bool(raw.get("isConnected")),
                )
                self.data.installations[installation_id] = installation

                details = await self.hass.async_add_executor_job(
                    self.session.installation_details, installation_id
                )
                for component in details.get("components", []):
                    if not isinstance(component, dict):
                        continue
                    component_type = str(component.get("componentType") or "")
                    if component_type != CONTROLLER_TYPE:
                        continue
                    serial = str(component.get("componentFn") or "")
                    if not serial:
                        continue
                    self.data.components[serial] = OxygenComponent(
                        installation_id=installation_id,
                        serial=serial,
                        component_type=component_type,
                        custom_name=str(component.get("customName") or ""),
                        manufacturer=str(component.get("producerName") or "Oxygen"),
                        hardware_version=_optional_string(
                            component.get("hardwareVersion")
                        ),
                        software_version=_optional_string(component.get("softVersion")),
                    )
                    self.data.values.setdefault(serial, {})

            if not self.data.components:
                raise UpdateFailed(
                    "No supported Oxygen ventilation controller was found"
                )
            await self.mqtt.async_ensure_connected(set(self.data.installations))
        except OxygenAuthenticationError as err:
            raise ConfigEntryAuthFailed from err
        except OxygenApiError as err:
            raise UpdateFailed(str(err)) from err

    async def _async_update_data(self) -> OxygenCoordinatorData:
        """Request a fresh snapshot; MQTT push updates fill gaps between polls."""
        try:
            await self.mqtt.async_ensure_connected(set(self.data.installations))
            for installation_id in self.data.installations:
                targets = [
                    {
                        "component": component.serial,
                        "parameters": list(MONITORED_UIDS),
                    }
                    for component in self.data.components.values()
                    if component.installation_id == installation_id
                ]
                if not targets:
                    continue
                response = await self.mqtt.async_send_operation(
                    installation_id,
                    {"name": "GET_VALUES", "targets": targets},
                )
                self._merge_values(extract_values(response))
            return self.data.clone()
        except OxygenAuthenticationError as err:
            raise ConfigEntryAuthFailed from err
        except (OxygenApiError, OxygenMqttError) as err:
            raise UpdateFailed(str(err)) from err

    def _handle_mqtt_values(self, values: dict[str, dict[str, Any]]) -> None:
        """Handle push values on the Home Assistant event loop."""
        if not self._merge_values(values):
            return
        self.async_set_updated_data(self.data.clone())

    def _merge_values(self, values: dict[str, dict[str, Any]]) -> bool:
        changed = False
        for serial, component_values in values.items():
            if serial not in self.data.components:
                continue
            current = self.data.values.setdefault(serial, {})
            for uid, value in component_values.items():
                if current.get(uid) != value:
                    current[uid] = value
                    changed = True
        return changed

    async def async_write_parameter(self, serial: str, uid: str, value: Any) -> None:
        """Write one parameter and accept only documented success statuses."""
        component = self.data.components[serial]
        response = await self.mqtt.async_send_operation(
            component.installation_id,
            {
                "name": "PARAMS_MODIFICATION",
                "targets": [{"component": serial, "parameters": {uid: value}}],
            },
        )
        status = _modification_status(response, serial, uid)
        if status not in ("0", "16"):
            raise OxygenMqttError(
                f"Oxygen controller rejected {uid} (status {status or 'missing'})"
            )
        self._merge_values({serial: {uid: value}})
        self.async_set_updated_data(self.data.clone())

    async def async_shutdown(self) -> None:
        """Release the MQTT connection."""
        await self.mqtt.async_disconnect()


def _optional_string(value: Any) -> str | None:
    return str(value) if value not in (None, "") else None


def _modification_status(document: Any, serial: str, uid: str) -> str | None:
    """Find a parameter status without depending on response ordering."""
    if isinstance(document, dict):
        component = document.get("component")
        if component is not None and str(component) == serial:
            parameters = document.get("parameters")
            if isinstance(parameters, dict) and uid in parameters:
                return str(parameters[uid])
        for value in document.values():
            status = _modification_status(value, serial, uid)
            if status is not None:
                return status
    elif isinstance(document, list):
        for value in document:
            status = _modification_status(value, serial, uid)
            if status is not None:
                return status
    return None
