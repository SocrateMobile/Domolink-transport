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

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from APIs."""
        try:
            # 1. Trajets A -> B (3 à 5 prochains départs)
            a_to_b = await self.api.async_get_next_journeys(self.station_a_id, self.station_b_id, count=5)

            # 2. Trajets A -> C (3 à 5 prochains départs)
            a_to_c = await self.api.async_get_next_journeys(self.station_a_id, self.station_c_id, count=5)

            # 3. Trajets retours B -> A (3 prochains départs)
            b_to_a = await self.api.async_get_next_journeys(self.station_b_id, self.station_a_id, count=3)

            # 4. Trajets retours C -> A (3 prochains départs)
            c_to_a = await self.api.async_get_next_journeys(self.station_c_id, self.station_a_id, count=3)

            # 5. Dernier train de nuit B -> A (entre 22h et 03h30)
            last_return_b_to_a = await self.api.async_get_last_night_journey(self.station_b_id, self.station_a_id)

            # 6. Dernier train de nuit C -> A (entre 22h et 03h30)
            last_return_c_to_a = await self.api.async_get_last_night_journey(self.station_c_id, self.station_a_id)

            # 7. Perturbations de la ligne H
            disruptions = await self.api.async_get_line_disruptions("H")

            return {
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
                "last_updated": datetime.now(TZ_PARIS).isoformat(),
            }
        except Exception as err:
            _LOGGER.error("Erreur de mise à jour DomoLink-Transport: %s", err)
            raise UpdateFailed(f"Erreur de communication avec l'API: {err}") from err
