"""Sensor platform for Platformatics device environmental readings."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SENSOR_DEFINITIONS
from .coordinator import PlatformaticsCoordinator

_DEVICE_CLASS_MAP: dict[str | None, SensorDeviceClass | None] = {
    "temperature": SensorDeviceClass.TEMPERATURE,
    "humidity": SensorDeviceClass.HUMIDITY,
    "pm25": SensorDeviceClass.PM25,
    "pm10": SensorDeviceClass.PM10,
    "volatile_organic_compounds_parts": SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS_PARTS,
    None: None,
}


def _build_sensor_entities(
    coordinator: PlatformaticsCoordinator,
) -> list[PlatformaticsSensor]:
    entities = []
    for device in coordinator.data["devices"].values():
        for key, label, unit, device_class_str, state_class_str in SENSOR_DEFINITIONS:
            value = device.get(key)
            if value is None:
                continue
            entities.append(
                PlatformaticsSensor(
                    coordinator=coordinator,
                    device_id=device["id"],
                    device_name=device.get("name", f"Device {device['id']}"),
                    sensor_key=key,
                    sensor_label=label,
                    unit=unit,
                    device_class=_DEVICE_CLASS_MAP.get(device_class_str),
                )
            )
    return entities


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: PlatformaticsCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(_build_sensor_entities(coordinator))


class PlatformaticsSensor(CoordinatorEntity[PlatformaticsCoordinator], SensorEntity):
    """An environmental sensor reading from a Platformatics device."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: PlatformaticsCoordinator,
        device_id: int,
        device_name: str,
        sensor_key: str,
        sensor_label: str,
        unit: str | None,
        device_class: SensorDeviceClass | None,
    ) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._sensor_key = sensor_key
        self._attr_unique_id = f"platformatics_device_{device_id}_{sensor_key}"
        self._attr_name = f"{device_name} {sensor_label}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class

    @property
    def name(self) -> str:
        return self._attr_name

    @property
    def unique_id(self) -> str:
        return self._attr_unique_id

    @property
    def state(self) -> float | int | None:
        device = self.coordinator.data["devices"].get(self._device_id, {})
        return device.get(self._sensor_key)

    @property
    def unit_of_measurement(self) -> str | None:
        return self._attr_native_unit_of_measurement
