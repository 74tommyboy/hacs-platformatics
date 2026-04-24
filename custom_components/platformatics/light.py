"""Light platform for Platformatics zones."""
from __future__ import annotations

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PlatformaticsCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: PlatformaticsCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        PlatformaticsZoneLight(coordinator, zone_id)
        for zone_id in coordinator.data["zones"]
    )


class PlatformaticsZoneLight(CoordinatorEntity[PlatformaticsCoordinator], LightEntity):
    """Represents a Platformatics zone as a dimmable light."""

    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    def __init__(self, coordinator: PlatformaticsCoordinator, zone_id: int) -> None:
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._attr_unique_id = f"platformatics_zone_{zone_id}"

    @property
    def _zone(self) -> dict:
        return self.coordinator.data["zones"][self._zone_id]

    @property
    def name(self) -> str:
        return self._zone.get("name", f"Zone {self._zone_id}")

    @property
    def is_on(self) -> bool:
        return bool(self._zone.get("outputState", False))

    @property
    def brightness(self) -> int | None:
        level = self._zone.get("level", 0)
        return round(level * 255 / 100)

    @property
    def _current_level(self) -> int:
        """Return the zone's current level (0-100), defaulting to 100."""
        return self._zone.get("level", 100) or 100

    @property
    def unique_id(self) -> str:
        return self._attr_unique_id

    async def async_turn_on(self, **kwargs) -> None:
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        if brightness is not None:
            level = round(brightness * 100 / 255)
            await self.coordinator.api.set_zone_level(
                zone_id=self._zone_id, level=level, output_state=True
            )
        else:
            await self.coordinator.api.set_zone_output_state(
                zone_id=self._zone_id, on=True, current_level=self._current_level
            )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.api.set_zone_output_state(
            zone_id=self._zone_id, on=False, current_level=self._current_level
        )
        await self.coordinator.async_request_refresh()
