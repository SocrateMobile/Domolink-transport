"""Sensor platform for DomoLink-Transport with native and legacy entities."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
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
    """Set up the sensor platform."""
    coordinator: DomolinkTransportCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities: list[SensorEntity] = []

    # 1. Capteurs modernes DomoLink pour le trajet A -> B (3 prochains départs)
    for idx in range(3):
        entities.append(DomolinkJourneySensor(coordinator, entry, "a_to_b", idx))

    # 2. Capteurs modernes DomoLink pour le trajet A -> C (3 prochains départs)
    for idx in range(3):
        entities.append(DomolinkJourneySensor(coordinator, entry, "a_to_c", idx))

    # 3. Derniers retours de nuit (B -> A et C -> A)
    entities.append(DomolinkLastReturnSensor(coordinator, entry, "b_to_a"))
    entities.append(DomolinkLastReturnSensor(coordinator, entry, "c_to_a"))

    # 4. Capteurs Rétrocompatibilité Totale pour openHASP (WT32-SC01 et Sunton 7")
    if coordinator.create_legacy_entities:
        # sensor.next_train_minutes_1 .. 4
        for idx in range(4):
            entities.append(LegacyNextTrainMinutesSensor(coordinator, entry, idx))

        # sensor.next_trains_one et next_trains_two (synthèses)
        entities.append(LegacyNextTrainsSummarySensor(coordinator, entry, 1))
        entities.append(LegacyNextTrainsSummarySensor(coordinator, entry, 2))

        # sensor.train_traveler_eng_par_next_journey_1 .. 5
        for idx in range(5):
            entities.append(LegacyJourneyMainSensor(coordinator, entry, idx))
            entities.append(LegacyJourneyDepartureSensor(coordinator, entry, idx))
            entities.append(LegacyJourneyArrivalSensor(coordinator, entry, idx))
            entities.append(LegacyJourneyDurationSensor(coordinator, entry, idx))
            entities.append(LegacyJourneyDelaySensor(coordinator, entry, idx))

        # sensor.train_traveler_eng_par_last_journey_1
        entities.append(LegacyLastJourneySensor(coordinator, entry))

        # sensor.train_traveler_par_eng_next_journey_1 et duration_1 (retour Paris -> Enghien)
        entities.append(LegacyReturnJourneySensor(coordinator, entry, 0))
        entities.append(LegacyReturnJourneyDurationSensor(coordinator, entry, 0))

    async_add_entities(entities)


class DomolinkTransportBaseSensor(CoordinatorEntity[DomolinkTransportCoordinator], SensorEntity):
    """Base sensor for DomoLink-Transport."""

    def __init__(self, coordinator: DomolinkTransportCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self.entry = entry

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self.entry.entry_id}_station")},
            name=f"{NAME} ({self.coordinator.station_a_name})",
            manufacturer="Socrate Mobile",
            model="DomoLink Suite",
            sw_version=VERSION,
        )


# =========================================================================
# CAPTEURS MODERNES DOMOLINK
# =========================================================================

class DomolinkJourneySensor(DomolinkTransportBaseSensor):
    """Sensor for a next journey (A->B or A->C)."""

    def __init__(self, coordinator: DomolinkTransportCoordinator, entry: ConfigEntry, route_key: str, index: int) -> None:
        super().__init__(coordinator, entry)
        self._route_key = route_key
        self._index = index
        dest_name = coordinator.station_b_name if route_key == "a_to_b" else coordinator.station_c_name
        self._attr_name = f"DomoLink Train {coordinator.station_a_name} - {dest_name} ({index + 1})"
        self._attr_unique_id = f"domolink_transport_{route_key}_{index + 1}_{entry.entry_id}"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self) -> str | None:
        journeys = self.coordinator.data.get(self._route_key, [])
        if len(journeys) > self._index:
            return journeys[self._index].get("departure_time")
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        journeys = self.coordinator.data.get(self._route_key, [])
        if len(journeys) > self._index:
            j = journeys[self._index]
            return {
                "minutes_remaining": j.get("minutes_remaining"),
                "platform": j.get("platform"),
                "voie": j.get("platform"),
                "line": j.get("line"),
                "direction": j.get("direction"),
                "headsign": j.get("headsign"),
                "mission": j.get("headsign"),
                "duration_minutes": j.get("duration_minutes"),
                "arrival_time": j.get("arrival_time"),
                "is_on_time": j.get("is_on_time"),
                "delay_minutes": j.get("delay_minutes"),
                "status_label": j.get("status_label"),
                "physical_mode": j.get("physical_mode"),
            }
        return {}


class DomolinkLastReturnSensor(DomolinkTransportBaseSensor):
    """Sensor for the last return train of the night."""

    def __init__(self, coordinator: DomolinkTransportCoordinator, entry: ConfigEntry, route_key: str) -> None:
        super().__init__(coordinator, entry)
        self._route_key = route_key
        orig_name = coordinator.station_b_name if route_key == "b_to_a" else coordinator.station_c_name
        self._attr_name = f"DomoLink Dernier Retour {orig_name} - {coordinator.station_a_name}"
        self._attr_unique_id = f"domolink_transport_last_return_{route_key}_{entry.entry_id}"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self) -> str | None:
        key = "last_return_b_to_a" if self._route_key == "b_to_a" else "last_return_c_to_a"
        j = self.coordinator.data.get(key)
        return j.get("departure_time") if j else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        key = "last_return_b_to_a" if self._route_key == "b_to_a" else "last_return_c_to_a"
        j = self.coordinator.data.get(key)
        if not j:
            return {"status": "Aucun train nocturne trouvé"}
        return {
            "minutes_remaining": j.get("minutes_remaining"),
            "platform": j.get("platform"),
            "voie": j.get("platform"),
            "line": j.get("line"),
            "direction": j.get("direction"),
            "headsign": j.get("headsign"),
            "mission": j.get("headsign"),
            "duration_minutes": j.get("duration_minutes"),
            "arrival_time": j.get("arrival_time"),
            "physical_mode": j.get("physical_mode"),
            "status_label": j.get("status_label"),
        }


# =========================================================================
# CAPTEURS DE RÉTROCOMPATIBILITÉ OPENHASP
# =========================================================================

class LegacyNextTrainMinutesSensor(DomolinkTransportBaseSensor):
    """Drop-in replacement for sensor.next_train_minutes_X."""

    def __init__(self, coordinator: DomolinkTransportCoordinator, entry: ConfigEntry, index: int) -> None:
        super().__init__(coordinator, entry)
        self._index = index
        self._attr_name = f"Minutes jusqu'au prochain train ({index + 1}{'er' if index == 0 else 'ème'})"
        self._attr_unique_id = f"domolink_legacy_next_train_minutes_{index + 1}"
        self.entity_id = f"sensor.next_train_minutes_{index + 1}"
        self._attr_native_unit_of_measurement = "min"

    @property
    def native_value(self) -> int:
        journeys = self.coordinator.data.get("a_to_b", [])
        if len(journeys) > self._index:
            mins = journeys[self._index].get("minutes_remaining", 0)
            return max(mins, 0)
        return 0


class LegacyNextTrainsSummarySensor(DomolinkTransportBaseSensor):
    """Drop-in replacement for sensor.next_trains_one and sensor.next_trains_two."""

    def __init__(self, coordinator: DomolinkTransportCoordinator, entry: ConfigEntry, mode: int) -> None:
        super().__init__(coordinator, entry)
        self._mode = mode
        if mode == 1:
            self._attr_name = "Le Prochain train"
            self._attr_unique_id = "domolink_legacy_next_trains_one"
            self.entity_id = "sensor.next_trains_one"
        else:
            self._attr_name = "2 Prochains trains"
            self._attr_unique_id = "domolink_legacy_next_trains_two"
            self.entity_id = "sensor.next_trains_two"

    @property
    def native_value(self) -> str:
        journeys = self.coordinator.data.get("a_to_b", [])
        if self._mode == 1:
            if not journeys:
                return "Pas de train"
            m = journeys[0].get("minutes_remaining", 0)
            if m >= 60:
                return f"{m // 60}h{m % 60:02d}"
            return f"{max(m, 0)} min"
        else:
            # 2 prochains trains suivants
            if len(journeys) < 2:
                return "-"
            m2 = max(journeys[1].get("minutes_remaining", 0), 0)
            m3 = max(journeys[2].get("minutes_remaining", 0), 0) if len(journeys) > 2 else None
            txt = f"{m2} min"
            if m3 is not None:
                txt += f" / {m3} min"
            return txt


class LegacyJourneyMainSensor(DomolinkTransportBaseSensor):
    """Drop-in replacement for sensor.train_traveler_eng_par_next_journey_X."""

    def __init__(self, coordinator: DomolinkTransportCoordinator, entry: ConfigEntry, index: int) -> None:
        super().__init__(coordinator, entry)
        self._index = index
        self._attr_name = f"{coordinator.station_a_name} - {coordinator.station_b_name} Journey {index + 1}"
        self._attr_unique_id = f"domolink_legacy_train_traveler_eng_par_next_journey_{index + 1}"
        self.entity_id = f"sensor.train_traveler_eng_par_next_journey_{index + 1}"

    @property
    def native_value(self) -> str | None:
        journeys = self.coordinator.data.get("a_to_b", [])
        if len(journeys) > self._index:
            return journeys[self._index].get("departure_time")
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        journeys = self.coordinator.data.get("a_to_b", [])
        if len(journeys) > self._index:
            j = journeys[self._index]
            return {
                "line": j.get("line"),
                "direction": j.get("direction"),
                "departure_time": j.get("departure_time"),
                "arrival_time": j.get("arrival_time"),
                "duration": j.get("duration_seconds"),
                "physical_mode": j.get("physical_mode"),
                "departure": self.coordinator.station_a_name,
                "arrival": self.coordinator.station_b_name,
                "platform": j.get("platform"),
                "voie": j.get("platform"),
                "headsign": j.get("headsign"),
                "delay": j.get("delay_minutes"),
            }
        return {}


class LegacyJourneyDepartureSensor(DomolinkTransportBaseSensor):
    """Drop-in replacement for sensor.train_traveler_eng_par_next_journey_departure_X."""

    def __init__(self, coordinator: DomolinkTransportCoordinator, entry: ConfigEntry, index: int) -> None:
        super().__init__(coordinator, entry)
        self._index = index
        self._attr_name = f"{coordinator.station_a_name} - {coordinator.station_b_name} Departure {index + 1}"
        self._attr_unique_id = f"domolink_legacy_train_traveler_eng_par_next_journey_departure_{index + 1}"
        self.entity_id = f"sensor.train_traveler_eng_par_next_journey_departure_{index + 1}"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self) -> str | None:
        journeys = self.coordinator.data.get("a_to_b", [])
        if len(journeys) > self._index:
            return journeys[self._index].get("departure_time")
        return None


class LegacyJourneyArrivalSensor(DomolinkTransportBaseSensor):
    """Drop-in replacement for sensor.train_traveler_eng_par_next_journey_arrival_X."""

    def __init__(self, coordinator: DomolinkTransportCoordinator, entry: ConfigEntry, index: int) -> None:
        super().__init__(coordinator, entry)
        self._index = index
        self._attr_name = f"{coordinator.station_a_name} - {coordinator.station_b_name} Arrival {index + 1}"
        self._attr_unique_id = f"domolink_legacy_train_traveler_eng_par_next_journey_arrival_{index + 1}"
        self.entity_id = f"sensor.train_traveler_eng_par_next_journey_arrival_{index + 1}"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self) -> str | None:
        journeys = self.coordinator.data.get("a_to_b", [])
        if len(journeys) > self._index:
            return journeys[self._index].get("arrival_time")
        return None


class LegacyJourneyDurationSensor(DomolinkTransportBaseSensor):
    """Drop-in replacement for sensor.train_traveler_eng_par_next_journey_duration_X."""

    def __init__(self, coordinator: DomolinkTransportCoordinator, entry: ConfigEntry, index: int) -> None:
        super().__init__(coordinator, entry)
        self._index = index
        self._attr_name = f"{coordinator.station_a_name} - {coordinator.station_b_name} Duration {index + 1}"
        self._attr_unique_id = f"domolink_legacy_train_traveler_eng_par_next_journey_duration_{index + 1}"
        self.entity_id = f"sensor.train_traveler_eng_par_next_journey_duration_{index + 1}"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = "s"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int:
        journeys = self.coordinator.data.get("a_to_b", [])
        if len(journeys) > self._index:
            return journeys[self._index].get("duration_seconds", 0)
        return 0


class LegacyJourneyDelaySensor(DomolinkTransportBaseSensor):
    """Drop-in replacement for sensor.train_traveler_eng_par_next_journey_disruption_delay_X."""

    def __init__(self, coordinator: DomolinkTransportCoordinator, entry: ConfigEntry, index: int) -> None:
        super().__init__(coordinator, entry)
        self._index = index
        self._attr_name = f"{coordinator.station_a_name} - {coordinator.station_b_name} Delay {index + 1}"
        self._attr_unique_id = f"domolink_legacy_train_traveler_eng_par_next_journey_disruption_delay_{index + 1}"
        self.entity_id = f"sensor.train_traveler_eng_par_next_journey_disruption_delay_{index + 1}"
        self._attr_native_unit_of_measurement = "min"

    @property
    def native_value(self) -> int:
        journeys = self.coordinator.data.get("a_to_b", [])
        if len(journeys) > self._index:
            return journeys[self._index].get("delay_minutes", 0)
        return 0


class LegacyLastJourneySensor(DomolinkTransportBaseSensor):
    """Drop-in replacement for sensor.train_traveler_eng_par_last_journey_1."""

    def __init__(self, coordinator: DomolinkTransportCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_name = "Dernier Train Retour Enghien"
        self._attr_unique_id = "domolink_legacy_train_traveler_eng_par_last_journey_1"
        self.entity_id = "sensor.train_traveler_eng_par_last_journey_1"

    @property
    def native_value(self) -> str | None:
        j = self.coordinator.data.get("last_return_b_to_a")
        return j.get("departure_time") if j else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        j = self.coordinator.data.get("last_return_b_to_a")
        if not j:
            return {}
        return {
            "line": j.get("line"),
            "direction": j.get("direction"),
            "departure_time": j.get("departure_time"),
            "duration": j.get("duration_seconds"),
            "physical_mode": j.get("physical_mode"),
            "platform": j.get("platform"),
            "voie": j.get("platform"),
        }


class LegacyReturnJourneySensor(DomolinkTransportBaseSensor):
    """Drop-in replacement for sensor.train_traveler_par_eng_next_journey_1."""

    def __init__(self, coordinator: DomolinkTransportCoordinator, entry: ConfigEntry, index: int) -> None:
        super().__init__(coordinator, entry)
        self._index = index
        self._attr_name = "Train Retour Paris Nord vers Enghien"
        self._attr_unique_id = "domolink_legacy_train_traveler_par_eng_next_journey_1"
        self.entity_id = "sensor.train_traveler_par_eng_next_journey_1"

    @property
    def native_value(self) -> str | None:
        returns = self.coordinator.data.get("b_to_a", [])
        if len(returns) > self._index:
            return returns[self._index].get("departure_time")
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        returns = self.coordinator.data.get("b_to_a", [])
        if len(returns) > self._index:
            j = returns[self._index]
            return {
                "line": j.get("line"),
                "direction": j.get("direction"),
                "departure_time": j.get("departure_time"),
                "arrival_time": j.get("arrival_time"),
                "duration": j.get("duration_seconds"),
                "physical_mode": j.get("physical_mode"),
                "platform": j.get("platform"),
                "voie": j.get("platform"),
                "delay": j.get("delay_minutes"),
            }
        return {}


class LegacyReturnJourneyDurationSensor(DomolinkTransportBaseSensor):
    """Drop-in replacement for sensor.train_traveler_par_eng_next_journey_duration_1."""

    def __init__(self, coordinator: DomolinkTransportCoordinator, entry: ConfigEntry, index: int) -> None:
        super().__init__(coordinator, entry)
        self._index = index
        self._attr_name = "Durée Retour Paris Nord vers Enghien"
        self._attr_unique_id = "domolink_legacy_train_traveler_par_eng_next_journey_duration_1"
        self.entity_id = "sensor.train_traveler_par_eng_next_journey_duration_1"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = "s"

    @property
    def native_value(self) -> int:
        returns = self.coordinator.data.get("b_to_a", [])
        if len(returns) > self._index:
            return returns[self._index].get("duration_seconds", 0)
        return 0
