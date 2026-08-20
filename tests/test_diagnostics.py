"""Diagnostics privacy tests for Oxygen Easy."""

import asyncio
from types import SimpleNamespace

from custom_components.oxygen_easy.const import DOMAIN
from custom_components.oxygen_easy.diagnostics import (
    async_get_config_entry_diagnostics,
)
from custom_components.oxygen_easy.models import (
    OxygenComponent,
    OxygenCoordinatorData,
    OxygenInstallation,
)


def test_diagnostics_exclude_private_identifiers() -> None:
    """Account details and device identifiers must never enter diagnostics."""
    private_values = {
        "person@example.com",
        "account-password",
        "installation-uuid",
        "gateway-serial",
        "My Home",
        "Bedroom Ventilation",
        "controller-serial",
    }
    data = OxygenCoordinatorData(
        installations={
            "installation-uuid": OxygenInstallation(
                installation_id="installation-uuid",
                name="My Home",
                serial="gateway-serial",
                custom_name="Bedroom Ventilation",
                hardware_version="test-hardware",
                software_version="test-software",
                connected=True,
            )
        },
        components={
            "controller-serial": OxygenComponent(
                installation_id="installation-uuid",
                serial="controller-serial",
                component_type="ecoVENT MINI OEM",
                custom_name="Bedroom Ventilation",
                hardware_version="test-hardware",
                software_version="test-software",
            )
        },
        values={"controller-serial": {"u6205": 20.8}},
    )
    entry = SimpleNamespace(
        entry_id="entry-id",
        data={"username": "person@example.com", "password": "account-password"},
    )
    coordinator = SimpleNamespace(data=data, last_update_success=True)
    hass = SimpleNamespace(data={DOMAIN: {entry.entry_id: coordinator}})

    diagnostics = asyncio.run(async_get_config_entry_diagnostics(hass, entry))
    serialized = repr(diagnostics)

    assert not any(value in serialized for value in private_values)
    assert diagnostics == {
        "configured_fields": ["password", "username"],
        "installations": [
            {
                "connected_at_discovery": True,
                "hardware_version": "test-hardware",
                "software_version": "test-software",
            }
        ],
        "components": [
            {
                "type": "ecoVENT MINI OEM",
                "manufacturer": "Oxygen",
                "hardware_version": "test-hardware",
                "software_version": "test-software",
                "available_parameters": ["u6205"],
            }
        ],
        "last_update_success": True,
    }
