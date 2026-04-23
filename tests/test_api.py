"""Tests for PlatformaticsApi authentication."""
import pytest
from aioresponses import aioresponses
import aiohttp
import yarl
from custom_components.platformatics.api import (
    PlatformaticsApi,
    PlatformaticsAuthError,
    PlatformaticsApiError,
)

BASE_URL = "https://192.168.1.100:8080"


@pytest.fixture
async def api():
    """Return an API instance with a real ClientSession (mocked at transport layer)."""
    session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False))
    yield PlatformaticsApi(
        host="192.168.1.100",
        username="admin",
        password="admin",
        session=session,
    )
    await session.close()


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


@pytest.fixture
async def authed_api():
    """Return an API instance that already has a token."""
    session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False))
    api = PlatformaticsApi(
        host="192.168.1.100",
        username="admin",
        password="admin",
        session=session,
    )
    api._token = "abc123"
    yield api
    await session.close()


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


@pytest.mark.asyncio
async def test_set_zone_level(authed_api):
    with aioresponses() as m:
        m.put(f"{BASE_URL}/api/level/zones/1", payload=True, status=200)
        await authed_api.set_zone_level(zone_id=1, level=75)
        call = m.requests[("PUT", yarl.URL(f"{BASE_URL}/api/level/zones/1"))][0]
        assert call.kwargs["json"] == {"value": 75}


@pytest.mark.asyncio
async def test_set_zone_level_with_output_state(authed_api):
    with aioresponses() as m:
        m.put(f"{BASE_URL}/api/level/zones/1", payload=True, status=200)
        await authed_api.set_zone_level(zone_id=1, level=50, output_state=True)
        call = m.requests[("PUT", yarl.URL(f"{BASE_URL}/api/level/zones/1"))][0]
        assert call.kwargs["json"] == {"value": 50, "outputState": True}


@pytest.mark.asyncio
async def test_set_zone_output_state_off(authed_api):
    with aioresponses() as m:
        m.put(f"{BASE_URL}/api/level/zones/1", payload=True, status=200)
        await authed_api.set_zone_output_state(zone_id=1, on=False)
        call = m.requests[("PUT", yarl.URL(f"{BASE_URL}/api/level/zones/1"))][0]
        assert call.kwargs["json"] == {"outputState": False}


@pytest.mark.asyncio
async def test_put_reauth_on_401(authed_api):
    with aioresponses() as m:
        m.put(f"{BASE_URL}/api/level/zones/1", status=401)
        m.post(f"{BASE_URL}/token", payload={"access_token": "fresh"}, status=200)
        m.put(f"{BASE_URL}/api/level/zones/1", payload=True, status=200)
        await authed_api.set_zone_output_state(zone_id=1, on=True)
        assert authed_api.token == "fresh"
