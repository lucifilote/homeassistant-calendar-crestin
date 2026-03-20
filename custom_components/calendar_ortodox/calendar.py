"""Calendar platform for Calendar Ortodox integration."""

from __future__ import annotations

from datetime import date, datetime, timedelta
import logging
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import CalendarDataUpdateCoordinator
from .api import (
    CatholicCalendarDay,
    OrthodoxCalendarDay,
    CATHOLIC_FEAST_LEVEL_FEAST,
    CATHOLIC_FEAST_LEVEL_SOLEMNITY,
)
from .const import (
    ATTR_COMMENTS,
    ATTR_FASTING,
    ATTR_FASTING_DESCRIPTION,
    ATTR_FEAST_DAY,
    ATTR_FEAST_LEVEL,
    ATTR_READINGS,
    ATTR_SAINTS,
    CALENDAR_TYPE_BOTH,
    CALENDAR_TYPE_CATHOLIC,
    CALENDAR_TYPE_ORTHODOX,
    CONF_CALENDAR_TYPE,
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
    _LOGGER.info("Setting up Calendar Ortodox calendar platform")

    try:
        coordinator: CalendarDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
        calendar_type = entry.data.get(CONF_CALENDAR_TYPE, CALENDAR_TYPE_ORTHODOX)

        calendars = []

        if calendar_type in (CALENDAR_TYPE_ORTHODOX, CALENDAR_TYPE_BOTH):
            calendars.append(OrthodoxCalendar(coordinator, entry))
            calendars.append(OrthodoxFeastDaysCalendar(coordinator, entry))

        if calendar_type in (CALENDAR_TYPE_CATHOLIC, CALENDAR_TYPE_BOTH):
            calendars.append(CatholicCalendar(coordinator, entry))
            calendars.append(CatholicFeastDaysCalendar(coordinator, entry))

        _LOGGER.info("Adding %d calendar entities", len(calendars))
        async_add_entities(calendars, True)
        _LOGGER.info("Calendar entities added successfully")

    except Exception as err:
        _LOGGER.error("Error setting up calendar platform: %s", err, exc_info=True)


class OrthodoxCalendar(CoordinatorEntity, CalendarEntity):
    """Representation of the full Orthodox Calendar."""

    def __init__(
        self,
        coordinator: CalendarDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the calendar."""
        super().__init__(coordinator)
        self._attr_name = "Calendar Ortodox"
        self._attr_unique_id = f"{entry.entry_id}_orthodox_calendar"
        self._attr_has_entity_name = False
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

        calendar_data = self.coordinator.data.get("orthodox", {})

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

        today = date.today()
        calendar_data = self.coordinator.data.get("orthodox", {})
        month_data = calendar_data.get(today.month, [])

        for day_info in month_data:
            if day_info.date == today:
                self._event = self._create_event(day_info)
                break

    def _create_event(self, day_info: OrthodoxCalendarDay) -> CalendarEvent:
        """Create a calendar event from day info."""
        include_fasting = self._entry.data.get(CONF_INCLUDE_FASTING, True)
        include_readings = self._entry.data.get(CONF_INCLUDE_READINGS, True)

        summary = day_info.saints

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

        start = dt_util.start_of_local_day(
            datetime.combine(day_info.date, datetime.min.time())
        )
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
        calendar_data = self.coordinator.data.get("orthodox", {})
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
        coordinator: CalendarDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the calendar."""
        super().__init__(coordinator)
        self._attr_name = "Calendar Ortodox - Sărbători"
        self._attr_unique_id = f"{entry.entry_id}_orthodox_feast_days"
        self._attr_has_entity_name = False
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

        calendar_data = self.coordinator.data.get("orthodox", {})

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

        today = date.today()
        calendar_data = self.coordinator.data.get("orthodox", {})

        current_date = today
        for _ in range(365):
            month_data = calendar_data.get(current_date.month, [])

            for day_info in month_data:
                if day_info.date == current_date and day_info.feast_day:
                    self._event = self._create_event(day_info)
                    return

            current_date += timedelta(days=1)

            if current_date.year != today.year:
                break

    def _create_event(self, day_info: OrthodoxCalendarDay) -> CalendarEvent:
        """Create a calendar event from day info."""
        if day_info.feast_level == FEAST_LEVEL_GREAT:
            summary = f"🌟 {day_info.saints}"
        elif day_info.feast_level == FEAST_LEVEL_MAJOR:
            summary = f"✝️ {day_info.saints}"
        else:
            summary = day_info.saints

        description_parts = []

        if day_info.fasting_info:
            fasting_text = " | ".join(day_info.fasting_info)
            description_parts.append(f"Post: {fasting_text}")

        if day_info.is_sunday and day_info.sunday_title:
            description_parts.append(f"\n{day_info.sunday_title}")

        description = "\n".join(description_parts) if description_parts else summary

        start = dt_util.start_of_local_day(
            datetime.combine(day_info.date, datetime.min.time())
        )
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

        event_date = self._event.start.date()
        calendar_data = self.coordinator.data.get("orthodox", {})
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


class CatholicCalendar(CoordinatorEntity, CalendarEntity):
    """Representation of the full Catholic Calendar."""

    def __init__(
        self,
        coordinator: CalendarDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the calendar."""
        super().__init__(coordinator)
        self._attr_name = "Calendar Romano-Catolic"
        self._attr_unique_id = f"{entry.entry_id}_catholic_calendar"
        self._attr_has_entity_name = False
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

        calendar_data = self.coordinator.data.get("catholic", {})

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

        today = date.today()
        calendar_data = self.coordinator.data.get("catholic", {})
        month_data = calendar_data.get(today.month, [])

        for day_info in month_data:
            if day_info.date == today:
                self._event = self._create_event(day_info)
                break

    def _create_event(self, day_info: CatholicCalendarDay) -> CalendarEvent:
        """Create a calendar event from day info."""
        summary = day_info.saints

        description_parts = []

        if day_info.feast_name:
            if day_info.feast_level == CATHOLIC_FEAST_LEVEL_SOLEMNITY:
                description_parts.append("🌟 Solenmitate")
            elif day_info.feast_level == CATHOLIC_FEAST_LEVEL_FEAST:
                description_parts.append("✝️ Sărbătoare")

        description = "\n".join(description_parts) if description_parts else summary

        start = dt_util.start_of_local_day(
            datetime.combine(day_info.date, datetime.min.time())
        )
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
        calendar_data = self.coordinator.data.get("catholic", {})
        month_data = calendar_data.get(today.month, [])

        day_info = None
        for info in month_data:
            if info.date == today:
                day_info = info
                break

        if not day_info:
            return {}

        return {
            ATTR_SAINTS: day_info.saints,
            ATTR_FEAST_DAY: day_info.is_feast,
            ATTR_FEAST_LEVEL: day_info.feast_level,
        }


class CatholicFeastDaysCalendar(CoordinatorEntity, CalendarEntity):
    """Representation of Catholic Feast Days only."""

    def __init__(
        self,
        coordinator: CalendarDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the calendar."""
        super().__init__(coordinator)
        self._attr_name = "Calendar Romano-Catolic - Sărbători"
        self._attr_unique_id = f"{entry.entry_id}_catholic_feast_days"
        self._attr_has_entity_name = False
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

        calendar_data = self.coordinator.data.get("catholic", {})

        current_date = start_date.date()
        end = end_date.date()

        while current_date <= end:
            month_data = calendar_data.get(current_date.month, [])

            for day_info in month_data:
                if day_info.date == current_date and day_info.is_feast:
                    event = self._create_event(day_info)
                    if event:
                        events.append(event)
                    break

            current_date += timedelta(days=1)

        return events

    async def async_update(self) -> None:
        """Update the entity."""
        await super().async_update()

        today = date.today()
        calendar_data = self.coordinator.data.get("catholic", {})

        current_date = today
        for _ in range(365):
            month_data = calendar_data.get(current_date.month, [])

            for day_info in month_data:
                if day_info.date == current_date and day_info.is_feast:
                    self._event = self._create_event(day_info)
                    return

            current_date += timedelta(days=1)

            if current_date.year != today.year:
                break

    def _create_event(self, day_info: CatholicCalendarDay) -> CalendarEvent:
        """Create a calendar event from day info."""
        if day_info.feast_level == CATHOLIC_FEAST_LEVEL_SOLEMNITY:
            summary = f"🌟 {day_info.saints}"
        elif day_info.feast_level == CATHOLIC_FEAST_LEVEL_FEAST:
            summary = f"✝️ {day_info.saints}"
        else:
            summary = day_info.saints

        description = day_info.feast_name or summary

        start = dt_util.start_of_local_day(
            datetime.combine(day_info.date, datetime.min.time())
        )
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

        event_date = self._event.start.date()
        calendar_data = self.coordinator.data.get("catholic", {})
        month_data = calendar_data.get(event_date.month, [])

        day_info = None
        for info in month_data:
            if info.date == event_date:
                day_info = info
                break

        if not day_info:
            return {}

        return {
            ATTR_SAINTS: day_info.saints,
            ATTR_FEAST_LEVEL: day_info.feast_level,
        }
