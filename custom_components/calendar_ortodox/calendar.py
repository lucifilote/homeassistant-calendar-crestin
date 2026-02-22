"""Calendar platform for Calendar Ortodox integration."""
from __future__ import annotations

from datetime import date, datetime, timedelta
import logging
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import CalendarOrtodoxDataUpdateCoordinator
from .api import OrthodoxCalendarDay
from .const import (
    ATTR_COMMENTS,
    ATTR_FASTING,
    ATTR_FASTING_DESCRIPTION,
    ATTR_FEAST_DAY,
    ATTR_FEAST_LEVEL,
    ATTR_READINGS,
    ATTR_SAINTS,
    CONF_INCLUDE_FASTING,
    CONF_INCLUDE_READINGS,
    DOMAIN,
    FEAST_LEVEL_GREAT,
    FEAST_LEVEL_MAJOR,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Calendar Ortodox calendar platform."""
    coordinator: CalendarOrtodoxDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            OrthodoxCalendar(coordinator, entry),
            OrthodoxFeastDaysCalendar(coordinator, entry),
        ],
        True,
    )


class OrthodoxCalendar(CoordinatorEntity, CalendarEntity):
    """Representation of the full Orthodox Calendar."""

    def __init__(
        self,
        coordinator: CalendarOrtodoxDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the calendar."""
        super().__init__(coordinator)
        self._attr_name = "Calendar Ortodox"
        self._attr_unique_id = f"{entry.entry_id}_calendar"
        self._entry = entry
        self._event: CalendarEvent | None = None

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        return self._event

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Get all events in a specific time frame."""
        events = []
        
        calendar_data = self.coordinator.data.get("calendar", {})
        
        current_date = start_date.date()
        end = end_date.date()
        
        while current_date <= end:
            month_data = calendar_data.get(current_date.month, [])
            
            for day_info in month_data:
                if day_info.date == current_date:
                    event = self._create_event(day_info)
                    if event:
                        events.append(event)
                    break
            
            current_date += timedelta(days=1)
        
        return events

    async def async_update(self) -> None:
        """Update the entity."""
        await super().async_update()
        
        # Get today's event
        today = date.today()
        calendar_data = self.coordinator.data.get("calendar", {})
        month_data = calendar_data.get(today.month, [])
        
        for day_info in month_data:
            if day_info.date == today:
                self._event = self._create_event(day_info)
                break

    def _create_event(self, day_info: OrthodoxCalendarDay) -> CalendarEvent:
        """Create a calendar event from day info."""
        include_fasting = self._entry.data.get(CONF_INCLUDE_FASTING, True)
        include_readings = self._entry.data.get(CONF_INCLUDE_READINGS, True)
        
        # Build event summary
        summary = day_info.saints
        
        # Build description
        description_parts = []
        
        if day_info.feast_day:
            if day_info.feast_level == FEAST_LEVEL_GREAT:
                description_parts.append("🌟 Praznic Mare")
            elif day_info.feast_level == FEAST_LEVEL_MAJOR:
                description_parts.append("✝️ Sărbătoare")
        
        if include_fasting and day_info.fasting_info:
            fasting_text = " | ".join(day_info.fasting_info)
            description_parts.append(f"Post: {fasting_text}")
        
        if day_info.is_sunday and day_info.sunday_title:
            description_parts.append(f"\n{day_info.sunday_title}")
        
        if include_readings and day_info.sunday_readings:
            readings = day_info.sunday_readings
            if "apostle" in readings:
                description_parts.append(f"\n{readings['apostle']}")
            if "gospel" in readings:
                description_parts.append(f"{readings['gospel']}")
        
        description = "\n".join(description_parts) if description_parts else summary
        
        # Create event - all-day events
        start = datetime.combine(day_info.date, datetime.min.time())
        end = start + timedelta(days=1)
        
        return CalendarEvent(
            start=start,
            end=end,
            summary=summary,
            description=description,
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        if not self._event:
            return {}
        
        today = date.today()
        calendar_data = self.coordinator.data.get("calendar", {})
        month_data = calendar_data.get(today.month, [])
        
        day_info = None
        for info in month_data:
            if info.date == today:
                day_info = info
                break
        
        if not day_info:
            return {}
        
        attrs = {
            ATTR_SAINTS: day_info.saints,
            ATTR_FEAST_DAY: day_info.feast_day,
            ATTR_FEAST_LEVEL: day_info.feast_level,
        }
        
        if day_info.fasting_info:
            attrs[ATTR_FASTING] = True
            attrs[ATTR_FASTING_DESCRIPTION] = " | ".join(day_info.fasting_info)
        else:
            attrs[ATTR_FASTING] = False
        
        if day_info.sunday_readings:
            attrs[ATTR_READINGS] = day_info.sunday_readings
        
        if day_info.sunday_title:
            attrs[ATTR_COMMENTS] = day_info.sunday_title
        
        return attrs


class OrthodoxFeastDaysCalendar(CoordinatorEntity, CalendarEntity):
    """Representation of Orthodox Feast Days (sărbători) only."""

    def __init__(
        self,
        coordinator: CalendarOrtodoxDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the calendar."""
        super().__init__(coordinator)
        self._attr_name = "Calendar Ortodox - Sărbători"
        self._attr_unique_id = f"{entry.entry_id}_feast_days"
        self._entry = entry
        self._event: CalendarEvent | None = None

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming feast day."""
        return self._event

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Get all feast day events in a specific time frame."""
        events = []
        
        calendar_data = self.coordinator.data.get("calendar", {})
        
        current_date = start_date.date()
        end = end_date.date()
        
        while current_date <= end:
            month_data = calendar_data.get(current_date.month, [])
            
            for day_info in month_data:
                if day_info.date == current_date and day_info.feast_day:
                    event = self._create_event(day_info)
                    if event:
                        events.append(event)
                    break
            
            current_date += timedelta(days=1)
        
        return events

    async def async_update(self) -> None:
        """Update the entity."""
        await super().async_update()
        
        # Get next feast day
        today = date.today()
        calendar_data = self.coordinator.data.get("calendar", {})
        
        # Look for next feast day
        current_date = today
        for _ in range(365):  # Look ahead up to a year
            month_data = calendar_data.get(current_date.month, [])
            
            for day_info in month_data:
                if day_info.date == current_date and day_info.feast_day:
                    self._event = self._create_event(day_info)
                    return
            
            current_date += timedelta(days=1)
            
            # If we've moved to next year, we need to fetch that year's data
            if current_date.year != today.year:
                break

    def _create_event(self, day_info: OrthodoxCalendarDay) -> CalendarEvent:
        """Create a calendar event from day info."""
        # Build event summary with feast indicator
        if day_info.feast_level == FEAST_LEVEL_GREAT:
            summary = f"🌟 {day_info.saints}"
        elif day_info.feast_level == FEAST_LEVEL_MAJOR:
            summary = f"✝️ {day_info.saints}"
        else:
            summary = day_info.saints
        
        # Build description
        description_parts = []
        
        if day_info.fasting_info:
            fasting_text = " | ".join(day_info.fasting_info)
            description_parts.append(f"Post: {fasting_text}")
        
        if day_info.is_sunday and day_info.sunday_title:
            description_parts.append(f"\n{day_info.sunday_title}")
        
        description = "\n".join(description_parts) if description_parts else summary
        
        # Create event - all-day events
        start = datetime.combine(day_info.date, datetime.min.time())
        end = start + timedelta(days=1)
        
        return CalendarEvent(
            start=start,
            end=end,
            summary=summary,
            description=description,
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        if not self._event:
            return {}
        
        # Extract date from event
        event_date = self._event.start.date()
        calendar_data = self.coordinator.data.get("calendar", {})
        month_data = calendar_data.get(event_date.month, [])
        
        day_info = None
        for info in month_data:
            if info.date == event_date:
                day_info = info
                break
        
        if not day_info:
            return {}
        
        attrs = {
            ATTR_SAINTS: day_info.saints,
            ATTR_FEAST_LEVEL: day_info.feast_level,
        }
        
        if day_info.fasting_info:
            attrs[ATTR_FASTING] = True
            attrs[ATTR_FASTING_DESCRIPTION] = " | ".join(day_info.fasting_info)
        
        return attrs
