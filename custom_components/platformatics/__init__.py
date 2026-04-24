"""Platformatics PoE lighting integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PlatformaticsApi
from .const import DOMAIN, PLATFORMS
from .coordinator import PlatformaticsCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Platformatics from a config entry."""
    session = async_get_clientsession(hass)
    api = PlatformaticsApi(
        host=entry.data["host"],
        username=entry.data["username"],
        password=entry.data["password"],
        session=session,
    )
    await api.authenticate()

    coordinator = PlatformaticsCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    hass.data[DOMAIN].pop(entry.entry_id)
    return True
