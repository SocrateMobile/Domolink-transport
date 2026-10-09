"""DataUpdateCoordinator for DomoLink-Transport."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any
import zoneinfo

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import DomolinkTransportApiClient
from .const import (
    CONF_API_KEY,
    CONF_CREATE_LEGACY_ENTITIES,
    CONF_PRIM_API_KEY,
    CONF_SCAN_INTERVAL,
    CONF_STATION_A,
    CONF_STATION_A_ID,
    CONF_STATION_B,
    CONF_STATION_B_ID,
    CONF_STATION_C,
    CONF_STATION_C_ID,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_STATION_A_ID,
    DEFAULT_STATION_A_NAME,
    DEFAULT_STATION_B_ID,
    DEFAULT_STATION_B_NAME,
    DEFAULT_STATION_C_ID,
    DEFAULT_STATION_C_NAME,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)
TZ_PARIS = zoneinfo.ZoneInfo("Europe/Paris")


class DomolinkTransportCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching DomoLink-Transport data from APIs."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        scan_interval = entry.options.get(
            CONF_SCAN_INTERVAL,
            entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

        session = async_get_clientsession(hass)
        api_key = entry.options.get(CONF_API_KEY, entry.data.get(CONF_API_KEY, ""))
        prim_key = entry.options.get(CONF_PRIM_API_KEY, entry.data.get(CONF_PRIM_API_KEY))

        self.api = DomolinkTransportApiClient(session, api_key, prim_key)

        # Gares
        self.station_a_name = entry.options.get(CONF_STATION_A, entry.data.get(CONF_STATION_A, DEFAULT_STATION_A_NAME))
        self.station_a_id = entry.options.get(CONF_STATION_A_ID, entry.data.get(CONF_STATION_A_ID, DEFAULT_STATION_A_ID))

        self.station_b_name = entry.options.get(CONF_STATION_B, entry.data.get(CONF_STATION_B, DEFAULT_STATION_B_NAME))
        self.station_b_id = entry.options.get(CONF_STATION_B_ID, entry.data.get(CONF_STATION_B_ID, DEFAULT_STATION_B_ID))

        self.station_c_name = entry.options.get(CONF_STATION_C, entry.data.get(CONF_STATION_C, DEFAULT_STATION_C_NAME))
        st_c_id = entry.options.get(CONF_STATION_C_ID, entry.data.get(CONF_STATION_C_ID, DEFAULT_STATION_C_ID))
        if st_c_id == "stop_area:SNCF:87276156":
            st_c_id = DEFAULT_STATION_C_ID
        self.station_c_id = st_c_id

        self.create_legacy_entities = entry.options.get(
            CONF_CREATE_LEGACY_ENTITIES,
            entry.data.get(CONF_CREATE_LEGACY_ENTITIES, True),
        )

        # Caches intelligents pour préserver le quota de 5000 requêtes/jour
        self._cached_last_b_to_a: dict[str, Any] | None = None
        self._cached_last_c_to_a: dict[str, Any] | None = None
        self._last_return_cache_time: datetime | None = None

        self._cached_disruptions: list[dict[str, Any]] = []
        self._disruptions_cache_time: datetime | None = None

        self._previous_data: dict[str, Any] | None = None

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from APIs with Eco-Quota optimization."""
        now = datetime.now(TZ_PARIS)

        # Coupure nocturne (01h30 - 04h45) : Aucun train ne circule
        # On évite de gaspiller des requêtes API SNCF la nuit
        is_deep_night = 1 <= now.hour < 5 and (now.hour > 1 or now.minute >= 15) and (now.hour < 4 or now.minute <= 45)

        try:
            # 1. Trajets A -> B et A -> C (uniquement si le service est actif)
            if not is_deep_night:
                a_to_b = await self.api.async_get_next_journeys(self.station_a_id, self.station_b_id, count=5)
                a_to_c = await self.api.async_get_next_journeys(self.station_a_id, self.station_c_id, count=5)
                b_to_a = await self.api.async_get_next_journeys(self.station_b_id, self.station_a_id, count=3)
                c_to_a = await self.api.async_get_next_journeys(self.station_c_id, self.station_a_id, count=3)
            else:
                a_to_b = []
                a_to_c = []
                b_to_a = []
                c_to_a = []

            # 2. Gestion du cache pour le dernier train de nuit (rafraîchi toutes les 30 minutes seulement)
            # Économise plus de 1300 requêtes par jour !
            if (
                self._last_return_cache_time is None
                or (now - self._last_return_cache_time).total_seconds() > 1800
                or self._cached_last_b_to_a is None
                or self._cached_last_c_to_a is None
            ):
                last_b = await self.api.async_get_last_night_journey(self.station_b_id, self.station_a_id)
                last_c = await self.api.async_get_last_night_journey(self.station_c_id, self.station_a_id)
                if last_b:
                    self._cached_last_b_to_a = last_b
                if last_c:
                    self._cached_last_c_to_a = last_c
                self._last_return_cache_time = now

            last_return_b_to_a = self._cached_last_b_to_a
            last_return_c_to_a = self._cached_last_c_to_a

            # Recalcul en direct du compte à rebours sans aucun appel API
            if last_return_b_to_a and last_return_b_to_a.get("departure_datetime"):
                dep_dt = last_return_b_to_a["departure_datetime"]
                last_return_b_to_a["minutes_remaining"] = int(round((dep_dt - now).total_seconds() / 60))

            if last_return_c_to_a and last_return_c_to_a.get("departure_datetime"):
                dep_dt = last_return_c_to_a["departure_datetime"]
                last_return_c_to_a["minutes_remaining"] = int(round((dep_dt - now).total_seconds() / 60))

            # 3. Gestion du cache pour les perturbations (rafraîchi toutes les 15 minutes)
            # Économise plus de 600 requêtes par jour !
            if (
                self._disruptions_cache_time is None
                or (now - self._disruptions_cache_time).total_seconds() > 900
            ):
                disruptions = await self.api.async_get_line_disruptions("H")
                if disruptions is not None:
                    self._cached_disruptions = disruptions
                    self._disruptions_cache_time = now

            disruptions = self._cached_disruptions

            # Si l'API renvoie des listes vides suite à un blocage de quota (HTTP 429),
            # on conserve les dernières données valides pour éviter d'effacer le tableau
            quota_reached = getattr(self.api, "quota_reached", False)
            if quota_reached and self._previous_data:
                _LOGGER.warning("DomoLink-Transport : Quota SNCF 5000/j atteint. Conservation des données en cache.")
                result = dict(self._previous_data)
                result["quota_reached"] = True
                result["last_updated"] = now.isoformat()
                return result

            result_data = {
                "station_a": {"name": self.station_a_name, "id": self.station_a_id},
                "station_b": {"name": self.station_b_name, "id": self.station_b_id},
                "station_c": {"name": self.station_c_name, "id": self.station_c_id},
                "a_to_b": a_to_b,
                "a_to_c": a_to_c,
                "b_to_a": b_to_a,
                "c_to_a": c_to_a,
                "last_return_b_to_a": last_return_b_to_a,
                "last_return_c_to_a": last_return_c_to_a,
                "disruptions": disruptions,
                "quota_reached": quota_reached,
                "last_updated": now.isoformat(),
            }
            if a_to_b or b_to_a:
                self._previous_data = result_data

            return result_data
        except Exception as err:
            _LOGGER.error("Erreur de mise à jour DomoLink-Transport: %s", err)
            if self._previous_data:
                return self._previous_data
            raise UpdateFailed(f"Erreur de communication avec l'API: {err}") from err
