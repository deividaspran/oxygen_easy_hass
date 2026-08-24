"""Constants for the Oxygen Easy integration."""

from datetime import timedelta

DOMAIN = "oxygen_easy"
PLATFORMS = ["binary_sensor", "button", "number", "select", "sensor", "switch"]

CONF_USERNAME = "username"
CONF_PASSWORD = "password"

REGION = "eu-central-1"
USER_POOL_ID = "eu-central-1_que8JCEVH"
CLIENT_ID = "3qga0ntgrj7fblcgau24plp2h4"
IDENTITY_POOL_ID = "eu-central-1:d1f8d4ae-7401-4d69-b603-1e992f635253"
API_HOST = "6tx17a8ijh.execute-api.eu-central-1.amazonaws.com"
API_STAGE = "/prod"
APP_ID = "251"
IOT_ENDPOINT = "a24t7r3f2r1nrr-ats.iot.eu-central-1.amazonaws.com"
ARCHIVES_API = "https://api.econetcloud.eu/api"

UPDATE_INTERVAL = timedelta(seconds=60)
REQUEST_TIMEOUT = 20
CREDENTIAL_REFRESH_MARGIN = timedelta(minutes=5)

CONTROLLER_TYPE = "ecoVENT MINI OEM"

MONITORED_UIDS = (
    "u6209",  # Outdoor/inlet temperature
    "u6208",  # Exhaust temperature
    "u6205",  # Supply temperature
    "u6207",  # Extract temperature
    "u6206",  # Temperature after heat exchanger
    "u6350",  # Ground heat exchanger temperature
    "u6338",  # Lead temperature
    "u6273",  # Humidity
    "u6265",  # CO2
    "u6828",  # Supply airflow
    "u6829",  # Extract airflow
    "u6812",  # Supply airflow setpoint
    "u6813",  # Extract airflow setpoint
    "u6202",  # Supply fan
    "u6203",  # Extract fan
    "u6938",  # Supply filter condition
    "u6939",  # Extract filter condition
    "u6832",  # Filter replacement flags
    "u6332",  # Bypass opening
    "u6322",  # Bypass active
    "u7074",  # Unit power
    "u7073",  # Automatic mode
    "u6630",  # Schedule mode
    "u81",  # Fan level
    "u7124",  # Comfort mode
    "u7125",  # Day comfort temperature
    "u7126",  # Night comfort temperature
    "u7151",  # Unit operating status
    "u84",  # Timed mode
    "u6425",  # Party mode duration
    "u6429",  # Party mode time remaining
    "u6240",  # Fireplace mode
    "u6639",  # Boost modes
    "u6381",  # Available boost modes
)

GATEWAY_MONITORED_UIDS = (
    "u9849",  # Gateway date and time
    "u9848",  # Timezone selection mode
    "u3296",  # Timezone
    "u3263",  # Button brightness
    "u3282",  # Button sound volume
    "u3283",  # Alarm sound volume
    "u3286",  # Gateway temperature
    "u3287",  # Gateway humidity
    "u9223",  # Gateway hardware capabilities
)
