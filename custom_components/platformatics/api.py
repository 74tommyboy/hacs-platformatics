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
