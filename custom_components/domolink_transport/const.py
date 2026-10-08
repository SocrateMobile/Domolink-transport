import json
import os

DOMAIN = "domolink_transport"
NAME = "DomoLink-Transport"

_MANIFEST_PATH = os.path.join(os.path.dirname(__file__), "manifest.json")
try:
    with open(_MANIFEST_PATH, "r", encoding="utf-8") as _f:
        VERSION = json.load(_f).get("version", "1.0.4")
except Exception:
    VERSION = "1.0.4"

GITHUB_REPO = "SocrateMobile/Domolink-transport"
GITHUB_LATEST_RELEASE_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

PLATFORMS = ["sensor", "binary_sensor", "update"]

# Sidebar Panel
PANEL_NAME = "domolink-transport-panel"
PANEL_TITLE = "DomoLink Transports"
PANEL_ICON = "mdi:train-car"
PANEL_URL_PATH = "domolink-transport"
FRONTEND_URL_PATH = "/domolink_transport_frontend"
FRONTEND_FILE_NAME = "domolink-transport-panel.js"

# Configuration keys
CONF_API_KEY = "api_key"
CONF_PRIM_API_KEY = "prim_api_key"
CONF_STATION_A = "station_a"
CONF_STATION_A_ID = "station_a_id"
CONF_STATION_B = "station_b"
CONF_STATION_B_ID = "station_b_id"
CONF_STATION_C = "station_c"
CONF_STATION_C_ID = "station_c_id"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_ENABLE_PANEL = "enable_panel"
CONF_CREATE_LEGACY_ENTITIES = "create_legacy_entities"

# Defaults
DEFAULT_SCAN_INTERVAL = 120  # seconds
DEFAULT_STATION_A_NAME = "Enghien-les-Bains"
DEFAULT_STATION_A_ID = "stop_area:SNCF:87276022"

DEFAULT_STATION_B_NAME = "Paris Nord"
DEFAULT_STATION_B_ID = "stop_area:SNCF:87271007"

DEFAULT_STATION_C_NAME = "Ermont - Eaubonne"
DEFAULT_STATION_C_ID = "stop_area:SNCF:87276055"

# Base API URLs
SNCF_API_URL = "https://api.sncf.com/v1"
NAVITIA_API_URL = "https://api.navitia.io/v1"
PRIM_API_URL = "https://prim.iledefrance-mobilites.fr/marketplace"
