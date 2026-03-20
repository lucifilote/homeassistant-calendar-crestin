"""Sensor platform for Calendar Ortodox integration."""

from __future__ import annotations

from datetime import date, timedelta
import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import CalendarDataUpdateCoordinator
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
    CALENDAR_TYPE_BOTH,
    CALENDAR_TYPE_CATHOLIC,
    CALENDAR_TYPE_ORTHODOX,
    CONF_CALENDAR_TYPE,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Calendar Ortodox sensor platform."""
    coordinator: CalendarDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    calendar_type = entry.data.get(CONF_CALENDAR_TYPE, CALENDAR_TYPE_ORTHODOX)

    sensors = []

    if calendar_type in (CALENDAR_TYPE_ORTHODOX, CALENDAR_TYPE_BOTH):
        sensors.append(OrthodoxTodaySaintsSensor(coordinator, entry))
        sensors.append(OrthodoxNextFeastDaySensor(coordinator, entry))

    if calendar_type in (CALENDAR_TYPE_CATHOLIC, CALENDAR_TYPE_BOTH):
        sensors.append(CatholicTodaySaintsSensor(coordinator, entry))
        sensors.append(CatholicNextFeastDaySensor(coordinator, entry))

    async_add_entities(sensors, True)


class OrthodoxTodaySaintsSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing today's Orthodox saints and information."""

    def __init__(
        self,
        coordinator: CalendarDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Sfântul Zilei - Ortodox"
        self._attr_unique_id = f"{entry.entry_id}_orthodox_today_saints"
        self._attr_icon = "mdi:calendar-star"

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        today = date.today()
        calendar_data = self.coordinator.data.get("orthodox", {})
        month_data = calendar_data.get(today.month, [])

        for day_info in month_data:
            if day_info.date == today:
                return day_info.saints

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        today = date.today()
        calendar_data = self.coordinator.data.get("orthodox", {})
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


class OrthodoxNextFeastDaySensor(CoordinatorEntity, SensorEntity):
    """Sensor showing the next upcoming Orthodox feast day."""

    def __init__(
        self,
        coordinator: CalendarDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Următoarea Sărbătoare - Ortodox"
        self._attr_unique_id = f"{entry.entry_id}_orthodox_next_feast"
        self._attr_icon = "mdi:calendar-star"

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        today = date.today()
        calendar_data = self.coordinator.data.get("orthodox", {})

        current_date = today
        for _ in range(365):
            month_data = calendar_data.get(current_date.month, [])

            for day_info in month_data:
                if day_info.date == current_date and day_info.feast_day:
                    if current_date == today:
                        current_date += timedelta(days=1)
                        break
                    return day_info.saints

            current_date += timedelta(days=1)

            if current_date.year != today.year:
                break

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        today = date.today()
        calendar_data = self.coordinator.data.get("orthodox", {})

        current_date = today
        for _ in range(365):
            month_data = calendar_data.get(current_date.month, [])

            for day_info in month_data:
                if day_info.date == current_date and day_info.feast_day:
                    if current_date == today:
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


class CatholicTodaySaintsSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing today's Catholic saints and information."""

    def __init__(
        self,
        coordinator: CalendarDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Sfântul Zilei - Romano-Catolic"
        self._attr_unique_id = f"{entry.entry_id}_catholic_today_saints"
        self._attr_icon = "mdi:calendar-star"

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        today = date.today()
        calendar_data = self.coordinator.data.get("catholic", {})
        month_data = calendar_data.get(today.month, [])

        for day_info in month_data:
            if day_info.date == today:
                return day_info.saints

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        today = date.today()
        calendar_data = self.coordinator.data.get("catholic", {})
        month_data = calendar_data.get(today.month, [])

        for day_info in month_data:
            if day_info.date == today:
                return {
                    ATTR_DAY_OF_WEEK: day_info.day_of_week,
                    ATTR_FEAST_DAY: day_info.is_feast,
                    ATTR_FEAST_LEVEL: day_info.feast_level,
                }

        return {}


class CatholicNextFeastDaySensor(CoordinatorEntity, SensorEntity):
    """Sensor showing the next upcoming Catholic feast day."""

    def __init__(
        self,
        coordinator: CalendarDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Următoarea Sărbătoare - Romano-Catolic"
        self._attr_unique_id = f"{entry.entry_id}_catholic_next_feast"
        self._attr_icon = "mdi:calendar-star"

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        today = date.today()
        calendar_data = self.coordinator.data.get("catholic", {})

        current_date = today
        for _ in range(365):
            month_data = calendar_data.get(current_date.month, [])

            for day_info in month_data:
                if day_info.date == current_date and day_info.is_feast:
                    if current_date == today:
                        current_date += timedelta(days=1)
                        break
                    return day_info.saints

            current_date += timedelta(days=1)

            if current_date.year != today.year:
                break

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        today = date.today()
        calendar_data = self.coordinator.data.get("catholic", {})

        current_date = today
        for _ in range(365):
            month_data = calendar_data.get(current_date.month, [])

            for day_info in month_data:
                if day_info.date == current_date and day_info.is_feast:
                    if current_date == today:
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
