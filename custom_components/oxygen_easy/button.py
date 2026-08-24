"""Filter maintenance buttons for Oxygen Easy controllers."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .coordinator import OxygenCoordinator
from .entity import OxygenEntity
from .mqtt import OxygenMqttError


@dataclass(frozen=True, kw_only=True)
class OxygenButtonDescription(ButtonEntityDescription):
    """Describe a momentary Oxygen maintenance command."""

    command: str


FILTER_RESET_BUTTONS: tuple[OxygenButtonDescription, ...] = (
    OxygenButtonDescription(
        key="reset_supply_filter",
        translation_key="reset_supply_filter",
        command="H2L253",
        icon="mdi:air-filter",
    ),
    OxygenButtonDescription(
        key="reset_extract_filter",
        translation_key="reset_extract_filter",
        command="H3L252",
        icon="mdi:air-filter",
    ),
    OxygenButtonDescription(
        key="reset_both_filters",
        translation_key="reset_both_filters",
        command="H7L248",
        icon="mdi:air-filter",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up filter maintenance buttons."""
    coordinator: OxygenCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        OxygenFilterResetButton(coordinator, serial, description)
        for serial, component in coordinator.data.components.items()
        if not component.is_gateway
        for description in FILTER_RESET_BUTTONS
    )


class OxygenFilterResetButton(OxygenEntity, ButtonEntity):
    """Reset one or both filter operation counters."""

    entity_description: OxygenButtonDescription

    def __init__(
        self,
        coordinator: OxygenCoordinator,
        serial: str,
        description: OxygenButtonDescription,
    ) -> None:
        super().__init__(coordinator, serial, "u6904")
        self.entity_description = description
        self._attr_unique_id = f"{serial}_{description.key}"

    async def async_press(self) -> None:
        """Send a momentary filter reset command."""
        try:
            await self.coordinator.async_write_parameter(
                self.serial,
                self.uid,
                self.entity_description.command,
                update_cache=False,
            )
        except OxygenMqttError as err:
            raise HomeAssistantError(str(err)) from err
