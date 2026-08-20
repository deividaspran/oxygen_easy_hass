"""Optional live, read-only Oxygen cloud smoke test.

Run with USERNAME and PASSWORD in the environment. The script intentionally
prints no identifiers, credentials, tokens, or signed URLs.
"""

from __future__ import annotations

import asyncio
import importlib
import os
import sys
import types
from pathlib import Path


def load_protocol_modules():
    """Load protocol modules without requiring a Home Assistant installation."""
    component_dir = (
        Path(__file__).parents[1] / "custom_components" / "oxygen_easy"
    ).resolve()
    package_name = "oxygen_easy_protocol_test"
    package = types.ModuleType(package_name)
    package.__path__ = [str(component_dir)]
    sys.modules[package_name] = package
    api = importlib.import_module(f"{package_name}.api")
    const = importlib.import_module(f"{package_name}.const")
    mqtt = importlib.import_module(f"{package_name}.mqtt")
    return api, const, mqtt


async def main() -> None:
    """Authenticate, discover, and read the verified parameter set once."""
    username = os.environ["USERNAME"]
    password = os.environ["PASSWORD"]
    api, const, mqtt_module = load_protocol_modules()
    session = api.OxygenCloudSession(username, password)
    loop = asyncio.get_running_loop()
    installations = await loop.run_in_executor(None, session.installations)
    routes: dict[str, list[str]] = {}
    for installation in installations:
        installation_id = installation["id"]
        details = await loop.run_in_executor(
            None, session.installation_details, installation_id
        )
        routes[installation_id] = [
            item["componentFn"]
            for item in details.get("components", [])
            if item.get("componentType") == const.CONTROLLER_TYPE
        ]

    pushed: dict[str, dict] = {}
    client = mqtt_module.OxygenMqttClient(
        session,
        lambda values: pushed.update(values),
    )
    try:
        await client.async_ensure_connected(set(routes))
        snapshot: dict[str, dict] = {}
        for installation_id, serials in routes.items():
            response = await client.async_send_operation(
                installation_id,
                {
                    "name": "GET_VALUES",
                    "targets": [
                        {
                            "component": serial,
                            "parameters": list(const.MONITORED_UIDS),
                        }
                        for serial in serials
                    ],
                },
            )
            snapshot.update(mqtt_module.extract_values(response))
        parameter_count = sum(len(values) for values in snapshot.values())
        print(
            f"ok: installations={len(installations)} "
            f"controllers={sum(map(len, routes.values()))} "
            f"parameters={parameter_count}"
        )
    finally:
        await client.async_disconnect()


if __name__ == "__main__":
    asyncio.run(main())
