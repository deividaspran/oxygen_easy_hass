"""Fan-level control tests for Oxygen Easy."""

from custom_components.oxygen_easy.select import (
    OPTION_TO_READ_VALUE,
    OPTION_TO_WRITE_VALUE,
    READ_VALUE_TO_OPTION,
)


def test_fan_levels_use_profile_bit_masks() -> None:
    """Writes must use the bit-mask strings from the controller profile."""
    assert OPTION_TO_WRITE_VALUE == {
        "low": "H3L252",
        "medium": "H4L251",
        "high": "H5L250",
        "paused": "H6L249",
    }
    assert READ_VALUE_TO_OPTION == {
        3: "low",
        4: "medium",
        5: "high",
        6: "paused",
    }
    assert OPTION_TO_READ_VALUE == {
        "low": 3,
        "medium": 4,
        "high": 5,
        "paused": 6,
    }
