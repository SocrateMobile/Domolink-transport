"""API Client for DomoLink-Transport (SNCF / Navitia / PRIM IDFM)."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any
import zoneinfo

import aiohttp

from .const import NAVITIA_API_URL, PRIM_API_URL, SNCF_API_URL

_LOGGER = logging.getLogger(__name__)
TZ_PARIS = zoneinfo.ZoneInfo("Europe/Paris")


class DomolinkTransportApiClient:
    """Client for fetching journeys, departures, platforms and disruptions."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        api_key: str,
        prim_api_key: str | None = None,
    ) -> None:
        """Initialize API client."""
        self._session = session
        self._api_key = api_key.strip() if api_key else ""
        self._prim_api_key = prim_api_key.strip() if prim_api_key else None

    async def async_search_station(self, query: str) -> list[dict[str, str]]:
        """Search for station stop_areas by text."""
        if not query or len(query) < 2:
            return []

        url = f"{SNCF_API_URL}/coverage/sncf/places"
        params = {"q": query, "type[]": "stop_area"}
        headers = {"Authorization": self._api_key}

        try:
            async with self._session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=6)) as resp:
                if resp.status != 200:
                    _LOGGER.debug("Station search HTTP %s", resp.status)
                    return []
                data = await resp.json()
                results = []
                for p in data.get("places", []):
                    sa = p.get("stop_area", {})
                    if sa and sa.get("id"):
                        results.append({
                            "id": sa.get("id"),
                            "name": sa.get("name") or p.get("name", ""),
                            "label": sa.get("label") or p.get("name", ""),
                        })
                return results
        except Exception as err:
            _LOGGER.error("Erreur lors de la recherche de gare '%s': %s", query, err)
            return []

    async def async_get_next_journeys(
        self,
        from_id: str,
        to_id: str,
        count: int = 3,
    ) -> list[dict[str, Any]]:
        """Fetch next journeys between origin and destination."""
        url = f"{SNCF_API_URL}/coverage/sncf/journeys"
        now = datetime.now(TZ_PARIS)
        datetime_str = now.strftime("%Y%m%dT%H%M%S")

        params = {
            "from": from_id,
            "to": to_id,
            "datetime": datetime_str,
            "datetime_represents": "departure",
            "min_nb_journeys": max(count, 3),
            "data_freshness": "realtime",
        }
        headers = {"Authorization": self._api_key}

        try:
            async with self._session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status != 200:
                    _LOGGER.warning("Erreur API SNCF journeys (%s -> %s): HTTP %s", from_id, to_id, resp.status)
                    return []
                data = await resp.json()
                journeys = data.get("journeys", [])
                parsed = [self._parse_journey(j, from_id, to_id) for j in journeys]
                # Filter out past journeys if diff < 0
                valid = [p for p in parsed if p is not None]
                return valid[:count]
        except Exception as err:
            _LOGGER.error("Exception API SNCF journeys (%s -> %s): %s", from_id, to_id, err)
            return []

    async def async_get_last_night_journey(
        self,
        from_id: str,
        to_id: str,
    ) -> dict[str, Any] | None:
        """Fetch the last return train before nocturnal interruption."""
        now = datetime.now(TZ_PARIS)
        
        # Si on est entre 00h et 04h du matin, la soirée a débuté hier à 21h00
        if now.hour < 4:
            start_date = (now - timedelta(days=1)).strftime("%Y%m%d")
        else:
            start_date = now.strftime("%Y%m%d")

        from_datetime = f"{start_date}T210000"

        url = f"{SNCF_API_URL}/coverage/sncf/journeys"
        params = {
            "from": from_id,
            "to": to_id,
            "from_datetime": from_datetime,
            "datetime_represents": "departure",
            "min_nb_journeys": 20,
            "data_freshness": "realtime",
        }
        headers = {"Authorization": self._api_key}

        try:
            async with self._session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status != 200:
                    _LOGGER.warning("Erreur API dernier train (%s -> %s): HTTP %s", from_id, to_id, resp.status)
                    return None
                data = await resp.json()
                journeys = data.get("journeys", [])
                if not journeys:
                    return None
                
                # Filtrer et trier par heure de départ croissante
                valid_journeys = [j for j in journeys if j.get("departure_date_time")]
                # Priorité aux trajets sans correspondances si existants
                direct_journeys = [j for j in valid_journeys if j.get("nb_transfers", 0) == 0]
                if direct_journeys:
                    target_list = direct_journeys
                else:
                    target_list = valid_journeys

                target_list.sort(key=lambda x: x.get("departure_date_time", ""))

                # Détection du dernier train avant la coupure nocturne (trou >= 120 minutes)
                last_raw = None
                for i in range(len(target_list)):
                    dep_str = target_list[i].get("departure_date_time")
                    dep_dt = datetime.strptime(dep_str, "%Y%m%dT%H%M%S").replace(tzinfo=TZ_PARIS)
                    
                    if i + 1 < len(target_list):
                        next_dep_str = target_list[i + 1].get("departure_date_time")
                        next_dep_dt = datetime.strptime(next_dep_str, "%Y%m%dT%H%M%S").replace(tzinfo=TZ_PARIS)
                        gap_minutes = (next_dep_dt - dep_dt).total_seconds() / 60
                        if gap_minutes >= 120:
                            # Coupure nocturne détectée !
                            last_raw = target_list[i]
                            break
                    else:
                        if dep_dt.hour < 4:
                            last_raw = target_list[i]

                # Fallback : dernier train partant entre 21h et 03h30
                if not last_raw and target_list:
                    night_trains = []
                    for j in target_list:
                        dep_str = j.get("departure_date_time")
                        if dep_str:
                            dt = datetime.strptime(dep_str, "%Y%m%dT%H%M%S").replace(tzinfo=TZ_PARIS)
                            if dt.hour >= 21 or dt.hour < 4:
                                night_trains.append(j)
                    if night_trains:
                        last_raw = night_trains[-1]

                if last_raw:
                    return self._parse_journey(last_raw, from_id, to_id)
                return None
        except Exception as err:
            _LOGGER.error("Exception API dernier train (%s -> %s): %s", from_id, to_id, err)
            return None

    async def async_get_line_disruptions(self, line_code: str = "H") -> list[dict[str, Any]]:
        """Fetch active disruptions for a specific line."""
        url = f"{SNCF_API_URL}/coverage/sncf/disruptions"
        headers = {"Authorization": self._api_key}

        try:
            async with self._session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=6)) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                disruptions = []
                for d in data.get("disruptions", []):
                    status = d.get("status")
                    if status not in ("active", "current", "future", "past"):
                        continue
                    # Check if relevant to line
                    messages = []
                    for m in d.get("messages", []):
                        if m.get("text"):
                            messages.append(m.get("text"))
                    full_text = " ".join(messages)
                    if line_code.lower() in full_text.lower() or f"ligne {line_code.lower()}" in full_text.lower():
                        disruptions.append({
                            "id": d.get("id"),
                            "severity": d.get("severity", {}).get("name", "Information"),
                            "cause": d.get("cause", ""),
                            "message": full_text,
                            "updated_at": d.get("updated_at", ""),
                        })
                return disruptions
        except Exception as err:
            _LOGGER.debug("Erreur récupération disruptions: %s", err)
            return []

    def _parse_journey(self, journey: dict[str, Any], from_id: str, to_id: str) -> dict[str, Any] | None:
        """Parse raw journey into clean structured format."""
        try:
            dep_str = journey.get("departure_date_time")
            arr_str = journey.get("arrival_date_time")
            duration = int(journey.get("duration", 0))

            if not dep_str:
                return None

            dep_dt = datetime.strptime(dep_str, "%Y%m%dT%H%M%S").replace(tzinfo=TZ_PARIS)
            arr_dt = datetime.strptime(arr_str, "%Y%m%dT%H%M%S").replace(tzinfo=TZ_PARIS) if arr_str else dep_dt + timedelta(seconds=duration)
            
            now = datetime.now(TZ_PARIS)
            diff_seconds = (dep_dt - now).total_seconds()
            minutes_remaining = int(round(diff_seconds / 60))

            # Extraire les infos du transport public
            line = "H"
            direction = ""
            headsign = "TRAIN"
            physical_mode = "RER / Transilien"
            platform = None
            delay_minutes = 0
            base_dep_str = None

            for sec in journey.get("sections", []):
                if sec.get("type") == "public_transport":
                    disp = sec.get("display_informations", {})
                    line = disp.get("code") or disp.get("label") or "H"
                    direction = disp.get("direction") or ""
                    headsign = disp.get("headsign") or "TRAIN"
                    physical_mode = disp.get("physical_mode") or "RER / Transilien"

                    # Platform detection in stop_point or stop_date_times
                    st_point = sec.get("from", {}).get("stop_point", {})
                    if st_point.get("platform"):
                        platform = str(st_point.get("platform"))

                    stop_dates = sec.get("stop_date_times", [])
                    if stop_dates:
                        first_stop = stop_dates[0]
                        base_dep_str = first_stop.get("base_departure_date_time")
                        if not platform and first_stop.get("stop_point", {}).get("platform"):
                            platform = str(first_stop.get("stop_point", {}).get("platform"))

                    break

            # Calcul du retard si base_departure_date_time existe
            if base_dep_str and base_dep_str != dep_str:
                try:
                    base_dep_dt = datetime.strptime(base_dep_str, "%Y%m%dT%H%M%S").replace(tzinfo=TZ_PARIS)
                    retard_sec = (dep_dt - base_dep_dt).total_seconds()
                    if retard_sec > 60:
                        delay_minutes = int(round(retard_sec / 60))
                except Exception:
                    pass

            # Inférence intelligente de voie pour la gare d'Enghien si non fournie par l'API
            if not platform:
                # Enghien-les-Bains : Voie 2 vers Paris, Voie 1 vers Ermont/Pontoise
                if "87276022" in from_id:
                    if "paris" in direction.lower() or "87271007" in to_id:
                        platform = "2"
                    else:
                        platform = "1"
                elif "87271007" in from_id:
                    # Départ de Paris Nord (Surface Ligne H = Voies 30-36)
                    platform = "30-36"
                elif "87276055" in from_id:
                    # Départ d'Ermont - Eaubonne vers Paris/Enghien (Voies 3-4)
                    platform = "3-4"
                else:
                    platform = "-"

            # Statut textuel
            if delay_minutes > 0:
                status_label = f"Retard {delay_minutes} min"
                is_on_time = False
            elif minutes_remaining <= 1:
                status_label = "À quai"
                is_on_time = True
            elif minutes_remaining <= 3:
                status_label = "Départ imminent"
                is_on_time = True
            else:
                status_label = "À l'heure"
                is_on_time = True

            return {
                "departure_time": dep_dt.isoformat(),
                "arrival_time": arr_dt.isoformat(),
                "departure_time_str": dep_dt.strftime("%H:%M"),
                "arrival_time_str": arr_dt.strftime("%H:%M"),
                "departure_timestamp": dep_dt.timestamp(),
                "minutes_remaining": minutes_remaining,
                "duration_seconds": duration,
                "duration_minutes": int(round(duration / 60)),
                "line": line,
                "direction": direction,
                "headsign": headsign,
                "platform": platform,
                "physical_mode": physical_mode,
                "is_on_time": is_on_time,
                "delay_minutes": delay_minutes,
                "status_label": status_label,
            }
        except Exception as err:
            _LOGGER.error("Erreur parsing journey: %s", err)
            return None
