"""Config flow for Calendar Ortodox integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CalendarOrtodoxAPI
from .const import (
    CONF_INCLUDE_FASTING,
    CONF_INCLUDE_READINGS,
    CONF_LANGUAGE,
    DEFAULT_INCLUDE_FASTING,
    DEFAULT_INCLUDE_READINGS,
    DEFAULT_LANGUAGE,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_LANGUAGE, default=DEFAULT_LANGUAGE): vol.In(["ro", "en"]),
        vol.Optional(CONF_INCLUDE_FASTING, default=DEFAULT_INCLUDE_FASTING): bool,
        vol.Optional(CONF_INCLUDE_READINGS, default=DEFAULT_INCLUDE_READINGS): bool,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    session = async_get_clientsession(hass)
    api = CalendarOrtodoxAPI(session)

    # Try to fetch calendar data to validate the connection
    try:
        calendar_data = await api.get_year_calendar()
        if not calendar_data:
            raise ValueError("No calendar data received")
    except Exception as err:
        _LOGGER.error("Failed to fetch calendar data: %s", err)
        raise

    return {"title": "Calendar Ortodox"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Calendar Ortodox."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "cannot_connect"
            else:
                # Check if already configured
                await self.async_set_unique_id("calendar_ortodox_instance")
                self._abort_if_unique_id_configured()

                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
