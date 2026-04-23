# Platformatics Home Assistant Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a HACS-compatible Home Assistant custom integration that connects to a Platformatics PoE lighting controller, exposes zones as `light` entities and environmental sensors as `sensor` entities.

**Architecture:** A `DataUpdateCoordinator` polls `/api/zones` and `/api/devices` every 30 seconds. An async `PlatformaticsApi` client wraps the REST API and handles token auth (bearer token, 8hr TTL, auto-refresh on 401). Zones become `LightEntity` instances; devices with sensor readings become `SensorEntity` instances. Config is entered via a UI flow (host + username + password).

**Tech Stack:** Python 3.11+, Home Assistant core (`DataUpdateCoordinator`, `ConfigFlow`, `LightEntity`, `SensorEntity`), `aiohttp` (provided by HA), `pytest-homeassistant-custom-component` for tests, `voluptuous` for schema validation.

---

## File Map

```
custom_components/
└── platformatics/
    ├── __init__.py          # Entry setup/teardown, wires coordinator + platforms
    ├── manifest.json        # HA integration manifest (domain, version, deps)
    ├── config_flow.py       # UI wizard: host + username + password → test auth → create entry
    ├── const.py             # DOMAIN, SCAN_INTERVAL, PLATFORMS, sensor key definitions
    ├── api.py               # Async REST client: auth, get_zones, get_devices, set_zone_level
    ├── coordinator.py       # DataUpdateCoordinator: polls API, stores {zones, devices}
    ├── light.py             # PlatformaticsZoneLight(CoordinatorEntity, LightEntity) per zone
    ├── sensor.py            # PlatformaticsSensor(CoordinatorEntity, SensorEntity) per sensor field
    └── strings.json         # UI strings for config flow labels + error messages

tests/
├── __init__.py
├── conftest.py              # pytest fixtures: mock_api, mock_coordinator, hass setup
├── test_api.py              # Unit tests for PlatformaticsApi (auth, get, put, 401 retry)
├── test_config_flow.py      # Tests config flow: success, bad creds, cannot connect
├── test_light.py            # Tests ZoneLight: state, turn_on, turn_off, brightness
└── test_sensor.py           # Tests sensor entities: state, unit, device class

hacs.json                    # HACS manifest
pyproject.toml               # pytest config + deps
README.md                    # Install instructions (created last)
```

---

## Task 1: Repo Scaffold + Constants

**Files:**
- Create: `custom_components/platformatics/const.py`
- Create: `custom_components/platformatics/__init__.py` (stub only)
- Create: `custom_components/platformatics/manifest.json`
- Create: `hacs.json`
- Create: `pyproject.toml`
- Create: `tests/__init__.py`

- [ ] **Step 1.1: Initialize git repo**

```bash
cd C:\Users\El_Gu\Projects\Platformatics
git init
```

- [ ] **Step 1.2: Create directory structure**

```bash
mkdir -p custom_components/platformatics tests
```

- [ ] **Step 1.3: Create `custom_components/platformatics/const.py`**

```python
from datetime import timedelta

DOMAIN = "platformatics"
SCAN_INTERVAL = timedelta(seconds=30)
PLATFORMS = ["light", "sensor"]

SENSOR_DEFINITIONS = [
    # (device_key, name, unit, device_class, state_class)
    ("temperature", "Temperature", "°C", "temperature", "measurement"),
    ("humidity", "Humidity", "%", "humidity", "measurement"),
    ("pm2_5", "PM2.5", "µg/m³", "pm25", "measurement"),
    ("pm10", "PM10", "µg/m³", "pm10", "measurement"),
    ("vocIndex", "VOC Index", None, "volatile_organic_compounds_parts", "measurement"),
    ("daylightLevel", "Daylight Level", "%", None, "measurement"),
]
```

- [ ] **Step 1.4: Create `custom_components/platformatics/__init__.py` (stub)**

```python
"""Platformatics PoE lighting integration."""
```

- [ ] **Step 1.5: Create `custom_components/platformatics/manifest.json`**

