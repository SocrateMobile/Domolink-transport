"""Initialization file for DomoLink-Transport integration."""
from __future__ import annotations

import logging
import os
from typing import Any

from aiohttp import web
from homeassistant.components import frontend
from homeassistant.components.http import HomeAssistantView
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_ENABLE_PANEL,
    DOMAIN,
    FRONTEND_FILE_NAME,
    FRONTEND_URL_PATH,
    NAME,
    PANEL_ICON,
    PANEL_NAME,
    PANEL_TITLE,
    PANEL_URL_PATH,
    PLATFORMS,
    VERSION,
)
from .coordinator import DomolinkTransportCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the DomoLink-Transport component from configuration.yaml (not used)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up DomoLink-Transport from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    coordinator = DomolinkTransportCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "last_reload_options": {k: v for k, v in entry.options.items() if k != CONF_ENABLE_PANEL},
    }

    # 1. Register static frontend path
    frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
    if os.path.exists(frontend_dir):
        if hasattr(hass.http, "async_register_static_paths"):
            from homeassistant.components.http import StaticPathConfig
            await hass.http.async_register_static_paths([
                StaticPathConfig(FRONTEND_URL_PATH, frontend_dir, cache_headers=False)
            ])
        elif hasattr(hass.http, "register_static_path"):
            try:
                hass.http.register_static_path(FRONTEND_URL_PATH, frontend_dir, cache_headers=False)
            except Exception as err:
                _LOGGER.debug("Erreur register_static_path: %s", err)

    # 2. Register Sidebar Panel & Lovelace card resource
    enable_panel = entry.options.get(CONF_ENABLE_PANEL, entry.data.get(CONF_ENABLE_PANEL, True))
    if enable_panel:
        _async_register_panel(hass)
    else:
        _async_remove_panel(hass)

    await _async_register_lovelace_resource(hass)

    # 3. Register HTTP API View for Panel
    hass.http.register_view(DomolinkTransportDataApiView(coordinator))
    hass.http.register_view(DomolinkTransportRefreshApiView(coordinator))
    hass.http.register_view(DomolinkTransportStationSearchApiView(coordinator))

    # 4. Forward platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # 5. Register HA Services
    async def handle_refresh(call: ServiceCall) -> None:
        """Service to force refresh transport data."""
        await coordinator.async_request_refresh()

    hass.services.async_register(DOMAIN, "refresh", handle_refresh)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    _LOGGER.info("DomoLink-Transport v%s initialisé avec succès.", VERSION)
    return True


def _async_register_panel(hass: HomeAssistant) -> None:
    """Register the built-in sidebar panel."""
    panel_url = f"{FRONTEND_URL_PATH}/{FRONTEND_FILE_NAME}?v={VERSION}"
    try:
        if hasattr(frontend, "add_extra_js_url"):
            frontend.add_extra_js_url(hass, panel_url)

        frontend.async_register_built_in_panel(
            hass,
            component_name="custom",
            sidebar_title=PANEL_TITLE,
            sidebar_icon=PANEL_ICON,
            frontend_url_path=PANEL_URL_PATH,
            config={
                "_panel_custom": {
                    "name": PANEL_NAME,
                    "module_url": panel_url,
                }
            },
            require_admin=False,
            update=True,
        )
        _LOGGER.info("DomoLink-Transport: Panneau latéral enregistré avec succès.")
    except Exception as err:
        _LOGGER.debug("Panneau latéral DomoLink-Transport déjà enregistré ou erreur: %s", err)


def _async_remove_panel(hass: HomeAssistant) -> None:
    """Remove sidebar panel."""
    try:
        frontend.async_remove_panel(hass, PANEL_URL_PATH)
    except Exception as err:
        _LOGGER.debug("Erreur retrait panneau latéral: %s", err)


