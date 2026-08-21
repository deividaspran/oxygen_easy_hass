# Oxygen Easy for Home Assistant

[![Validate](https://github.com/deividaspran/oxygen_easy_hass/actions/workflows/validate.yml/badge.svg)](https://github.com/deividaspran/oxygen_easy_hass/actions/workflows/validate.yml)

Unofficial Home Assistant custom integration for Oxygen / ecoVENT MINI OEM
ventilation controllers. It uses the same Cognito, account API, and AWS IoT MQTT
cloud path as the current Oxygen Easy app.

## Features

- UI configuration with the existing Oxygen Easy email and password
- Automatic installation and controller discovery
- MQTT push updates, reconnect handling, and a 60-second snapshot refresh
- Outdoor, supply, extract, and exhaust temperatures
- Humidity, CO₂, supply/extract airflow, and supply/extract fan output
- Supply/extract filter condition and bypass position
- Bypass status
- Power switch
- Low, medium, high, and paused fan-level control
- Manual/schedule operating mode and timed away/party/airing modes
- Day/night/schedule comfort mode with day and night temperature setpoints
- Automatic, fireplace, and supported Boost 1 switches
- Unit operating status, lead/heat-exchanger temperatures, airflow setpoints,
  and party-mode time remaining
- Internet-gateway date/time, temperature, humidity, timezone mode, button
  brightness, and button/alarm volume
- Supply/extract filter-replacement problem sensors and a persistent Home
  Assistant notification when the controller requests replacement
- Persistent notifications for active controller and internet-gateway alarms,
  using the model profile's English alarm descriptions
- Credential reauthentication and redacted diagnostics

## Installation

### Manual

1. Copy `custom_components/oxygen_easy` into the `custom_components` directory
   inside your Home Assistant configuration directory.
2. Restart Home Assistant.
3. Open **Settings → Devices & services → Add integration**.
4. Search for **Oxygen Easy** and enter the same credentials as the app.

For a typical Home Assistant OS installation, the resulting path is:

```text
/config/custom_components/oxygen_easy
```

### HACS custom repository

[![Open your Home Assistant instance and add this repository to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=deividaspran&repository=oxygen_easy_hass&category=integration)

Use the button above, or add
`https://github.com/deividaspran/oxygen_easy_hass` to HACS as an
**Integration**. Install Oxygen Easy, restart Home Assistant, and follow the
same UI configuration steps.

## Notes

- This is a cloud integration and needs internet access. It does not communicate
  directly with the controller over the local network.
- Credentials are stored in Home Assistant's config-entry storage. Passwords,
  Cognito tokens, AWS secrets, and signed MQTT URLs are not logged or included in
  diagnostics.
- Controls use the app's profile-defined `PARAMS_MODIFICATION` masks and
  require a controller success status before local state changes.
- Sensors with a measurement state class are recorded by Home Assistant and can
  be graphed from the entity History view or dashboard. History begins when Home
  Assistant starts recording the entity; the Oxygen cloud archive is not
  imported. The integration exposes every numeric/status series used by the
  Oxygen chart that is available in the live controller snapshot.
- Filter values are exposed as **filter condition** because the cloud reports a
  percentage whose direction is not labeled reliably. Replacement alerts use
  the controller's separate supply/extract replacement flags instead.
- This project is not affiliated with Oxygen or Plum.
- The OXYGEN name and logo are trademarks of OXYGEN GROUP, UAB. The bundled
  brand assets are used only to identify compatible products.

## Troubleshooting

Enable debug logging temporarily:

```yaml
logger:
  logs:
    custom_components.oxygen_easy: debug
```

Then reload the integration. Home Assistant diagnostics include connection and
firmware metadata plus available parameter IDs, but no account details, custom
names, installation IDs, or controller serial numbers.
