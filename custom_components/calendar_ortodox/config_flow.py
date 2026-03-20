"""Config flow for Calendar Ortodox integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CalendarOrtodoxAPI, CatholicCalendarAPI
from .const import (
    CALENDAR_TYPE_BOTH,
    CALENDAR_TYPE_CATHOLIC,
    CALENDAR_TYPE_ORTHODOX,
    CONF_CALENDAR_TYPE,
    CONF_INCLUDE_FASTING,
    CONF_INCLUDE_READINGS,
    CONF_LANGUAGE,
    DEFAULT_CALENDAR_TYPE,
    DEFAULT_INCLUDE_FASTING,
    DEFAULT_INCLUDE_READINGS,
    DEFAULT_LANGUAGE,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

CALENDAR_TYPE_OPTIONS = {
    CALENDAR_TYPE_ORTHODOX: "Ortodox",
    CALENDAR_TYPE_CATHOLIC: "Romano-Catolic",
    CALENDAR_TYPE_BOTH: "Ambele (Ortodox + Romano-Catolic)",
}

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_CALENDAR_TYPE, default=DEFAULT_CALENDAR_TYPE): vol.In(
            CALENDAR_TYPE_OPTIONS
        ),
        vol.Optional(CONF_LANGUAGE, default=DEFAULT_LANGUAGE): vol.In(["ro", "en"]),
        vol.Optional(CONF_INCLUDE_FASTING, default=DEFAULT_INCLUDE_FASTING): bool,
        vol.Optional(CONF_INCLUDE_READINGS, default=DEFAULT_INCLUDE_READINGS): bool,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    session = async_get_clientsession(hass)
    calendar_type = data.get(CONF_CALENDAR_TYPE, DEFAULT_CALENDAR_TYPE)

    if calendar_type in (CALENDAR_TYPE_ORTHODOX, CALENDAR_TYPE_BOTH):
        api = CalendarOrtodoxAPI(session)
        try:
            calendar_data = await api.get_year_calendar()
            if not calendar_data:
                raise ValueError("No Orthodox calendar data received")
        except Exception as err:
            _LOGGER.error("Failed to fetch Orthodox calendar data: %s", err)
            raise

    if calendar_type in (CALENDAR_TYPE_CATHOLIC, CALENDAR_TYPE_BOTH):
        api = CatholicCalendarAPI(session)
        try:
            calendar_data = await api.get_year_calendar()
            if not calendar_data:
                raise ValueError("No Catholic calendar data received")
        except Exception as err:
            _LOGGER.error("Failed to fetch Catholic calendar data: %s", err)
            raise

    title = CALENDAR_TYPE_OPTIONS.get(calendar_type, "Calendar Ortodox")
    return {"title": title}


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
                calendar_type = user_input.get(
                    CONF_CALENDAR_TYPE, DEFAULT_CALENDAR_TYPE
                )
                unique_id = f"calendar_{calendar_type}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
