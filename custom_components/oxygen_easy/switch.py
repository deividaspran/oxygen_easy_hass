"""Switch controls for Oxygen Easy controllers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .coordinator import OxygenCoordinator
from .entity import OxygenEntity
from .mqtt import OxygenMqttError


@dataclass(frozen=True, kw_only=True)
class OxygenSwitchDescription(SwitchEntityDescription):
    """Describe a writable Oxygen bit."""

    uid: str
    bit_mask: int
    write_on: str
    write_off: str
    capability_uid: str | None = None
    capability_mask: int = 0


SWITCHES: tuple[OxygenSwitchDescription, ...] = (
    OxygenSwitchDescription(
        key="power",
        translation_key="power",
        uid="u7074",
        bit_mask=1,
        write_on="H1L0",
        write_off="H0L1",
        icon="mdi:power",
    ),
    OxygenSwitchDescription(
        key="automatic_mode",
        translation_key="automatic_mode",
        uid="u7073",
        bit_mask=1,
        write_on="H1L0",
        write_off="H0L1",
        icon="mdi:autorenew",
    ),
    OxygenSwitchDescription(
        key="fireplace_mode",
        translation_key="fireplace_mode",
        uid="u6240",
        bit_mask=4,
        write_on="H4L0",
        write_off="H0L4",
        icon="mdi:fireplace",
    ),
    OxygenSwitchDescription(
        key="boost_1",
        translation_key="boost_1",
        uid="u6639",
        bit_mask=64,
        write_on="H64L0",
        write_off="H0L64",
        capability_uid="u6381",
        capability_mask=128,
        icon="mdi:fan-plus",
    ),
)


def _is_supported(
    description: OxygenSwitchDescription,
    values: dict[str, Any],
) -> bool:
    """Return whether the controller exposes a switch and its capability."""
    if description.uid not in values:
        return False
    if description.capability_uid is None:
        return True
    try:
        capabilities = int(values.get(description.capability_uid))
    except (TypeError, ValueError):
        return False
    return bool(capabilities & description.capability_mask)


def updated_bit_value(value: Any, bit_mask: int, enabled: bool) -> int:
    """Return a cached bitfield after applying a switch state."""
    try:
        current = int(value)
    except (TypeError, ValueError):
        current = 0
    return current | bit_mask if enabled else current & ~bit_mask


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up controller switches."""
    coordinator: OxygenCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        OxygenSwitch(coordinator, serial, description)
        for serial, values in coordinator.data.values.items()
        for description in SWITCHES
        if _is_supported(description, values)
    )


class OxygenSwitch(OxygenEntity, SwitchEntity):
    """Control one bit in an Oxygen controller parameter."""

    entity_description: OxygenSwitchDescription

    def __init__(
        self,
        coordinator: OxygenCoordinator,
        serial: str,
        description: OxygenSwitchDescription,
    ) -> None:
        super().__init__(coordinator, serial, description.uid)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return whether the controlled bit is set."""
        try:
            return bool(int(self.parameter_value) & self.entity_description.bit_mask)
        except (TypeError, ValueError):
            return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Set the controlled bit."""
        await self._async_set_state(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Clear the controlled bit."""
        await self._async_set_state(False)

    async def _async_set_state(self, enabled: bool) -> None:
        description = self.entity_description
        cached_value = updated_bit_value(
            self.parameter_value,
            description.bit_mask,
            enabled,
        )
        try:
            await self.coordinator.async_write_parameter(
                self.serial,
                self.uid,
                description.write_on if enabled else description.write_off,
                cached_value=cached_value,
            )
        except OxygenMqttError as err:
            raise HomeAssistantError(str(err)) from err
