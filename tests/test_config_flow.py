"""Tests for Platformatics config flow."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from custom_components.platformatics.config_flow import PlatformaticsConfigFlow
from custom_components.platformatics.api import PlatformaticsAuthError, PlatformaticsApiError

USER_INPUT = {"host": "192.168.1.100", "username": "admin", "password": "admin"}


def make_flow():
    flow = PlatformaticsConfigFlow()
    flow.hass = MagicMock()
    return flow


@pytest.mark.asyncio
async def test_config_flow_shows_form_when_no_input():
    flow = make_flow()
    result = await flow.async_step_user(None)
    assert result["type"] == "form"
    assert result["step_id"] == "user"


@pytest.mark.asyncio
async def test_config_flow_success():
    flow = make_flow()
    with patch(
        "custom_components.platformatics.config_flow.PlatformaticsApi"
    ) as MockApi:
        instance = MockApi.return_value
        instance.authenticate = AsyncMock()
        result = await flow.async_step_user(USER_INPUT)
    assert result["type"] == "create_entry"
    assert result["title"] == "192.168.1.100"
    assert result["data"] == USER_INPUT


@pytest.mark.asyncio
async def test_config_flow_invalid_auth():
    flow = make_flow()
    with patch(
        "custom_components.platformatics.config_flow.PlatformaticsApi"
    ) as MockApi:
        instance = MockApi.return_value
        instance.authenticate = AsyncMock(side_effect=PlatformaticsAuthError("bad creds"))
        result = await flow.async_step_user(USER_INPUT)
    assert result["type"] == "form"
    assert result["errors"] == {"base": "invalid_auth"}


@pytest.mark.asyncio
async def test_config_flow_cannot_connect():
    flow = make_flow()
    with patch(
        "custom_components.platformatics.config_flow.PlatformaticsApi"
    ) as MockApi:
        instance = MockApi.return_value
        instance.authenticate = AsyncMock(side_effect=PlatformaticsApiError("timeout"))
        result = await flow.async_step_user(USER_INPUT)
    assert result["type"] == "form"
    assert result["errors"] == {"base": "cannot_connect"}
