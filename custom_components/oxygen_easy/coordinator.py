"""Data coordinator for Oxygen Easy controllers."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    OxygenApiError,
    OxygenAuthenticationError,
    OxygenCloudError,
    OxygenCloudSession,
)
from .const import (
    CONTROLLER_TYPE,
    DOMAIN,
    GATEWAY_MONITORED_UIDS,
    MONITORED_UIDS,
    UPDATE_INTERVAL,
)
from .models import OxygenComponent, OxygenCoordinatorData, OxygenInstallation
from .mqtt import OxygenMqttClient, OxygenMqttError, extract_values

_LOGGER = logging.getLogger(__name__)

FILTER_REPLACEMENT_UID = "u6832"
SUPPLY_FILTER_REPLACEMENT_BIT = 16
EXTRACT_FILTER_REPLACEMENT_BIT = 32


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
        self.entry_id = entry.entry_id
        self.data = OxygenCoordinatorData()
        self.mqtt = OxygenMqttClient(session, self._handle_mqtt_values)
        self._filter_notification_state: dict[str, tuple[str, ...]] = {}
        self._alarm_descriptions: dict[str, dict[int, str]] = {}
        self._active_alarm_state: set[tuple[str, int]] = set()

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
                gateway = details.get("installationInfo")
                if isinstance(gateway, dict):
                    gateway_serial = str(gateway.get("factoryNumber") or "")
                    if gateway_serial:
                        self.data.components[gateway_serial] = OxygenComponent(
                            installation_id=installation_id,
                            serial=gateway_serial,
                            component_type="internet module",
                            custom_name=str(gateway.get("customName") or ""),
                            manufacturer=str(gateway.get("producerName") or "Oxygen"),
                            producer_code=_optional_string(gateway.get("producerCode")),
                            profile_name=_optional_string(gateway.get("name")),
                            hardware_version=_optional_string(
                                gateway.get("hardwareVersion")
                            ),
                            software_version=_optional_string(
                                gateway.get("softVersion")
                            ),
                            is_gateway=True,
                        )
                        self.data.values.setdefault(gateway_serial, {})

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
                        producer_code=_optional_string(component.get("producerCode")),
                        profile_name=component_type,
                        hardware_version=_optional_string(
                            component.get("hardwareVersion")
                        ),
                        software_version=_optional_string(component.get("softVersion")),
                    )
                    self.data.values.setdefault(serial, {})

            if not any(
                not component.is_gateway for component in self.data.components.values()
            ):
                raise UpdateFailed(
                    "No supported Oxygen ventilation controller was found"
                )
            await self.mqtt.async_ensure_connected(set(self.data.installations))
            await self._async_load_alarm_descriptions()
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
                        "parameters": list(
                            GATEWAY_MONITORED_UIDS
                            if component.is_gateway
                            else MONITORED_UIDS
                        ),
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
                await self._async_update_alarms(installation_id)
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
        if changed:
            self._sync_filter_notifications()
        return changed

    def _sync_filter_notifications(self) -> None:
        """Create or clear controller-driven filter replacement alerts."""
        for serial, component in self.data.components.items():
            raw_value = self.data.values.get(serial, {}).get(FILTER_REPLACEMENT_UID)
            replacement_parts = filter_replacement_parts(raw_value)
            if replacement_parts is None:
                continue
            if self._filter_notification_state.get(serial) == replacement_parts:
                continue

            notification_id = f"{DOMAIN}_filter_replacement_{self.entry_id}_{serial}"
            if replacement_parts:
                installation = self.data.installations[component.installation_id]
                device_name = installation.custom_name or component.display_name
                filters = " and ".join(replacement_parts)
                persistent_notification.async_create(
                    self.hass,
                    (
                        f"{device_name} reports that the {filters} "
                        "need replacement. Replace the indicated filters and "
                        "complete the filter-change procedure on the controller."
                    ),
                    title="Oxygen filter replacement required",
                    notification_id=notification_id,
                )
            else:
                persistent_notification.async_dismiss(self.hass, notification_id)
            self._filter_notification_state[serial] = replacement_parts

    async def _async_load_alarm_descriptions(self) -> None:
        """Load model-specific English descriptions for cloud alarms."""
        for serial, component in self.data.components.items():
            profile_parts = (
                component.producer_code,
                component.profile_name,
                component.hardware_version,
                component.software_version,
            )
            if any(part is None for part in profile_parts):
                continue
            try:
                profile = await self.hass.async_add_executor_job(
                    self.session.component_profile, *profile_parts
                )
                translations = await self.hass.async_add_executor_job(
                    self.session.component_translations, *profile_parts
                )
            except OxygenCloudError as err:
                _LOGGER.debug(
                    "Could not load Oxygen alarm descriptions for %s: %s",
                    component.component_type,
                    err,
                )
                continue
            self._alarm_descriptions[serial] = parse_alarm_descriptions(
                profile, translations
            )

    async def _async_update_alarms(self, installation_id: str) -> None:
        """Fetch active cloud alarms without making telemetry unavailable."""
        component_ids = [
            component.serial
            for component in self.data.components.values()
            if component.installation_id == installation_id
        ]
        if not component_ids:
            return
        try:
            alarms = await self.hass.async_add_executor_job(
                self.session.active_alarms, installation_id, component_ids
            )
        except OxygenCloudError as err:
            _LOGGER.debug("Could not refresh Oxygen alarms: %s", err)
            return
        self._sync_alarm_notifications(component_ids, alarms)

    def _sync_alarm_notifications(
        self,
        component_ids: list[str],
        alarms: list[dict[str, Any]],
    ) -> None:
        """Create notifications for new alarms and dismiss cleared alarms."""
        scoped_ids = set(component_ids)
        previous = {key for key in self._active_alarm_state if key[0] in scoped_ids}
        active: set[tuple[str, int]] = set()
        for alarm in alarms:
            serial = str(alarm.get("componentId") or "")
            code = parse_alarm_code(alarm.get("code"))
            if (
                serial not in scoped_ids
                or code is None
                or str(alarm.get("type")) != "0"
                or alarm.get("endTime") is not None
            ):
                continue
            active.add((serial, code))

        for serial, code in active - previous:
            component = self.data.components.get(serial)
            if component is None:
                continue
            installation = self.data.installations[component.installation_id]
            device_name = installation.custom_name or component.display_name
            description = self._alarm_descriptions.get(serial, {}).get(
                code, f"Alarm e{code}"
            )
            persistent_notification.async_create(
                self.hass,
                f"{device_name} reports: {description} (e{code}).",
                title="Oxygen alarm",
                notification_id=self._alarm_notification_id(serial, code),
            )

        for serial, code in previous - active:
            persistent_notification.async_dismiss(
                self.hass, self._alarm_notification_id(serial, code)
            )

        self._active_alarm_state.difference_update(previous)
        self._active_alarm_state.update(active)

    def _alarm_notification_id(self, serial: str, code: int) -> str:
        """Return a stable identifier for one cloud alarm."""
        return f"{DOMAIN}_alarm_{self.entry_id}_{serial}_{code}"

    async def async_write_parameter(
        self,
        serial: str,
        uid: str,
        value: Any,
        *,
        cached_value: Any | None = None,
    ) -> None:
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
        self._merge_values(
            {serial: {uid: value if cached_value is None else cached_value}}
        )
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


def filter_replacement_parts(value: Any) -> tuple[str, ...] | None:
    """Return the filter names selected by the controller replacement flags."""
    try:
        flags = int(value)
    except (TypeError, ValueError):
        return None

    parts = []
    if flags & SUPPLY_FILTER_REPLACEMENT_BIT:
        parts.append("supply air filter")
    if flags & EXTRACT_FILTER_REPLACEMENT_BIT:
        parts.append("extraction air filter")
    return tuple(parts)


def parse_alarm_code(value: Any) -> int | None:
    """Normalize archive and profile alarm codes such as 37 and e37."""
    text = str(value).strip().lower()
    if text.startswith("e"):
        text = text[1:]
    try:
        return int(text)
    except ValueError:
        return None


def parse_alarm_descriptions(
    profile: dict[str, Any], translations: dict[str, str]
) -> dict[int, str]:
    """Build an alarm-code lookup from a component web profile."""
    alarms = profile.get("alarms")
    if not isinstance(alarms, dict):
        return {}
    descriptions = alarms.get("descriptions")
    if not isinstance(descriptions, list):
        return {}

    result: dict[int, str] = {}
    for item in descriptions:
        if not isinstance(item, dict):
            continue
        code = parse_alarm_code(item.get("code"))
        raw_description = item.get("description")
        if code is None or not isinstance(raw_description, str):
            continue
        translation_key = raw_description.removeprefix("@")
        result[code] = translations.get(
            translation_key,
            translations.get(raw_description, f"Alarm e{code}"),
        )
    return result
