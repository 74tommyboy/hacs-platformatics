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