async def _async_register_lovelace_resource(hass: HomeAssistant) -> None:
    """Auto-register DomoLink-Transport Lovelace card resource in storage mode."""
    card_url = f"{FRONTEND_URL_PATH}/{FRONTEND_FILE_NAME}?v={VERSION}"
    base_url = f"{FRONTEND_URL_PATH}/{FRONTEND_FILE_NAME}"

    async def _check_and_register(_now: Any = None) -> None:
        lovelace = hass.data.get("lovelace")
        if lovelace and getattr(lovelace.resources, "loaded", False):
            try:
                existing_resources = [
                    res for res in lovelace.resources.async_items()
                    if res.get("url", "").split("?")[0] == base_url
                ]

                if existing_resources:
                    for res in existing_resources:
                        if res.get("url") != card_url:
                            _LOGGER.info("Mise à jour de la ressource Lovelace DomoLink vers %s", card_url)
                            await lovelace.resources.async_update_item(
                                res["id"],
                                {
                                    "res_type": "module",
                                    "url": card_url,
                                },
                            )
                else:
                    _LOGGER.info("Enregistrement automatique de la ressource Lovelace DomoLink : %s", card_url)
                    await lovelace.resources.async_create_item(
                        {
                            "res_type": "module",
                            "url": card_url,
                        }
                    )
            except Exception as err:
                _LOGGER.debug("Erreur enregistrement ressource Lovelace: %s", err)
        else:
            from homeassistant.helpers.event import async_call_later
            async_call_later(hass, 2, _check_and_register)

    lovelace = hass.data.get("lovelace")
    mode = getattr(lovelace, "mode", None) or getattr(lovelace, "resource_mode", "yaml") if lovelace else "storage"
    if mode == "storage" or lovelace is None:
        await _check_and_register()


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload integration when options change."""
    entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    last_reload_options = entry_data.get("last_reload_options")
    current_options = {k: v for k, v in entry.options.items() if k != CONF_ENABLE_PANEL}

    if last_reload_options is not None and current_options == last_reload_options:
        # Seul le panneau latéral (CONF_ENABLE_PANEL) a changé : pas besoin de recharger toutes les plateformes
        enable_panel = entry.options.get(CONF_ENABLE_PANEL, entry.data.get(CONF_ENABLE_PANEL, True))
        if enable_panel:
            _async_register_panel(hass)
        else:
            _async_remove_panel(hass)
        return

    entry_data["last_reload_options"] = current_options
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload DomoLink-Transport entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok


# =========================================================================
# API VIEWS POUR LE PANNEAU FRONTEND
# =========================================================================

class DomolinkTransportDataApiView(HomeAssistantView):
    """View to get current transport data."""

    url = "/api/domolink_transport/data"
    name = "api:domolink_transport:data"
    requires_auth = True

    def __init__(self, coordinator: DomolinkTransportCoordinator) -> None:
        self.coordinator = coordinator

    async def get(self, request: web.Request) -> web.Response:
        return self.json({
            "version": VERSION,
            "data": self.coordinator.data,
        })


class DomolinkTransportRefreshApiView(HomeAssistantView):
    """View to trigger refresh from panel."""

    url = "/api/domolink_transport/refresh"
    name = "api:domolink_transport:refresh"
    requires_auth = True

    def __init__(self, coordinator: DomolinkTransportCoordinator) -> None:
        self.coordinator = coordinator

    async def post(self, request: web.Request) -> web.Response:
        await self.coordinator.async_request_refresh()
        return self.json({"status": "ok", "message": "Actualisation en cours..."})


class DomolinkTransportStationSearchApiView(HomeAssistantView):
    """View to search stations from panel."""

    url = "/api/domolink_transport/search_station"
    name = "api:domolink_transport:search_station"
    requires_auth = True

    def __init__(self, coordinator: DomolinkTransportCoordinator) -> None:
        self.coordinator = coordinator

    async def get(self, request: web.Request) -> web.Response:
        q = request.query.get("q", "").strip()
        results = await self.coordinator.api.async_search_station(q)
        return self.json({"results": results})
