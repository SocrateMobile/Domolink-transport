"""Switch platform for DomoLink-Transport (Panneau latéral on/off)."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_ENABLE_PANEL, DOMAIN, NAME, VERSION

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the DomoLink-Transport switch platform."""
    async_add_entities([DomolinkTransportPanelSwitch(hass, entry)], True)


class DomolinkTransportPanelSwitch(SwitchEntity):
    """Switch to dynamically show/hide DomoLink-Transport sidebar panel."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:dock-left"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._attr_name = "Affichage Panneau Latéral"
        self._attr_unique_id = f"domolink_transport_panel_switch_{entry.entry_id}"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self.entry.entry_id}_system")},
            name=f"{NAME} Système",
            manufacturer="Socrate Mobile",
            model="DomoLink Suite",
            sw_version=VERSION,
        )

    @property
    def is_on(self) -> bool:
        """Return True if the sidebar panel is enabled."""
        return self.entry.options.get(
            CONF_ENABLE_PANEL, self.entry.data.get(CONF_ENABLE_PANEL, True)
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable sidebar panel."""
        await self._async_set_state(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable sidebar panel."""
        await self._async_set_state(False)

    async def _async_set_state(self, enabled: bool) -> None:
        """Update entry options and refresh panel registration."""
        from . import _async_register_panel, _async_remove_panel

        new_options = dict(self.entry.options)
        new_options[CONF_ENABLE_PANEL] = enabled
        self.hass.config_entries.async_update_entry(self.entry, options=new_options)

        if enabled:
            _async_register_panel(self.hass)
        else:
            _async_remove_panel(self.hass)

        self.async_write_ha_state()
