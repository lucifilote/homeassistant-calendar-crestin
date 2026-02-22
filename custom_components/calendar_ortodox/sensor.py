"""Sensor platform for Calendar Ortodox integration."""
from __future__ import annotations

from datetime import date
import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import CalendarOrtodoxDataUpdateCoordinator
from .const import (
    ATTR_DAY_OF_WEEK,
    ATTR_FASTING,
    ATTR_FASTING_DESCRIPTION,
    ATTR_FEAST_DAY,
    ATTR_FEAST_LEVEL,
    ATTR_LITURGICAL_INFO,
    ATTR_MOON_PHASE,
    ATTR_READINGS,
    ATTR_SAINTS,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Calendar Ortodox sensor platform."""
    coordinator: CalendarOrtodoxDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            TodaySaintsSensor(coordinator, entry),
            NextFeastDaySensor(coordinator, entry),
        ],
        True,
    )


class TodaySaintsSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing today's saints and information."""

    def __init__(
        self,
        coordinator: CalendarOrtodoxDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Sfântul Zilei"
        self._attr_unique_id = f"{entry.entry_id}_today_saints"
        self._attr_icon = "mdi:calendar-star"

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        today = date.today()
        calendar_data = self.coordinator.data.get("calendar", {})
        month_data = calendar_data.get(today.month, [])
        
        for day_info in month_data:
            if day_info.date == today:
                return day_info.saints
        
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        today = date.today()
        calendar_data = self.coordinator.data.get("calendar", {})
        month_data = calendar_data.get(today.month, [])
        
        for day_info in month_data:
            if day_info.date == today:
                attrs = {
                    ATTR_DAY_OF_WEEK: day_info.day_of_week,
                    ATTR_FEAST_DAY: day_info.feast_day,
                    ATTR_FEAST_LEVEL: day_info.feast_level,
                }
                
                if day_info.fasting_info:
                    attrs[ATTR_FASTING] = True
                    attrs[ATTR_FASTING_DESCRIPTION] = " | ".join(day_info.fasting_info)
                else:
                    attrs[ATTR_FASTING] = False
                
                if day_info.moon_phase:
                    attrs[ATTR_MOON_PHASE] = day_info.moon_phase
                
                if day_info.sunday_title:
                    attrs[ATTR_LITURGICAL_INFO] = day_info.sunday_title
                
                if day_info.sunday_readings:
                    attrs[ATTR_READINGS] = day_info.sunday_readings
                
                return attrs
        
        return {}


class NextFeastDaySensor(CoordinatorEntity, SensorEntity):
    """Sensor showing the next upcoming feast day."""

    def __init__(
        self,
        coordinator: CalendarOrtodoxDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Următoarea Sărbătoare"
        self._attr_unique_id = f"{entry.entry_id}_next_feast"
        self._attr_icon = "mdi:calendar-star"

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        from datetime import timedelta
        
        today = date.today()
        calendar_data = self.coordinator.data.get("calendar", {})
        
        # Look ahead for the next feast day
        current_date = today
        for _ in range(365):
            month_data = calendar_data.get(current_date.month, [])
            
            for day_info in month_data:
                if day_info.date == current_date and day_info.feast_day:
                    if current_date == today:
                        # Skip today, look for next one
                        current_date += timedelta(days=1)
                        break
                    return day_info.saints
            
            current_date += timedelta(days=1)
            
            # Stop if we've moved to next year
            if current_date.year != today.year:
                break
        
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        from datetime import timedelta
        
        today = date.today()
        calendar_data = self.coordinator.data.get("calendar", {})
        
        # Look ahead for the next feast day
        current_date = today
        for _ in range(365):
            month_data = calendar_data.get(current_date.month, [])
            
            for day_info in month_data:
                if day_info.date == current_date and day_info.feast_day:
                    if current_date == today:
                        # Skip today, look for next one
                        current_date += timedelta(days=1)
                        break
                    
                    days_until = (day_info.date - today).days
                    
                    return {
                        "date": day_info.date.isoformat(),
                        "days_until": days_until,
                        ATTR_FEAST_LEVEL: day_info.feast_level,
                        ATTR_DAY_OF_WEEK: day_info.day_of_week,
                    }
            
            current_date += timedelta(days=1)
            
            if current_date.year != today.year:
                break
        
        return {}
