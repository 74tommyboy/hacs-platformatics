"""Tests for PlatformaticsSensor."""
import pytest
from unittest.mock import MagicMock
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from custom_components.platformatics.sensor import (
    PlatformaticsSensor,
    _build_sensor_entities,
)
from custom_components.platformatics.coordinator import PlatformaticsCoordinator


@pytest.fixture
def coordinator(mock_api):
    coord = MagicMock(spec=PlatformaticsCoordinator)
    coord.api = mock_api
    coord.data = {
        "zones": {},
        "devices": {
            101: {
                "id": 101,
                "name": "Office Sensor",
                "zoneId": 1,
                "temperature": 22.5,
                "humidity": 45.0,
                "pm2_5": 8.2,
                "pm10": 12.1,
                "vocIndex": 100,
                "daylightLevel": 60.0,
            },
            102: {
                "id": 102,
                "name": "Lobby Light",
                "zoneId": 2,
                "temperature": None,
                "humidity": None,
                "pm2_5": None,
                "pm10": None,
                "vocIndex": None,
                "daylightLevel": None,
            },
        },
    }
    return coord


def test_build_sensor_entities_only_for_devices_with_readings(coordinator):
    entities = _build_sensor_entities(coordinator)
    names = [e.name for e in entities]
    assert any("Office Sensor" in n for n in names)
    assert not any("Lobby Light" in n for n in names)


def test_sensor_temperature_state(coordinator):
    entities = _build_sensor_entities(coordinator)
    temp = next(e for e in entities if "Temperature" in e.name)
    assert temp.state == 22.5
    assert temp.unit_of_measurement == "°C"


def test_sensor_unique_id(coordinator):
    entities = _build_sensor_entities(coordinator)
    temp = next(e for e in entities if "Temperature" in e.name)
    assert temp.unique_id == "platformatics_device_101_temperature"