```json
{
  "domain": "platformatics",
  "name": "Platformatics",
  "version": "1.0.0",
  "config_flow": true,
  "documentation": "https://github.com/TommyboyDesigns/hacs-platformatics",
  "issue_tracker": "https://github.com/TommyboyDesigns/hacs-platformatics/issues",
  "requirements": [],
  "dependencies": [],
  "codeowners": ["@TommyboyDesigns"],
  "iot_class": "local_polling"
}
```

- [ ] **Step 1.6: Create `hacs.json`**

```json
{
  "name": "Platformatics",
  "render_readme": true
}
```

- [ ] **Step 1.7: Create `pyproject.toml`**

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.pytest]
filterwarnings = ["ignore::DeprecationWarning"]

[project]
name = "hacs-platformatics"
version = "1.0.0"
requires-python = ">=3.11"

[project.optional-dependencies]
dev = [
    "pytest",
    "pytest-asyncio",
    "pytest-homeassistant-custom-component",
    "aiohttp",
    "aioresponses",
]
```

- [ ] **Step 1.8: Create `tests/__init__.py`**

```python
```

- [ ] **Step 1.9: Commit**

```bash
git add .
git commit -m "feat: scaffold repo with manifest, constants, and hacs.json"
```

---

## Task 2: API Client — Authentication

**Files:**
- Create: `custom_components/platformatics/api.py`
- Create: `tests/test_api.py` (auth tests only)

- [ ] **Step 2.1: Write failing tests for API auth**

Create `tests/test_api.py`:

```python
"""Tests for PlatformaticsApi authentication."""
import pytest
from aioresponses import aioresponses
import aiohttp
from custom_components.platformatics.api import (
    PlatformaticsApi,
    PlatformaticsAuthError,
    PlatformaticsApiError,
)

BASE_URL = "https://192.168.1.100:8080"


@pytest.fixture
def api():
    """Return an API instance with a real ClientSession (mocked at transport layer)."""
    session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False))
    yield PlatformaticsApi(
        host="192.168.1.100",
        username="admin",
        password="admin",
        session=session,
    )
    # teardown handled by aioresponses context manager


@pytest.mark.asyncio
async def test_authenticate_success(api):
    with aioresponses() as m:
        m.post(
            f"{BASE_URL}/token",
            payload={"access_token": "abc123", "token_type": "bearer"},
            status=200,
        )
        await api.authenticate()
        assert api.token == "abc123"


@pytest.mark.asyncio
async def test_authenticate_bad_credentials(api):
    with aioresponses() as m:
        m.post(f"{BASE_URL}/token", status=401)
        with pytest.raises(PlatformaticsAuthError):
            await api.authenticate()


@pytest.mark.asyncio
async def test_authenticate_connection_error(api):
    with aioresponses() as m:
        m.post(f"{BASE_URL}/token", exception=aiohttp.ClientConnectionError())
        with pytest.raises(PlatformaticsApiError):
            await api.authenticate()
```

- [ ] **Step 2.2: Run tests to confirm they fail**

```bash
cd C:\Users\El_Gu\Projects\Platformatics
python -m pytest tests/test_api.py -v 2>&1 | head -30
```

Expected: `ModuleNotFoundError` or `ImportError` — api.py doesn't exist yet.

- [ ] **Step 2.3: Create `custom_components/platformatics/api.py`**

```python
"""Async REST client for the Platformatics API."""
from __future__ import annotations

import aiohttp
from base64 import b64encode


class PlatformaticsApiError(Exception):
    """Base error for Platformatics API failures."""


class PlatformaticsAuthError(PlatformaticsApiError):
    """Raised when authentication fails (wrong credentials)."""


