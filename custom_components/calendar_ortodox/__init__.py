"""The Calendar Ortodox integration."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CalendarOrtodoxAPI, CatholicCalendarAPI
from .const import (
    CALENDAR_TYPE_BOTH,
    CALENDAR_TYPE_CATHOLIC,
    CALENDAR_TYPE_ORTHODOX,
    CONF_CALENDAR_TYPE,
    DEFAULT_CALENDAR_TYPE,
    DOMAIN,
    SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.CALENDAR, Platform.SENSOR]

SERVICE_REFRESH_CALENDAR = "refresh_calendar"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Calendar Ortodox from a config entry."""
    session = async_get_clientsession(hass)
    calendar_type = entry.data.get(CONF_CALENDAR_TYPE, DEFAULT_CALENDAR_TYPE)

    apis = {}

    if calendar_type in (CALENDAR_TYPE_ORTHODOX, CALENDAR_TYPE_BOTH):
        apis[CALENDAR_TYPE_ORTHODOX] = CalendarOrtodoxAPI(session)

    if calendar_type in (CALENDAR_TYPE_CATHOLIC, CALENDAR_TYPE_BOTH):
        apis[CALENDAR_TYPE_CATHOLIC] = CatholicCalendarAPI(session)

    coordinator = CalendarDataUpdateCoordinator(hass, apis, calendar_type)

    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        raise ConfigEntryNotReady(f"Failed to fetch calendar data: {err}") from err

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def handle_refresh_calendar(call: ServiceCall) -> None:
        """Handle the refresh_calendar service call."""
        _LOGGER.info("Manual calendar refresh requested")
        await coordinator.async_request_refresh()
        _LOGGER.info("Calendar refresh completed")

    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH_CALENDAR,
        handle_refresh_calendar,
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_REFRESH_CALENDAR)

    return unload_ok


class CalendarDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching calendar data for both Orthodox and Catholic."""

    def __init__(
        self,
        hass: HomeAssistant,
        apis: dict[str, CalendarOrtodoxAPI | CatholicCalendarAPI],
        calendar_type: str,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.apis = apis
        self.calendar_type = calendar_type

    async def _async_update_data(self) -> dict:
        """Fetch data from API(s)."""
        result = {"calendar_type": self.calendar_type}

        try:
            if CALENDAR_TYPE_ORTHODOX in self.apis:
                _LOGGER.debug("Fetching Orthodox calendar")
                result["orthodox"] = await self.apis[
                    CALENDAR_TYPE_ORTHODOX
                ].get_year_calendar()

            if CALENDAR_TYPE_CATHOLIC in self.apis:
                _LOGGER.debug("Fetching Catholic calendar")
                result["catholic"] = await self.apis[
                    CALENDAR_TYPE_CATHOLIC
                ].get_year_calendar()

            _LOGGER.debug("Successfully fetched calendar data")
            return result

        except Exception as err:
            _LOGGER.error("Error fetching calendar data: %s", err)
            raise UpdateFailed(f"Error communicating with API: {err}") from err
