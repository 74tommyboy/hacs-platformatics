"""Tests for PlatformaticsCoordinator."""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from custom_components.platformatics.coordinator import PlatformaticsCoordinator
from custom_components.platformatics.api import PlatformaticsApiError
from homeassistant.helpers.update_coordinator import UpdateFailed


@pytest.mark.asyncio
async def test_coordinator_fetches_data(mock_api):
    hass = MagicMock()
    hass.loop = asyncio.get_event_loop()
    coordinator = PlatformaticsCoordinator(hass, mock_api)
    data = await coordinator._async_update_data()

    assert data["zones"][1]["name"] == "Office"
    assert data["zones"][2]["name"] == "Lobby"
    assert data["devices"][101]["temperature"] == 22.5


@pytest.mark.asyncio
async def test_coordinator_raises_update_failed_on_api_error(mock_api):
    mock_api.get_zones = AsyncMock(side_effect=PlatformaticsApiError("timeout"))

    hass = MagicMock()
    hass.loop = asyncio.get_event_loop()
    coordinator = PlatformaticsCoordinator(hass, mock_api)
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
