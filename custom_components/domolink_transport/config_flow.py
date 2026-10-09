"""Config flow for DomoLink-Transport integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv

from .api import DomolinkTransportApiClient
from .const import (
    CONF_API_KEY,
    CONF_CREATE_LEGACY_ENTITIES,
    CONF_ENABLE_PANEL,
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
    NAME,
)

_LOGGER = logging.getLogger(__name__)


async def _resolve_station(api: DomolinkTransportApiClient, name_or_id: str, default_name: str, default_id: str) -> tuple[str, str]:
    """Resolve station input to (name, stop_area_id)."""
    clean = (name_or_id or "").strip()
    if not clean:
        return default_name, default_id

    if clean.startswith("stop_area:"):
        return clean, clean

    # Search via API
    results = await api.async_search_station(clean)
    if results:
        return results[0]["name"], results[0]["id"]

    return clean, default_id


class DomolinkTransportConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for DomoLink-Transport."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            prim_key = user_input.get(CONF_PRIM_API_KEY, "").strip() or None

            session = async_get_clientsession(self.hass)
            api = DomolinkTransportApiClient(session, api_key, prim_key)

            # Test API auth
            test_res = await api.async_search_station("Paris")
            if not test_res:
                # Tester directement un trajet
                test_j = await api.async_get_next_journeys(DEFAULT_STATION_A_ID, DEFAULT_STATION_B_ID, count=1)
                if not test_j:
                    errors["base"] = "invalid_auth"

            if not errors:
                # Résolution des 3 gares
                st_a_name, st_a_id = await _resolve_station(
                    api, user_input.get(CONF_STATION_A, DEFAULT_STATION_A_NAME),
                    DEFAULT_STATION_A_NAME, DEFAULT_STATION_A_ID
                )
                st_b_name, st_b_id = await _resolve_station(
                    api, user_input.get(CONF_STATION_B, DEFAULT_STATION_B_NAME),
                    DEFAULT_STATION_B_NAME, DEFAULT_STATION_B_ID
                )
                st_c_name, st_c_id = await _resolve_station(
                    api, user_input.get(CONF_STATION_C, DEFAULT_STATION_C_NAME),
                    DEFAULT_STATION_C_NAME, DEFAULT_STATION_C_ID
                )

                data = {
                    CONF_API_KEY: api_key,
                    CONF_PRIM_API_KEY: prim_key,
                    CONF_STATION_A: st_a_name,
                    CONF_STATION_A_ID: st_a_id,
                    CONF_STATION_B: st_b_name,
                    CONF_STATION_B_ID: st_b_id,
                    CONF_STATION_C: st_c_name,
                    CONF_STATION_C_ID: st_c_id,
                    CONF_SCAN_INTERVAL: user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                    CONF_CREATE_LEGACY_ENTITIES: user_input.get(CONF_CREATE_LEGACY_ENTITIES, True),
                    CONF_ENABLE_PANEL: user_input.get(CONF_ENABLE_PANEL, True),
                }

                await self.async_set_unique_id(f"{DOMAIN}_{st_a_id}")
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"DomoLink Transport ({st_a_name})",
                    data=data,
                )

        schema = vol.Schema({
            vol.Required(CONF_API_KEY): cv.string,
            vol.Optional(CONF_PRIM_API_KEY, default=""): cv.string,
            vol.Required(CONF_STATION_A, default=DEFAULT_STATION_A_NAME): cv.string,
            vol.Required(CONF_STATION_B, default=DEFAULT_STATION_B_NAME): cv.string,
            vol.Required(CONF_STATION_C, default=DEFAULT_STATION_C_NAME): cv.string,
            vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): cv.positive_int,
            vol.Optional(CONF_CREATE_LEGACY_ENTITIES, default=True): cv.boolean,
            vol.Optional(CONF_ENABLE_PANEL, default=True): cv.boolean,
        })

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        return DomolinkTransportOptionsFlow(config_entry)


class DomolinkTransportOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for DomoLink-Transport."""

    def __init__(self, config_entry: config_entries.ConfigEntry | None = None) -> None:
        """Initialize options flow without conflicting with Home Assistant base property."""
        self._config_entry = config_entry

    @property
    def config_entry(self) -> config_entries.ConfigEntry:
        """Return config entry, prioritizing HA base property with fallback."""
        try:
            entry = super().config_entry
            if entry is not None:
                return entry
        except (AttributeError, KeyError, Exception):
            pass
        return self._config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            api_key = user_input.get(CONF_API_KEY, self.config_entry.data.get(CONF_API_KEY, "")).strip()
            prim_key = user_input.get(CONF_PRIM_API_KEY, "").strip() or None

            session = async_get_clientsession(self.hass)
            api = DomolinkTransportApiClient(session, api_key, prim_key)

            st_a_name, st_a_id = await _resolve_station(
                api, user_input.get(CONF_STATION_A, DEFAULT_STATION_A_NAME),
                DEFAULT_STATION_A_NAME, DEFAULT_STATION_A_ID
            )
            st_b_name, st_b_id = await _resolve_station(
                api, user_input.get(CONF_STATION_B, DEFAULT_STATION_B_NAME),
                DEFAULT_STATION_B_NAME, DEFAULT_STATION_B_ID
            )
            st_c_name, st_c_id = await _resolve_station(
                api, user_input.get(CONF_STATION_C, DEFAULT_STATION_C_NAME),
                DEFAULT_STATION_C_NAME, DEFAULT_STATION_C_ID
            )

            options = {
                CONF_API_KEY: api_key,
                CONF_PRIM_API_KEY: prim_key,
                CONF_STATION_A: st_a_name,
                CONF_STATION_A_ID: st_a_id,
                CONF_STATION_B: st_b_name,
                CONF_STATION_B_ID: st_b_id,
                CONF_STATION_C: st_c_name,
                CONF_STATION_C_ID: st_c_id,
                CONF_SCAN_INTERVAL: user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                CONF_CREATE_LEGACY_ENTITIES: user_input.get(CONF_CREATE_LEGACY_ENTITIES, True),
                CONF_ENABLE_PANEL: user_input.get(CONF_ENABLE_PANEL, True),
            }
            return self.async_create_entry(title="", data=options)

        cur_data = {**self.config_entry.data, **self.config_entry.options}

        schema = vol.Schema({
            vol.Required(CONF_API_KEY, default=cur_data.get(CONF_API_KEY, "")): cv.string,
            vol.Optional(CONF_PRIM_API_KEY, default=cur_data.get(CONF_PRIM_API_KEY, "") or ""): cv.string,
            vol.Required(CONF_STATION_A, default=cur_data.get(CONF_STATION_A, DEFAULT_STATION_A_NAME)): cv.string,
            vol.Required(CONF_STATION_B, default=cur_data.get(CONF_STATION_B, DEFAULT_STATION_B_NAME)): cv.string,
            vol.Required(CONF_STATION_C, default=cur_data.get(CONF_STATION_C, DEFAULT_STATION_C_NAME)): cv.string,
            vol.Optional(CONF_SCAN_INTERVAL, default=cur_data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)): cv.positive_int,
            vol.Optional(CONF_CREATE_LEGACY_ENTITIES, default=cur_data.get(CONF_CREATE_LEGACY_ENTITIES, True)): cv.boolean,
            vol.Optional(CONF_ENABLE_PANEL, default=cur_data.get(CONF_ENABLE_PANEL, True)): cv.boolean,
        })

        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
