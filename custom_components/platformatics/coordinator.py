"""DataUpdateCoordinator for Platformatics."""
from __future__ import annotations

import logging
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import PlatformaticsApi, PlatformaticsApiError
from .const import DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class PlatformaticsCoordinator(DataUpdateCoordinator[dict]):
    """Polls the Platformatics controller and stores zones + devices."""

    def __init__(self, hass: HomeAssistant, api: PlatformaticsApi) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.api = api

    async def _async_update_data(self) -> dict:
        try:
            zones = await self.api.get_zones()
            devices = await self.api.get_devices()
            return {
                "zones": {z["id"]: z for z in zones},
                "devices": {d["id"]: d for d in devices},
            }
        except PlatformaticsApiError as err:
            raise UpdateFailed(f"Error communicating with Platformatics: {err}") from err
