"""Button platform for DomoLink-Transport (Génération du code carte Lovelace)."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_STATION_A,
    CONF_STATION_B,
    CONF_STATION_C,
    DEFAULT_STATION_A_NAME,
    DEFAULT_STATION_B_NAME,
    DEFAULT_STATION_C_NAME,
    DOMAIN,
    NAME,
    VERSION,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the button platform for DomoLink-Transport."""
    async_add_entities([DomolinkTransportCopyCardButton(hass, entry)], True)


class DomolinkTransportCopyCardButton(ButtonEntity):
    """Button entity that creates a notification containing the ready-to-use Lovelace card YAML code."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:card-text-outline"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._attr_name = "Copie Code Carte Lovelace"
        self._attr_unique_id = f"domolink_transport_copy_card_button_{entry.entry_id}"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self.entry.entry_id}_system")},
            name=f"{NAME} Système",
            manufacturer="Socrate Mobile",
            model="DomoLink Suite",
            sw_version=VERSION,
        )

    async def async_press(self) -> None:
        """Handle the button press by creating a notification with the card YAML."""
        data = {**self.entry.data, **self.entry.options}
        st_a = data.get(CONF_STATION_A, DEFAULT_STATION_A_NAME)
        st_b = data.get(CONF_STATION_B, DEFAULT_STATION_B_NAME)
        st_c = data.get(CONF_STATION_C, DEFAULT_STATION_C_NAME)

        card_yaml = (
            "type: custom:domolink-transport-card\n"
            "style: modern\n"
            f"station_a: {st_a}\n"
            f"station_b: {st_b}\n"
            f"station_c: {st_c}"
        )

        message = (
            f"### 📋 Code de votre Carte Lovelace DomoLink-Transport\n\n"
            f"Copiez le bloc ci-dessous dans votre tableau de bord Lovelace (bouton **Ajouter une carte** ➔ **Manuel**) :\n\n"
            f"```yaml\n{card_yaml}\n```\n\n"
            f"*💡 Conseil : Vous pouvez remplacer `style: modern` par `style: mechanical` pour afficher l'effet girouette / palettes mécaniques vintage Solari.*"
        )

        await self.hass.services.async_call(
            "persistent_notification",
            "create",
            {
                "notification_id": "domolink_transport_card_code",
                "title": "📋 DomoLink Transport - Carte Lovelace",
                "message": message,
            },
        )
        _LOGGER.info("Code carte Lovelace généré dans les notifications Home Assistant.")
