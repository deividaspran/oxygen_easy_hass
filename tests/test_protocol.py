"""Protocol parser tests for Oxygen Easy."""

from custom_components.oxygen_easy.coordinator import _modification_status
from custom_components.oxygen_easy.mqtt import extract_values


def test_extract_values_from_get_values_response() -> None:
    """The first array item is the current parameter value."""
    response = {
        "transactionId": "2",
        "operations": [
            {
                "name": "GET_VALUES",
                "targets": [
                    {
                        "component": "controller-1",
                        "parameters": {
                            "u6205": [20.8, 0, 0],
                            "u6273": [61.7, 0, 0],
                        },
                    }
                ],
            }
        ],
    }

    assert extract_values(response) == {"controller-1": {"u6205": 20.8, "u6273": 61.7}}


def test_extract_values_from_notification() -> None:
    """Push messages may contain scalar values instead of arrays."""
    response = {
        "messages": [
            {
                "messageType": "PARAMS_UPDATE",
                "targets": [
                    {
                        "component": "controller-1",
                        "parameters": {"u7074": 1},
                    }
                ],
            }
        ]
    }

    assert extract_values(response) == {"controller-1": {"u7074": 1}}


def test_modification_status() -> None:
    """Find a write status in the nested operation response."""
    response = {
        "operations": [
            {
                "name": "PARAMS_MODIFICATION",
                "targets": [
                    {
                        "component": "controller-1",
                        "parameters": {"u7074": "16"},
                    }
                ],
            }
        ]
    }

    assert _modification_status(response, "controller-1", "u7074") == "16"


def test_modification_status_normalizes_numeric_component_id() -> None:
    """Firmware may encode an otherwise identical component ID as a number."""
    response = {
        "transactionId": "3",
        "operations": [
            {
                "name": "PARAMS_MODIFICATION",
                "targets": [
                    {
                        "component": 12345,
                        "parameters": {"u81": "0"},
                    }
                ],
            }
        ],
    }

    assert _modification_status(response, "12345", "u81") == "0"