class PlatformaticsApi:
    """Wraps the Platformatics REST API."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        session: aiohttp.ClientSession,
    ) -> None:
        self._host = host
        self._username = username
        self._password = password
        self._session = session
        self._token: str | None = None

    @property
    def base_url(self) -> str:
        return f"https://{self._host}:8080"

    @property
    def token(self) -> str | None:
        return self._token

    async def authenticate(self) -> None:
        """Obtain a bearer token using HTTP Basic credentials."""
        credentials = b64encode(
            f"{self._username}:{self._password}".encode()
        ).decode()
        try:
            async with self._session.post(
                f"{self.base_url}/token",
                headers={
                    "Authorization": f"Basic {credentials}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                data="",
                ssl=False,
            ) as resp:
                if resp.status == 401:
                    raise PlatformaticsAuthError("Invalid credentials")
                resp.raise_for_status()
                data = await resp.json()
                self._token = data["access_token"]
        except PlatformaticsAuthError:
            raise
        except aiohttp.ClientError as err:
            raise PlatformaticsApiError(f"Connection error: {err}") from err
```

- [ ] **Step 2.4: Run tests to confirm they pass**

```bash
python -m pytest tests/test_api.py -v
```

Expected: 3 tests pass.

- [ ] **Step 2.5: Commit**

```bash
git add custom_components/platformatics/api.py tests/test_api.py
git commit -m "feat: add PlatformaticsApi with token authentication"
```

---

## Task 3: API Client — Get Zones & Devices

**Files:**
- Modify: `custom_components/platformatics/api.py` (add `_get`, `get_zones`, `get_devices`)
- Modify: `tests/test_api.py` (add GET tests)

- [ ] **Step 3.1: Write failing tests**

Append to `tests/test_api.py`:

```python
@pytest.fixture
def authed_api():
    """Return an API instance that already has a token."""
    session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False))
    api = PlatformaticsApi(
        host="192.168.1.100",
        username="admin",
        password="admin",
        session=session,
    )
    api._token = "abc123"
    return api


ZONE_PAYLOAD = [{"id": 1, "name": "Office", "level": 75.0, "outputState": True}]
DEVICE_PAYLOAD = [
    {
        "id": 101,
        "name": "Office Sensor",
        "zoneId": 1,
        "temperature": 22.5,
        "humidity": 45.0,
        "pm2_5": None,
        "pm10": None,
        "vocIndex": None,
        "daylightLevel": None,
        "level": 75.0,
        "outputState": True,
    }
]


@pytest.mark.asyncio
async def test_get_zones(authed_api):
    with aioresponses() as m:
        m.get(f"{BASE_URL}/api/zones", payload=ZONE_PAYLOAD, status=200)
        zones = await authed_api.get_zones()
        assert zones == ZONE_PAYLOAD


@pytest.mark.asyncio
async def test_get_devices(authed_api):
    with aioresponses() as m:
        m.get(f"{BASE_URL}/api/devices", payload=DEVICE_PAYLOAD, status=200)
        devices = await authed_api.get_devices()
        assert devices == DEVICE_PAYLOAD


@pytest.mark.asyncio
async def test_get_reauth_on_401(authed_api):
    """If a GET returns 401, re-authenticate and retry once."""
    with aioresponses() as m:
        m.get(f"{BASE_URL}/api/zones", status=401)
        m.post(f"{BASE_URL}/token", payload={"access_token": "newtoken"}, status=200)
        m.get(f"{BASE_URL}/api/zones", payload=ZONE_PAYLOAD, status=200)
        zones = await authed_api.get_zones()
        assert zones == ZONE_PAYLOAD
        assert authed_api.token == "newtoken"
```

- [ ] **Step 3.2: Run to confirm failure**

```bash
python -m pytest tests/test_api.py::test_get_zones -v
```

Expected: `AttributeError: 'PlatformaticsApi' object has no attribute 'get_zones'`

- [ ] **Step 3.3: Add `_get`, `get_zones`, `get_devices` to `api.py`**

Append inside the `PlatformaticsApi` class (after `authenticate`):

```python
    @property
    def _auth_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def _get(self, path: str, _retry: bool = True) -> list | dict:
        """Perform an authenticated GET. Re-authenticates once on 401."""
        try:
            async with self._session.get(
                f"{self.base_url}{path}",
                headers=self._auth_headers,
                ssl=False,
            ) as resp:
                if resp.status == 401 and _retry:
                    await self.authenticate()
                    return await self._get(path, _retry=False)
                resp.raise_for_status()
                return await resp.json()
        except PlatformaticsAuthError:
            raise
        except aiohttp.ClientError as err:
            raise PlatformaticsApiError(f"Request failed: {err}") from err

    async def get_zones(self) -> list[dict]:
        """Return all zones from the controller."""
        return await self._get("/api/zones")

    async def get_devices(self) -> list[dict]:
        """Return all devices from the controller."""
        return await self._get("/api/devices")
```

- [ ] **Step 3.4: Run tests to confirm pass**

```bash
python -m pytest tests/test_api.py -v
```

Expected: 6 tests pass.

- [ ] **Step 3.5: Commit**

```bash
git add custom_components/platformatics/api.py tests/test_api.py
git commit -m "feat: add get_zones and get_devices with 401 auto-retry"
```

---

## Task 4: API Client — Control Endpoints

**Files:**
- Modify: `custom_components/platformatics/api.py` (add `_put`, `set_zone_level`, `set_zone_output_state`)
- Modify: `tests/test_api.py` (add PUT tests)

- [ ] **Step 4.1: Write failing tests**

Append to `tests/test_api.py`:

```python
@pytest.mark.asyncio
async def test_set_zone_level(authed_api):
    with aioresponses() as m:
        m.put(f"{BASE_URL}/api/level/zones/1", payload=True, status=200)
        await authed_api.set_zone_level(zone_id=1, level=75)
        # verify request body contained value=75
        call = m.requests[("PUT", f"{BASE_URL}/api/level/zones/1")][0]
        assert call.kwargs["json"] == {"value": 75}


@pytest.mark.asyncio
async def test_set_zone_level_with_output_state(authed_api):
    with aioresponses() as m:
        m.put(f"{BASE_URL}/api/level/zones/1", payload=True, status=200)
        await authed_api.set_zone_level(zone_id=1, level=50, output_state=True)
        call = m.requests[("PUT", f"{BASE_URL}/api/level/zones/1")][0]
        assert call.kwargs["json"] == {"value": 50, "outputState": True}


@pytest.mark.asyncio
async def test_set_zone_output_state_off(authed_api):
    with aioresponses() as m:
        m.put(f"{BASE_URL}/api/level/zones/1", payload=True, status=200)
        await authed_api.set_zone_output_state(zone_id=1, on=False)
        call = m.requests[("PUT", f"{BASE_URL}/api/level/zones/1")][0]
        assert call.kwargs["json"] == {"outputState": False}


@pytest.mark.asyncio
async def test_put_reauth_on_401(authed_api):
    with aioresponses() as m:
        m.put(f"{BASE_URL}/api/level/zones/1", status=401)
        m.post(f"{BASE_URL}/token", payload={"access_token": "fresh"}, status=200)
        m.put(f"{BASE_URL}/api/level/zones/1", payload=True, status=200)
        await authed_api.set_zone_output_state(zone_id=1, on=True)
        assert authed_api.token == "fresh"
```

- [ ] **Step 4.2: Run to confirm failure**

```bash
python -m pytest tests/test_api.py::test_set_zone_level -v
```

Expected: `AttributeError: 'PlatformaticsApi' object has no attribute 'set_zone_level'`

- [ ] **Step 4.3: Add `_put`, `set_zone_level`, `set_zone_output_state` to `api.py`**

Append inside the `PlatformaticsApi` class:

```python
    async def _put(self, path: str, data: dict, _retry: bool = True) -> None:
        """Perform an authenticated PUT. Re-authenticates once on 401."""
        try:
            async with self._session.put(
                f"{self.base_url}{path}",
                headers=self._auth_headers,
                json=data,
                ssl=False,
            ) as resp:
                if resp.status == 401 and _retry:
                    await self.authenticate()
                    return await self._put(path, data, _retry=False)
                resp.raise_for_status()
        except PlatformaticsAuthError:
            raise
        except aiohttp.ClientError as err:
            raise PlatformaticsApiError(f"Request failed: {err}") from err

    async def set_zone_level(
        self,
        zone_id: int,
        level: int,
        output_state: bool | None = None,
    ) -> None:
        """Set zone brightness level (0-100). Optionally set on/off state."""
        body: dict = {"value": level}
        if output_state is not None:
            body["outputState"] = output_state
        await self._put(f"/api/level/zones/{zone_id}", body)

    async def set_zone_output_state(self, zone_id: int, on: bool) -> None:
        """Turn a zone on or off without changing its level."""
        await self._put(f"/api/level/zones/{zone_id}", {"outputState": on})
```

- [ ] **Step 4.4: Run all API tests**

```bash
python -m pytest tests/test_api.py -v
```

Expected: 10 tests pass.

- [ ] **Step 4.5: Commit**

```bash
git add custom_components/platformatics/api.py tests/test_api.py
git commit -m "feat: add zone level and output state control endpoints"
```

---

## Task 5: DataUpdateCoordinator

**Files:**
- Create: `custom_components/platformatics/coordinator.py`
- Create: `tests/conftest.py`
- Create: `tests/test_coordinator.py`

- [ ] **Step 5.1: Create `tests/conftest.py`**

```python
"""Shared pytest fixtures."""
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
```

- [ ] **Step 5.2: Write failing coordinator tests**

Create `tests/test_coordinator.py`:

```python
"""Tests for PlatformaticsCoordinator."""
import pytest
from unittest.mock import AsyncMock
from homeassistant.core import HomeAssistant
from custom_components.platformatics.coordinator import PlatformaticsCoordinator
from custom_components.platformatics.api import PlatformaticsApiError


@pytest.mark.asyncio
async def test_coordinator_fetches_data(hass: HomeAssistant, mock_api):
    coordinator = PlatformaticsCoordinator(hass, mock_api)
    await coordinator._async_update_data()

    assert coordinator.data["zones"][1]["name"] == "Office"
    assert coordinator.data["zones"][2]["name"] == "Lobby"
    assert coordinator.data["devices"][101]["temperature"] == 22.5


@pytest.mark.asyncio
async def test_coordinator_raises_update_failed_on_api_error(hass: HomeAssistant, mock_api):
    from homeassistant.helpers.update_coordinator import UpdateFailed
    mock_api.get_zones = AsyncMock(side_effect=PlatformaticsApiError("timeout"))

    coordinator = PlatformaticsCoordinator(hass, mock_api)
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
```

- [ ] **Step 5.3: Run to confirm failure**

```bash
python -m pytest tests/test_coordinator.py -v
```

Expected: `ModuleNotFoundError` for `coordinator`.

- [ ] **Step 5.4: Create `custom_components/platformatics/coordinator.py`**

```python
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
```

- [ ] **Step 5.5: Run coordinator tests**

```bash
python -m pytest tests/test_coordinator.py -v
```

Expected: 2 tests pass.

- [ ] **Step 5.6: Commit**

```bash
git add custom_components/platformatics/coordinator.py tests/conftest.py tests/test_coordinator.py
git commit -m "feat: add DataUpdateCoordinator with zone and device polling"
```

---

## Task 6: Config Flow

**Files:**
- Create: `custom_components/platformatics/config_flow.py`
- Create: `custom_components/platformatics/strings.json`
- Create: `tests/test_config_flow.py`

- [ ] **Step 6.1: Write failing config flow tests**

Create `tests/test_config_flow.py`:

```python
"""Tests for Platformatics config flow."""
import pytest
from unittest.mock import AsyncMock, patch
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from custom_components.platformatics.const import DOMAIN
from custom_components.platformatics.api import PlatformaticsAuthError, PlatformaticsApiError

USER_INPUT = {"host": "192.168.1.100", "username": "admin", "password": "admin"}


@pytest.mark.asyncio
async def test_config_flow_success(hass: HomeAssistant):
    with patch(
        "custom_components.platformatics.config_flow.PlatformaticsApi"
    ) as MockApi:
        instance = MockApi.return_value
        instance.authenticate = AsyncMock()

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=USER_INPUT
        )
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == "192.168.1.100"
        assert result["data"] == USER_INPUT


@pytest.mark.asyncio
async def test_config_flow_invalid_auth(hass: HomeAssistant):
    with patch(
        "custom_components.platformatics.config_flow.PlatformaticsApi"
    ) as MockApi:
        instance = MockApi.return_value
        instance.authenticate = AsyncMock(side_effect=PlatformaticsAuthError())

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=USER_INPUT
        )
        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": "invalid_auth"}


@pytest.mark.asyncio
async def test_config_flow_cannot_connect(hass: HomeAssistant):
    with patch(
        "custom_components.platformatics.config_flow.PlatformaticsApi"
    ) as MockApi:
        instance = MockApi.return_value
        instance.authenticate = AsyncMock(side_effect=PlatformaticsApiError())

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=USER_INPUT
        )
        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": "cannot_connect"}
```

- [ ] **Step 6.2: Run to confirm failure**

```bash
python -m pytest tests/test_config_flow.py -v
```

Expected: import error or flow not found.

- [ ] **Step 6.3: Create `custom_components/platformatics/strings.json`**

```json
{
  "config": {
    "step": {
      "user": {
        "title": "Connect to Platformatics Controller",
        "data": {
          "host": "Controller IP Address",
          "username": "Username",
          "password": "Password"
        }
      }
    },
    "error": {
      "cannot_connect": "Cannot connect to the controller. Check the IP address.",
      "invalid_auth": "Invalid username or password.",
      "unknown": "Unexpected error."
    },
    "abort": {
      "already_configured": "Controller is already configured."
    }
  }
}
```

- [ ] **Step 6.4: Create `custom_components/platformatics/config_flow.py`**

```python
"""Config flow for Platformatics integration."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PlatformaticsApi, PlatformaticsAuthError, PlatformaticsApiError
from .const import DOMAIN

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("host"): str,
        vol.Required("username", default="admin"): str,
        vol.Required("password"): str,
    }
)


class PlatformaticsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial setup flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> config_entries.FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            api = PlatformaticsApi(
                host=user_input["host"],
                username=user_input["username"],
                password=user_input["password"],
                session=session,
            )
            try:
                await api.authenticate()
            except PlatformaticsAuthError:
                errors["base"] = "invalid_auth"
            except PlatformaticsApiError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=user_input["host"],
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
```

- [ ] **Step 6.5: Run config flow tests**

```bash
python -m pytest tests/test_config_flow.py -v
```

Expected: 3 tests pass.

- [ ] **Step 6.6: Commit**

```bash
git add custom_components/platformatics/config_flow.py custom_components/platformatics/strings.json tests/test_config_flow.py
git commit -m "feat: add config flow with host/username/password and error handling"
```

---

## Task 7: Integration Entry Setup (`__init__.py`)

**Files:**
- Modify: `custom_components/platformatics/__init__.py`

- [ ] **Step 7.1: Write the entry setup and teardown**

Replace `custom_components/platformatics/__init__.py` with:

```python
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
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded
```

- [ ] **Step 7.2: Verify no syntax errors**

```bash
python -m py_compile custom_components/platformatics/__init__.py && echo "OK"
```

Expected: `OK`

- [ ] **Step 7.3: Commit**

```bash
git add custom_components/platformatics/__init__.py
git commit -m "feat: wire coordinator and platforms in async_setup_entry"
```

---

## Task 8: Light Platform

**Files:**
- Create: `custom_components/platformatics/light.py`
- Create: `tests/test_light.py`

- [ ] **Step 8.1: Write failing light tests**

Create `tests/test_light.py`:

```python
"""Tests for PlatformaticsZoneLight."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
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
```

- [ ] **Step 8.2: Run to confirm failure**

```bash
python -m pytest tests/test_light.py -v
```

Expected: `ModuleNotFoundError` for `light`.

- [ ] **Step 8.3: Create `custom_components/platformatics/light.py`**

```python
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

    async def async_turn_on(self, **kwargs) -> None:
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        if brightness is not None:
            level = round(brightness * 100 / 255)
            await self.coordinator.api.set_zone_level(
                zone_id=self._zone_id, level=level, output_state=True
            )
        else:
            await self.coordinator.api.set_zone_output_state(
                zone_id=self._zone_id, on=True
            )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.api.set_zone_output_state(
            zone_id=self._zone_id, on=False
        )
        await self.coordinator.async_request_refresh()
```

- [ ] **Step 8.4: Run light tests**

```bash
python -m pytest tests/test_light.py -v
```

Expected: 9 tests pass.

- [ ] **Step 8.5: Commit**

```bash
git add custom_components/platformatics/light.py tests/test_light.py
git commit -m "feat: add light platform with zone dimming and on/off control"
```

---

## Task 9: Sensor Platform

**Files:**
- Create: `custom_components/platformatics/sensor.py`
- Create: `tests/test_sensor.py`

- [ ] **Step 9.1: Write failing sensor tests**

Create `tests/test_sensor.py`:

```python
"""Tests for PlatformaticsSensor."""
import pytest
from unittest.mock import AsyncMock, MagicMock
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
    # Device 101 has 6 sensor fields with values; device 102 has none
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
```

- [ ] **Step 9.2: Run to confirm failure**

```bash
python -m pytest tests/test_sensor.py -v
```

Expected: `ModuleNotFoundError` for `sensor`.

- [ ] **Step 9.3: Create `custom_components/platformatics/sensor.py`**

```python
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

# Map device_class strings to HA SensorDeviceClass enum values
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
    def state(self) -> float | int | None:
        device = self.coordinator.data["devices"].get(self._device_id, {})
        return device.get(self._sensor_key)

    @property
    def unit_of_measurement(self) -> str | None:
        return self._attr_native_unit_of_measurement
```

- [ ] **Step 9.4: Run sensor tests**

```bash
python -m pytest tests/test_sensor.py -v
```

Expected: 3 tests pass.

- [ ] **Step 9.5: Run full test suite**

```bash
python -m pytest tests/ -v
```

Expected: All tests pass (aim for 20+).

- [ ] **Step 9.6: Commit**

```bash
git add custom_components/platformatics/sensor.py tests/test_sensor.py
git commit -m "feat: add sensor platform for temperature, humidity, PM, and VOC readings"
```

---

## Task 10: GitHub Release Prep

**Files:**
- Create: `README.md`
- Create: `.gitignore`

- [ ] **Step 10.1: Create `.gitignore`**

```
__pycache__/
*.py[cod]
.pytest_cache/
.venv/
*.egg-info/
dist/
.env
```

- [ ] **Step 10.2: Create `README.md`**

Write `README.md` with:
- What it does (1 paragraph)
- Requirements section: Home Assistant 2024.1+, HACS installed, Platformatics controller on local network
- Installation section:
  1. In HACS → Integrations → ⋮ → Custom repositories → add this repo URL → category: Integration
  2. Click Install on "Platformatics"
  3. Restart Home Assistant
  4. Settings → Integrations → Add Integration → search "Platformatics"
  5. Enter controller IP, username (`admin`), password
- Entities section: describes `light` (one per zone) and `sensor` entities
- Limitations: polling every 30s, no push; read-only sensors (no scene/clip control in v1)

- [ ] **Step 10.3: Tag a release**

```bash
git add README.md .gitignore
git commit -m "docs: add README with HACS install instructions"
git tag v1.0.0
```

- [ ] **Step 10.4: Push to GitHub**

Create a new repo at `github.com/TommyboyDesigns/hacs-platformatics`, then:

```bash
git remote add origin https://github.com/TommyboyDesigns/hacs-platformatics.git
git push -u origin main
git push origin v1.0.0
```

---

## Self-Review

### Spec coverage
- [x] HACS-installable custom integration → `hacs.json` + correct repo structure
- [x] Config UI (host + credentials) → `config_flow.py`
- [x] Zones exposed as `light` entities with dimming → `light.py`
- [x] Environmental sensors → `sensor.py`
- [x] Token auth with auto-refresh → `api.py` (`_retry` on 401)
- [x] Polling coordinator → `coordinator.py` (30s interval)
- [x] Error handling in config flow → invalid_auth + cannot_connect
- [x] Entry unload → `async_unload_entry` in `__init__.py`

### Placeholder scan
No TBDs, TODOs, or vague steps present.

### Type consistency
- `set_zone_level(zone_id, level, output_state)` — consistent across api.py, light.py, test_light.py
- `set_zone_output_state(zone_id, on)` — consistent across api.py, light.py, test_light.py
- `coordinator.data["zones"][id]` and `coordinator.data["devices"][id]` — consistent across coordinator, light, sensor, and all tests
- `PlatformaticsApiError` / `PlatformaticsAuthError` — consistent in api.py, config_flow.py, coordinator.py, test_api.py, test_config_flow.py
