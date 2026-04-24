"""Tests for PlatformaticsZoneLight."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from homeassistant.components.light import ATTR_BRIGHTNESS
from custom_components.platformatics.light import PlatformaticsZoneLight
from custom_components.platformatics.coordinator import PlatformaticsCoordinator


@pytest.fixture
def coordinator(mock_api):
    coord = MagicMock(spec=PlatformaticsCoordinator)
    coord.api = mock_api
    coord.data = {
        "zones": {
            1: {"id": 1, "name": "Office", "level": 75.0, "outputState": True},
            2: {"id": 2, "name": "Lobby", "level": 0.0, "outputState": False},
        },
        "devices": {},
    }
    coord.async_request_refresh = AsyncMock()
    return coord


def make_light(coordinator, zone_id):
    light = PlatformaticsZoneLight(coordinator, zone_id)
    light.hass = MagicMock()
    return light


def test_light_name(coordinator):
    light = make_light(coordinator, 1)
    assert light.name == "Office"


def test_light_is_on(coordinator):
    light = make_light(coordinator, 1)
    assert light.is_on is True


def test_light_is_off(coordinator):
    light = make_light(coordinator, 2)
    assert light.is_on is False


def test_light_brightness(coordinator):
    light = make_light(coordinator, 1)
    # 75% level → round(75 * 255 / 100) = 191
    assert light.brightness == 191


def test_light_unique_id(coordinator):
    light = make_light(coordinator, 1)
    assert light.unique_id == "platformatics_zone_1"


@pytest.mark.asyncio
async def test_turn_on_no_brightness(coordinator):
    light = make_light(coordinator, 2)
    await light.async_turn_on()
    coordinator.api.set_zone_output_state.assert_called_once_with(zone_id=2, on=True)
    coordinator.async_request_refresh.assert_called_once()


@pytest.mark.asyncio
async def test_turn_on_with_brightness(coordinator):
    light = make_light(coordinator, 2)
    await light.async_turn_on(**{ATTR_BRIGHTNESS: 128})
    # 128 * 100 / 255 = 50 (rounded)
    coordinator.api.set_zone_level.assert_called_once_with(
        zone_id=2, level=50, output_state=True
    )


@pytest.mark.asyncio
async def test_turn_off(coordinator):
    light = make_light(coordinator, 1)
    await light.async_turn_off()
    coordinator.api.set_zone_output_state.assert_called_once_with(zone_id=1, on=False)
    coordinator.async_request_refresh.assert_called_once()
