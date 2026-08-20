"""Data models for Oxygen Easy."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class OxygenInstallation:
    """An Oxygen cloud installation."""

    installation_id: str
    name: str
    serial: str
    custom_name: str
    hardware_version: str | None = None
    software_version: str | None = None
    connected: bool = False


@dataclass(frozen=True, slots=True)
class OxygenComponent:
    """A ventilation controller attached to an installation."""

    installation_id: str
    serial: str
    component_type: str
    custom_name: str
    manufacturer: str = "Oxygen"
    hardware_version: str | None = None
    software_version: str | None = None

    @property
    def display_name(self) -> str:
        """Return a friendly controller name."""
        return self.custom_name or self.component_type


@dataclass(slots=True)
class OxygenCoordinatorData:
    """Coordinator state shared by all entities."""

    installations: dict[str, OxygenInstallation] = field(default_factory=dict)
    components: dict[str, OxygenComponent] = field(default_factory=dict)
    values: dict[str, dict[str, Any]] = field(default_factory=dict)

    def clone(self) -> OxygenCoordinatorData:
        """Copy mutable state before notifying coordinator listeners."""
        return OxygenCoordinatorData(
            installations=dict(self.installations),
            components=dict(self.components),
            values={serial: dict(values) for serial, values in self.values.items()},
        )
