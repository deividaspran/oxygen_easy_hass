"""Controller profile mapping tests for Oxygen Easy."""

from custom_components.oxygen_easy.coordinator import (
    filter_replacement_parts,
    parse_alarm_code,
    parse_alarm_descriptions,
)
from custom_components.oxygen_easy.number import NUMBERS
from custom_components.oxygen_easy.select import (
    COMFORT_MODE_OPTION_TO_WRITE_VALUE,
    COMFORT_MODE_READ_VALUE_TO_OPTION,
    OPERATING_MODE_OPTION_TO_WRITE_VALUE,
    OPERATING_MODE_READ_VALUE_TO_OPTION,
    TIMED_MODE_OPTION_TO_WRITE_VALUE,
    TIMED_MODE_READ_VALUE_TO_OPTION,
    TIMEZONE_MODE_OPTION_TO_WRITE_VALUE,
    TIMEZONE_MODE_READ_VALUE_TO_OPTION,
)
from custom_components.oxygen_easy.sensor import _nonnegative, _unit_status
from custom_components.oxygen_easy.switch import (
    SWITCHES,
    _is_supported,
    updated_bit_value,
)


def test_dashboard_selects_use_profile_masks() -> None:
    """Dashboard option writes must use the controller profile masks."""
    assert OPERATING_MODE_OPTION_TO_WRITE_VALUE == {
        "manual": "H0L1",
        "schedule": "H1L0",
    }
    assert OPERATING_MODE_READ_VALUE_TO_OPTION == {
        0: "manual",
        1: "schedule",
    }
    assert COMFORT_MODE_OPTION_TO_WRITE_VALUE == {
        "schedule": "H0L255",
        "day": "H1L254",
        "night": "H2L253",
    }
    assert COMFORT_MODE_READ_VALUE_TO_OPTION == {
        0: "schedule",
        1: "day",
        2: "night",
    }
    assert TIMED_MODE_OPTION_TO_WRITE_VALUE == {
        "off": "H0L255",
        "away": "H1L254",
        "party": "H2L253",
        "airing": "H4L251",
    }
    assert TIMED_MODE_READ_VALUE_TO_OPTION == {
        0: "off",
        1: "away",
        2: "party",
        4: "airing",
    }
    assert TIMEZONE_MODE_OPTION_TO_WRITE_VALUE == {
        "automatic": 0,
        "manual": 1,
    }
    assert TIMEZONE_MODE_READ_VALUE_TO_OPTION == {
        0: "automatic",
        1: "manual",
    }


def test_dashboard_switches_use_profile_masks() -> None:
    """Switch writes and controlled bits must match the controller profile."""
    mappings = {
        item.key: (item.uid, item.bit_mask, item.write_on, item.write_off)
        for item in SWITCHES
    }
    assert mappings == {
        "power": ("u7074", 1, "H1L0", "H0L1"),
        "automatic_mode": ("u7073", 1, "H1L0", "H0L1"),
        "fireplace_mode": ("u6240", 4, "H4L0", "H0L4"),
        "boost_1": ("u6639", 64, "H64L0", "H0L64"),
    }


def test_switch_cached_value_preserves_other_bits() -> None:
    """Optimistic updates must change only the switch's controlled bit."""
    assert updated_bit_value(5, 64, True) == 69
    assert updated_bit_value(69, 64, False) == 5
    assert updated_bit_value(None, 4, True) == 4


def test_boost_switch_requires_profile_capability() -> None:
    """Boost 1 appears only when the controller advertises capability bit 128."""
    boost = next(item for item in SWITCHES if item.key == "boost_1")
    assert _is_supported(boost, {"u6639": 0, "u6381": 129})
    assert not _is_supported(boost, {"u6639": 0, "u6381": 1})


def test_filter_replacement_flags_are_exact() -> None:
    """Wear percentages must not be mistaken for replacement requests."""
    assert filter_replacement_parts(1) == ()
    assert filter_replacement_parts(16) == ("supply air filter",)
    assert filter_replacement_parts(32) == ("extraction air filter",)
    assert filter_replacement_parts(48) == (
        "supply air filter",
        "extraction air filter",
    )
    assert filter_replacement_parts(None) is None


def test_alarm_profile_descriptions_are_translated() -> None:
    """Alarm codes should use the model profile's English text."""
    profile = {
        "alarms": {
            "descriptions": [
                {"code": "e37", "description": "@ALARM_37"},
                {"code": "bad", "description": "@IGNORED"},
            ]
        }
    }
    assert parse_alarm_descriptions(profile, {"ALARM_37": "Supply fan fault"}) == {
        37: "Supply fan fault"
    }
    assert parse_alarm_descriptions({}, {}) == {}


def test_alarm_codes_accept_archive_and_profile_formats() -> None:
    """Archive integer codes and profile e-prefixed codes should match."""
    assert parse_alarm_code(37) == 37
    assert parse_alarm_code("e37") == 37
    assert parse_alarm_code("E37") == 37
    assert parse_alarm_code(None) is None
    assert parse_alarm_code("invalid") is None


def test_chart_value_transforms() -> None:
    """Chart-facing enum and duration values should remain valid HA states."""
    assert _unit_status(3) == "normal"
    assert _unit_status(15) == "cold_recovery"
    assert _unit_status("bad") is None
    assert _nonnegative(-1) is None
    assert _nonnegative(12) == 12


def test_number_ranges_match_live_controller_profile() -> None:
    """Number controls must stay within the ranges reported by GET_VALUES."""
    ranges = {
        item.key: (
            item.native_min_value,
            item.native_max_value,
            item.native_step,
        )
        for item in NUMBERS
    }
    assert ranges == {
        "day_comfort_temperature": (8, 30, 1),
        "gateway_alarm_volume": (0, 50, 1),
        "gateway_button_brightness": (1, 3, 1),
        "gateway_button_volume": (0, 50, 1),
        "night_comfort_temperature": (8, 30, 1),
        "party_mode_duration": (1, 15, 1),
    }
