"""Binary sensor platform for DomoLink-Transport (traffic status and delays)."""
from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NAME, VERSION
from .coordinator import DomolinkTransportCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensor platform."""
    coordinator: DomolinkTransportCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    async_add_entities([
        DomolinkTrafficStatusBinarySensor(coordinator, entry),
        DomolinkDelaysBinarySensor(coordinator, entry),
    ])


class DomolinkTrafficStatusBinarySensor(CoordinatorEntity[DomolinkTransportCoordinator], BinarySensorEntity):
    """Binary sensor for line traffic status."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: DomolinkTransportCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self.entry = entry
        self._attr_name = f"DomoLink Perturbation Trafic ({coordinator.station_a_name})"
        self._attr_unique_id = f"domolink_transport_disruptions_{entry.entry_id}"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self.entry.entry_id}_station")},
            name=f"{NAME} ({self.coordinator.station_a_name})",
            manufacturer="Socrate Mobile",
            model="DomoLink Suite",
            sw_version=VERSION,
        )

    @property
    def is_on(self) -> bool:
        """Return True if there is a disruption (problem active)."""
        disruptions = self.coordinator.data.get("disruptions", [])
        return len(disruptions) > 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        disruptions = self.coordinator.data.get("disruptions", [])
        messages = [d.get("message") for d in disruptions if d.get("message")]
        return {
            "disruptions_count": len(disruptions),
            "disruptions": disruptions,
            "banner_text": " | ".join(messages) if messages else "Trafic normal sur la ligne",
        }


class DomolinkDelaysBinarySensor(CoordinatorEntity[DomolinkTransportCoordinator], BinarySensorEntity):
    """Binary sensor indicating if any upcoming train is delayed."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: DomolinkTransportCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self.entry = entry
        self._attr_name = f"DomoLink Retards Détectés ({coordinator.station_a_name})"
        self._attr_unique_id = f"domolink_transport_delays_{entry.entry_id}"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self.entry.entry_id}_station")},
            name=f"{NAME} ({self.coordinator.station_a_name})",
            manufacturer="Socrate Mobile",
            model="DomoLink Suite",
            sw_version=VERSION,
        )

    @property
    def is_on(self) -> bool:
        """Return True if any of the next trains has delay > 0."""
        for route in ("a_to_b", "a_to_c"):
            for j in self.coordinator.data.get(route, []):
                if j.get("delay_minutes", 0) > 0:
                    return True
        return False
