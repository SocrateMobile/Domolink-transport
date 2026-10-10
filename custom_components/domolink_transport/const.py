import json
import os

DOMAIN = "domolink_transport"
NAME = "DomoLink-Transport"

_MANIFEST_PATH = os.path.join(os.path.dirname(__file__), "manifest.json")
try:
    with open(_MANIFEST_PATH, "r", encoding="utf-8") as _f:
        VERSION = json.load(_f).get("version", "1.0.5")
except Exception:
    VERSION = "1.0.5"

GITHUB_REPO = "SocrateMobile/Domolink-transport"
GITHUB_LATEST_RELEASE_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

PLATFORMS = ["sensor", "binary_sensor", "update", "switch", "button"]

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
DEFAULT_SCAN_INTERVAL = 180  # seconds (3 min pour préserver le quota 5000/j)
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

# Pre-mapped Stop Area IDs for popular stations (Fast resolution)
KNOWN_STATION_IDS = {
    "Enghien-les-Bains": "stop_area:SNCF:87276022",
    "Paris Nord": "stop_area:SNCF:87271007",
    "Ermont - Eaubonne": "stop_area:SNCF:87276055",
    "Saint-Denis": "stop_area:SNCF:87271015",
    "Épinay - Villetaneuse": "stop_area:SNCF:87276006",
    "Deuil - Montmagny": "stop_area:SNCF:87276014",
    "Champ de courses d'Enghien": "stop_area:SNCF:87276030",
    "La Barre Ormesson": "stop_area:SNCF:87276063",
    "Saint-Gratien": "stop_area:SNCF:87276071",
    "Cernay": "stop_area:SNCF:87276089",
    "Franconville - Le Plessis-Bouchard": "stop_area:SNCF:87276105",
    "Montigny - Beauchamp": "stop_area:SNCF:87276113",
    "Pierrelaye": "stop_area:SNCF:87276121",
    "Saint-Ouen-l'Aumône": "stop_area:SNCF:87276147",
    "Saint-Ouen-l'Aumône Liesse": "stop_area:SNCF:87276204",
    "Pontoise": "stop_area:SNCF:87276139",
    "Saint-Leu-la-Forêt": "stop_area:SNCF:87276154",
    "Taverny": "stop_area:SNCF:87276162",
    "Bessancourt": "stop_area:SNCF:87276170",
    "Frépillon": "stop_area:SNCF:87276188",
    "Méry-sur-Oise": "stop_area:SNCF:87276196",
    "Mériel": "stop_area:SNCF:87276212",
    "Valmondois": "stop_area:SNCF:87276220",
    "L'Isle-Adam - Parmain": "stop_area:SNCF:87276238",
    "Champagne-sur-Oise": "stop_area:SNCF:87276246",
    "Persan - Beaumont": "stop_area:SNCF:87276253",
    "Sarcelles - Saint-Brice": "stop_area:SNCF:87276303",
    "Écouen - Ézanville": "stop_area:SNCF:87276311",
    "Domont": "stop_area:SNCF:87276329",
    "Bouffémont - Moisselles": "stop_area:SNCF:87276337",
    "Montsoult - Maffliers": "stop_area:SNCF:87276345",
    "Belloy - Saint-Martin": "stop_area:SNCF:87276352",
    "Viarmes": "stop_area:SNCF:87276360",
    "Seugy": "stop_area:SNCF:87276378",
    "Luzarches": "stop_area:SNCF:87276386",
    "Paris Gare de Lyon": "stop_area:SNCF:87686006",
    "Paris Saint-Lazare": "stop_area:SNCF:87384008",
    "Paris Montparnasse": "stop_area:SNCF:87391003",
    "Paris Est": "stop_area:SNCF:87113001",
    "Paris Bercy": "stop_area:SNCF:87686667",
    "Paris Austerlitz": "stop_area:SNCF:87547000",
    "Châtelet - Les Halles": "stop_area:SNCF:87758607",
    "La Défense": "stop_area:SNCF:87382218",
}

# Popular station names for autocomplete suggestion dropdown
POPULAR_STATIONS = sorted(list(set(list(KNOWN_STATION_IDS.keys()) + [
    "Aéroport Charles de Gaulle 2 TGV",
    "Angers Saint-Laud",
    "Argenteuil",
    "Asnières-sur-Seine",
    "Aulnay-sous-Bois",
    "Bécon-les-Bruyères",
    "Bobigny - Pablo Picasso",
    "Bordeaux Saint-Jean",
    "Cergy le Haut",
    "Cergy Préfecture",
    "Cergy Saint-Christophe",
    "Chelles - Gournay",
    "Créteil Pompadour",
    "Dijon Ville",
    "Grenoble",
    "Juvisy",
    "Le Havre",
    "Lille Europe",
    "Lille Flandres",
    "Lyon Part-Dieu",
    "Lyon Perrache",
    "Maisons-Alfort - Alfortville",
    "Marne-la-Vallée Chessy",
    "Marseille Saint-Charles",
    "Massy - Palaiseau",
    "Meaux",
    "Melun",
    "Metz Ville",
    "Mitry - Claye",
    "Montpellier Saint-Roch",
    "Nanterre - Préfecture",
    "Nanterre - Université",
    "Nantes",
    "Nice Ville",
    "Noisy-le-Sec",
    "Poissy",
    "Reims",
    "Rennes",
    "Rouen Rive Droite",
    "Saint-Germain-en-Laye",
    "Saint-Quentin-en-Yvelines",
    "Strasbourg",
    "Toulouse Matabiau",
    "Tournan",
    "Tours",
    "Val d'Argenteuil",
    "Versailles Chantiers",
    "Versailles Château Rive Gauche",
    "Versailles Rive Droite",
    "Villeneuve-Saint-Georges",
])))

