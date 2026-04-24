"""Shared pytest fixtures.

HA stubs are injected into sys.modules at import time so tests run without
a real homeassistant install (Python 3.14 / Windows environment).
"""
# --- HA stubs must come before any other project imports ---
import sys
import types


def _mod(name: str, **attrs) -> types.ModuleType:
    m = types.ModuleType(name)
    m.__dict__.update(attrs)
    sys.modules[name] = m
    return m


# homeassistant.core
class _HomeAssistant:
    def __init__(self):
        self.data = {}
        self.loop = None
        self.config_entries = types.SimpleNamespace(
            flow=types.SimpleNamespace(
                async_init=None,
                async_configure=None,
            )
        )


# homeassistant.helpers.update_coordinator
class _UpdateFailed(Exception):
    pass


class _DataUpdateCoordinator:
    def __class_getitem__(cls, item):
        return cls

    def __init__(self, hass, logger, *, name, update_interval):
        self.hass = hass
        self.logger = logger
        self.name = name
        self.update_interval = update_interval
        self.data = None

    async def async_config_entry_first_refresh(self):
        self.data = await self._async_update_data()

    async def _async_update_data(self):
        raise NotImplementedError


class _CoordinatorEntity:
    def __class_getitem__(cls, item):
        return cls

    def __init__(self, coordinator):
        self.coordinator = coordinator


# homeassistant.config_entries
class _ConfigFlow:
    VERSION = 1

    def __init__(self):
        self.hass = None

    def async_create_entry(self, *, title, data):
        return {"type": "create_entry", "title": title, "data": data}

    def async_show_form(self, *, step_id, data_schema=None, errors=None):
        return {"type": "form", "step_id": step_id, "errors": errors or {}}


class _ConfigEntry:
    def __init__(self, entry_id="test_entry", data=None):
        self.entry_id = entry_id
        self.data = data or {}


SOURCE_USER = "user"


# homeassistant.data_entry_flow
class _FlowResultType:
    FORM = "form"
    CREATE_ENTRY = "create_entry"


# homeassistant.components.light
ATTR_BRIGHTNESS = "brightness"


class _ColorMode:
    BRIGHTNESS = "brightness"
    ONOFF = "onoff"


class _LightEntity:
    pass


# homeassistant.components.sensor
class _SensorDeviceClass:
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    PM25 = "pm25"
    PM10 = "pm10"
    VOLATILE_ORGANIC_COMPOUNDS_PARTS = "volatile_organic_compounds_parts"


class _SensorStateClass:
    MEASUREMENT = "measurement"


class _SensorEntity:
    pass


# homeassistant.helpers.aiohttp_client
def _async_get_clientsession(hass):
    from unittest.mock import MagicMock
    return MagicMock()


# Inject all stubs into sys.modules
_mod("homeassistant", HomeAssistant=_HomeAssistant)
_mod("homeassistant.core", HomeAssistant=_HomeAssistant)
_mod("homeassistant.helpers")
_mod(
    "homeassistant.helpers.update_coordinator",
    DataUpdateCoordinator=_DataUpdateCoordinator,
    UpdateFailed=_UpdateFailed,
    CoordinatorEntity=_CoordinatorEntity,
)
_mod(
    "homeassistant.helpers.aiohttp_client",
    async_get_clientsession=_async_get_clientsession,
)
_mod("homeassistant.helpers.entity_platform", AddEntitiesCallback=None)
_mod(
    "homeassistant.config_entries",
    ConfigFlow=_ConfigFlow,
    ConfigEntry=_ConfigEntry,
    SOURCE_USER=SOURCE_USER,
)
_mod(
    "homeassistant.data_entry_flow",
    FlowResultType=_FlowResultType,
)
_mod("homeassistant.components")
_mod(
    "homeassistant.components.light",
    ATTR_BRIGHTNESS=ATTR_BRIGHTNESS,
    ColorMode=_ColorMode,
    LightEntity=_LightEntity,
)
_mod(
    "homeassistant.components.sensor",
    SensorDeviceClass=_SensorDeviceClass,
    SensorStateClass=_SensorStateClass,
    SensorEntity=_SensorEntity,
)

# --- Normal imports ---
import pytest
from unittest.mock import AsyncMock, MagicMock
from custom_components.platformatics.api import PlatformaticsApi

MOCK_ZONES = [
    {"id": 1, "name": "Office", "level": 75.0, "outputState": True},
    {"id": 2, "name": "Lobby", "level": 0.0, "outputState": False},
]

MOCK_DEVICES = [
    {
        "id": 101,
        "name": "Office Sensor",
        "zoneId": 1,
        "temperature": 22.5,
        "humidity": 45.0,
        "pm2_5": 8.2,
        "pm10": 12.1,
        "vocIndex": 100,
        "daylightLevel": 60.0,
        "level": 75.0,
        "outputState": True,
    },
    {
        "id": 102,
        "name": "Lobby Light",
        "zoneId": 2,
        "temperature": None,
        "humidity": None,
        "pm2_5": None,
        "pm10": None,
        "vocIndex": None,
        "daylightLevel": None,
        "level": 0.0,
        "outputState": False,
    },
]


@pytest.fixture
def mock_api():
    api = MagicMock(spec=PlatformaticsApi)
    api.get_zones = AsyncMock(return_value=MOCK_ZONES)
    api.get_devices = AsyncMock(return_value=MOCK_DEVICES)
    api.set_zone_level = AsyncMock()
    api.set_zone_output_state = AsyncMock()
    return api
