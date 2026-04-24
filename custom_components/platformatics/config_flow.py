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


class PlatformaticsConfigFlow(config_entries.ConfigFlow):
    """Handle the initial setup flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> dict:
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
