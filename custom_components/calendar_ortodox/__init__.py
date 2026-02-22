"""The Calendar Ortodox integration."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CalendarOrtodoxAPI
from .const import DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.CALENDAR, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Calendar Ortodox from a config entry."""
    session = async_get_clientsession(hass)
    api = CalendarOrtodoxAPI(session)

    coordinator = CalendarOrtodoxDataUpdateCoordinator(hass, api)

    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        raise ConfigEntryNotReady(f"Failed to fetch calendar data: {err}") from err

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class CalendarOrtodoxDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Calendar Ortodox data."""

    def __init__(self, hass: HomeAssistant, api: CalendarOrtodoxAPI) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.api = api

    async def _async_update_data(self) -> dict:
        """Fetch data from API."""
        try:
            # Get the full year calendar
            calendar_data = await self.api.get_year_calendar()
            
            _LOGGER.debug("Successfully fetched calendar data with %d months", len(calendar_data))
            
            return {
                "calendar": calendar_data,
                "api": self.api,
            }
        except Exception as err:
            _LOGGER.error("Error fetching calendar data: %s", err)
            raise UpdateFailed(f"Error communicating with API: {err}") from err
