"""API client for Calendar Ortodox."""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Any

from aiohttp import ClientSession
from bs4 import BeautifulSoup

from .const import (
    BASE_URL,
    CATHOLIC_BASE_URL,
    CSS_CLASS_DUMINICA,
    CSS_CLASS_SARBATOARE,
    FEAST_LEVEL_GREAT,
    FEAST_LEVEL_MAJOR,
    FEAST_LEVEL_NORMAL,
)

_LOGGER = logging.getLogger(__name__)

MONTHS_RO = {
    1: "ianuarie",
    2: "februarie",
    3: "martie",
    4: "aprilie",
    5: "mai",
    6: "iunie",
    7: "iulie",
    8: "august",
    9: "septembrie",
    10: "octombrie",
    11: "noiembrie",
    12: "decembrie",
}


class LiturgicalDay(ABC):
    """Abstract base class for liturgical calendar days."""

    @property
    @abstractmethod
    def date(self) -> date:
        """Return the date object."""

    @property
    @abstractmethod
    def saints(self) -> str:
        """Return saints commemorated."""

    @property
    @abstractmethod
    def is_feast(self) -> bool:
        """Return True if this is a feast day."""

    @property
    @abstractmethod
    def feast_level(self) -> str:
        """Return feast level."""

    @property
    @abstractmethod
    def is_sunday(self) -> bool:
        """Return True if this is a Sunday."""


class OrthodoxCalendarDay(LiturgicalDay):
    """Represents a single day in the Orthodox calendar."""

    def __init__(
        self,
        day: int,
        month: int,
        year: int,
        day_of_week: str,
        saints: str,
        feast_day: bool = False,
        feast_level: str = FEAST_LEVEL_NORMAL,
        fasting_info: list[str] | None = None,
        moon_phase: str | None = None,
        is_sunday: bool = False,
        sunday_title: str | None = None,
        sunday_readings: dict[str, str] | None = None,
    ) -> None:
        """Initialize a calendar day."""
        self.day = day
        self.month = month
        self.year = year
        self.day_of_week = day_of_week
        self._saints = saints
        self.feast_day = feast_day
        self._feast_level = feast_level
        self.fasting_info = fasting_info or []
        self.moon_phase = moon_phase
        self._is_sunday = is_sunday
        self.sunday_title = sunday_title
        self.sunday_readings = sunday_readings or {}

    @property
    def date(self) -> date:
        """Return the date object."""
        return date(self.year, self.month, self.day)

    @property
    def saints(self) -> str:
        """Return saints commemorated."""
        return self._saints

    @property
    def is_feast(self) -> bool:
        """Return True if this is a feast day."""
        return self.feast_day

    @property
    def feast_level(self) -> str:
        """Return feast level."""
        return self._feast_level

    @property
    def is_sunday(self) -> bool:
        """Return True if this is a Sunday."""
        return self._is_sunday

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "date": self.date.isoformat(),
            "day_of_week": self.day_of_week,
            "saints": self.saints,
            "feast_day": self.feast_day,
            "feast_level": self.feast_level,
            "fasting_info": self.fasting_info,
            "moon_phase": self.moon_phase,
            "is_sunday": self.is_sunday,
            "sunday_title": self.sunday_title,
            "sunday_readings": self.sunday_readings,
        }


class CalendarOrtodoxAPI:
    """API client for noutati-ortodoxe.ro calendar."""

    def __init__(self, session: ClientSession, year: int | None = None) -> None:
        """Initialize the API client."""
        self._session = session
        self._year = year or datetime.now().year
        self._cache: dict[int, dict[int, list[OrthodoxCalendarDay]]] = {}

    async def get_year_calendar(
        self, year: int | None = None
    ) -> dict[int, list[OrthodoxCalendarDay]]:
        """Get the full year calendar data."""
        target_year = year or self._year

        if target_year in self._cache:
            _LOGGER.debug("Returning cached calendar for year %s", target_year)
            return self._cache[target_year]

        url = BASE_URL
        if target_year != datetime.now().year:
            url = f"{BASE_URL}?year={target_year}"

        _LOGGER.debug("Fetching calendar from %s", url)

        try:
            async with self._session.get(url, timeout=30) as response:
                response.raise_for_status()
                html = await response.text()
        except Exception as err:
            _LOGGER.error("Failed to fetch calendar: %s", err)
            raise

        calendar_data = self._parse_calendar_html(html, target_year)
        self._cache[target_year] = calendar_data

        return calendar_data

    async def get_month_calendar(
        self, year: int, month: int
    ) -> list[OrthodoxCalendarDay]:
        """Get calendar data for a specific month."""
        year_calendar = await self.get_year_calendar(year)
        return year_calendar.get(month, [])

    async def get_day_info(self, target_date: date) -> OrthodoxCalendarDay | None:
        """Get calendar info for a specific date."""
        month_calendar = await self.get_month_calendar(
            target_date.year, target_date.month
        )

        for day_info in month_calendar:
            if day_info.day == target_date.day:
                return day_info

        return None

    def _parse_calendar_html(
        self, html: str, year: int
    ) -> dict[int, list[OrthodoxCalendarDay]]:
        """Parse the HTML calendar and extract data."""
        soup = BeautifulSoup(html, "lxml")
        calendar_data: dict[int, list[OrthodoxCalendarDay]] = {}

        # Find all month calendars
        month_divs = soup.find_all("div", class_="calendar")

        for month_idx, month_div in enumerate(month_divs, start=1):
            month_data = []

            # Find all day rows (skip header rows)
            rows = month_div.find_all("tr")

            for row in rows:
                # Skip if this is the month header row
                if row.find("td", class_="luna"):
                    continue

                # Skip if this is a Sunday reading row (duminica)
                if "duminica" in row.get("class", []):
                    # This row contains Sunday readings, we'll handle it separately
                    continue

                day_cell = row.find("td", class_="ziua")
                day_of_week_cell = row.find("td", class_="sapt")

                # Find the third cell (content cell) - it has no class attribute
                all_cells = row.find_all("td", recursive=False)
                content_cell = None
                if len(all_cells) >= 3:
                    # Third cell is the content (index 2)
                    content_cell = all_cells[2]

                if not day_cell or not day_of_week_cell or not content_cell:
                    continue

                try:
                    day_num = int(day_cell.get_text(strip=True))
                except (ValueError, AttributeError):
                    continue

                day_of_week = day_of_week_cell.get_text(strip=True)

                # Check if it's a feast day (sarbatoare)
                row_classes = row.get("class", [])
                is_feast = CSS_CLASS_SARBATOARE in row_classes
                is_sunday = CSS_CLASS_DUMINICA in row_classes or day_of_week == "D"

                # Extract saints and determine feast level
                saints_link = content_cell.find("a", class_="sinaxar")
                if saints_link:
                    saints_text = saints_link.get_text(strip=True)

                    # Log for debugging
                    if day_num == 25 and month_idx == 3:
                        _LOGGER.info(
                            "March 25 - Found sinaxar link with text: %r", saints_text
                        )

                    # Determine feast level by counting crosses/daggers
                    feast_level = FEAST_LEVEL_NORMAL
                    if is_feast or "†" in saints_text or "(†)" in saints_text:
                        if "(†)" in saints_text:
                            feast_level = FEAST_LEVEL_GREAT
                        elif "†" in saints_text:
                            feast_level = FEAST_LEVEL_MAJOR
                        is_feast = True
                else:
                    # No sinaxar link - extract text more carefully
                    if day_num == 25 and month_idx == 3:
                        _LOGGER.warning(
                            "March 25 - NO sinaxar link found! Content cell HTML: %s",
                            str(content_cell)[:500],
                        )

                    # First, try to get direct text nodes (excluding spans and other elements)
                    saints_text_parts = []
                    for element in content_cell.children:
                        if isinstance(element, str):
                            text = element.strip()
                            if text:
                                saints_text_parts.append(text)
                        elif element.name == "a":
                            text = element.get_text(strip=True)
                            if text:
                                saints_text_parts.append(text)

                    saints_text = " ".join(saints_text_parts).strip()

                    # If still empty, fall back to getting all text
                    if not saints_text:
                        saints_text = content_cell.get_text(strip=True)

                    feast_level = FEAST_LEVEL_NORMAL

                # Extract fasting info from comments
                fasting_info = []
                comment_spans = content_cell.find_all("span", class_="comentariu")
                for comment in comment_spans:
                    comment_text = comment.get_text(strip=True)
                    if any(
                        keyword in comment_text
                        for keyword in ["Post", "Dezlegare", "pâine", "aliturgică"]
                    ):
                        fasting_info.append(comment_text)

                # Clean up saints_text only if it wasn't from a sinaxar link
                if not saints_link:
                    # Remove fasting comments
                    for fasting in fasting_info:
                        saints_text = saints_text.replace(fasting, "")

                    # Remove standalone numbers (likely day numbers that got included)
                    saints_text = re.sub(
                        r"^\d+\s*", "", saints_text
                    )  # Remove leading numbers
                    saints_text = re.sub(
                        r"\s*\d+$", "", saints_text
                    )  # Remove trailing numbers
                    saints_text = saints_text.strip()

                    # If saints_text is empty or just a number, use a placeholder
                    if not saints_text or saints_text.isdigit():
                        saints_text = f"Ziua {day_num} {MONTHS_RO[month_idx]}"
                        if day_num == 25 and month_idx == 3:
                            _LOGGER.warning(
                                "March 25 - Using placeholder text: %r", saints_text
                            )

                # Log final value for March 25
                if day_num == 25 and month_idx == 3:
                    _LOGGER.info(
                        "March 25 - Final saints_text: %r, feast_day: %s, feast_level: %s",
                        saints_text,
                        is_feast,
                        feast_level,
                    )

                # Extract moon phase
                moon_phase = None
                moon_img = content_cell.find("img")
                if moon_img and moon_img.get("src"):
                    moon_src = moon_img["src"]
                    if "luna-" in moon_src:
                        moon_phase = moon_src.split("/")[-1].replace(".png", "")

                # Handle Sunday readings (look for next row)
                sunday_title = None
                sunday_readings = {}
                if is_sunday:
                    # Find the next row which should be the duminica row
                    next_row = row.find_next_sibling("tr")
                    if next_row and "duminica" in next_row.get("class", []):
                        title_span = next_row.find("span", class_="title")
                        if title_span:
                            sunday_title = title_span.get_text(strip=True)

                        # Get the full text and parse readings
                        readings_text = next_row.get_text(strip=True)
                        if "Ap." in readings_text:
                            parts = readings_text.split(";")
                            for part in parts:
                                if "Ap." in part:
                                    sunday_readings["apostle"] = part.strip()
                                elif "Ev." in part:
                                    sunday_readings["gospel"] = part.strip()

                day_obj = OrthodoxCalendarDay(
                    day=day_num,
                    month=month_idx,
                    year=year,
                    day_of_week=day_of_week,
                    saints=saints_text,
                    feast_day=is_feast,
                    feast_level=feast_level,
                    fasting_info=fasting_info,
                    moon_phase=moon_phase,
                    is_sunday=is_sunday,
                    sunday_title=sunday_title,
                    sunday_readings=sunday_readings,
                )

                month_data.append(day_obj)

            if month_data:
                calendar_data[month_idx] = month_data

        _LOGGER.debug(
            "Parsed %d months of calendar data for year %s", len(calendar_data), year
        )
        return calendar_data


CATHOLIC_FEAST_LEVEL_SOLEMNITY = "solemnity"
CATHOLIC_FEAST_LEVEL_FEAST = "feast"
CATHOLIC_FEAST_LEVEL_MEMORIAL = "memorial"
CATHOLIC_FEAST_LEVEL_OPTIONAL = "optional"


class CatholicCalendarDay(LiturgicalDay):
    """Represents a single day in the Catholic calendar."""

    def __init__(
        self,
        day: int,
        month: int,
        year: int,
        day_of_week: str,
        saints: str,
        feast_name: str | None = None,
        feast_level: str = CATHOLIC_FEAST_LEVEL_OPTIONAL,
        is_sunday: bool = False,
    ) -> None:
        """Initialize a calendar day."""
        self.day = day
        self.month = month
        self.year = year
        self.day_of_week = day_of_week
        self._saints = saints
        self.feast_name = feast_name
        self._feast_level = feast_level
        self._is_sunday = is_sunday

    @property
    def date(self) -> date:
        """Return the date object."""
        return date(self.year, self.month, self.day)

    @property
    def saints(self) -> str:
        """Return saints commemorated."""
        return self._saints

    @property
    def is_feast(self) -> bool:
        """Return True if this is a feast or higher."""
        return self.feast_level in (
            CATHOLIC_FEAST_LEVEL_SOLEMNITY,
            CATHOLIC_FEAST_LEVEL_FEAST,
            CATHOLIC_FEAST_LEVEL_MEMORIAL,
        )

    @property
    def feast_level(self) -> str:
        """Return feast level."""
        return self._feast_level

    @property
    def is_sunday(self) -> bool:
        """Return True if this is a Sunday."""
        return self._is_sunday

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "date": self.date.isoformat(),
            "day_of_week": self.day_of_week,
            "saints": self.saints,
            "feast_name": self.feast_name,
            "feast_level": self.feast_level,
            "is_sunday": self.is_sunday,
        }


class CatholicCalendarAPI:
    """API client for catholica.ro Roman Catholic calendar."""

    def __init__(self, session: ClientSession, year: int | None = None) -> None:
        """Initialize the API client."""
        self._session = session
        self._year = year or datetime.now().year
        self._cache: dict[int, dict[int, list[CatholicCalendarDay]]] = {}

    async def get_year_calendar(
        self, year: int | None = None
    ) -> dict[int, list[CatholicCalendarDay]]:
        """Get the full year calendar data."""
        target_year = year or self._year

        if target_year in self._cache:
            _LOGGER.debug("Returning cached Catholic calendar for year %s", target_year)
            return self._cache[target_year]

        calendar_data: dict[int, list[CatholicCalendarDay]] = {}

        for month in range(1, 13):
            try:
                month_data = await self._fetch_month(target_year, month)
                if month_data:
                    calendar_data[month] = month_data
            except Exception as err:
                _LOGGER.warning("Failed to fetch month %d: %s", month, err)

        self._cache[target_year] = calendar_data
        return calendar_data

    async def _fetch_month(self, year: int, month: int) -> list[CatholicCalendarDay]:
        """Fetch and parse a single month."""
        url = f"{CATHOLIC_BASE_URL}{year}/{month:02d}/"

        try:
            async with self._session.get(url, timeout=30) as response:
                response.raise_for_status()
                html = await response.text()
        except Exception as err:
            _LOGGER.error("Failed to fetch %s: %s", url, err)
            raise

        return self._parse_month_html(html, year, month)

    async def get_month_calendar(
        self, year: int, month: int
    ) -> list[CatholicCalendarDay]:
        """Get calendar data for a specific month."""
        year_calendar = await self.get_year_calendar(year)
        return year_calendar.get(month, [])

    async def get_day_info(self, target_date: date) -> CatholicCalendarDay | None:
        """Get calendar info for a specific date."""
        month_calendar = await self.get_month_calendar(
            target_date.year, target_date.month
        )

        for day_info in month_calendar:
            if day_info.day == target_date.day:
                return day_info

        return None

    def _parse_month_html(
        self, html: str, year: int, month: int
    ) -> list[CatholicCalendarDay]:
        """Parse the HTML calendar and extract data."""
        soup = BeautifulSoup(html, "lxml")
        month_data = []

        page_text = soup.get_text()
        page_text = re.sub(r"\s+", " ", page_text)

        day_pattern = re.compile(
            r"(\d+)\s+([LMJVSD])\s+(.+?)(?=\d+\s+[LMJVSD]|$)", re.DOTALL
        )

        matches = day_pattern.findall(page_text)

        for match in matches:
            day_num = int(match[0])
            day_of_week = match[1].strip()
            content = match[2].strip().replace("\n", " ").replace("\r", "")

            if not content:
                continue

            is_sunday = day_of_week == "D"

            month_data.append(
                self._parse_content(
                    day_num, day_of_week, content, year, month, is_sunday
                )
            )

        _LOGGER.debug(
            "Parsed %d days for Catholic calendar %d/%d", len(month_data), month, year
        )
        return month_data

    def _parse_content(
        self,
        day_num: int,
        day_of_week: str,
        content: str,
        year: int,
        month: int,
        is_sunday: bool,
    ) -> CatholicCalendarDay:
        """Parse content string into CatholicCalendarDay."""
        content = content.strip()

        has_dagger = "&#8224;" in content or "†" in content
        has_double_star = "**" in content
        has_single_star = "*" in content

        if has_dagger and has_double_star:
            feast_level = CATHOLIC_FEAST_LEVEL_SOLEMNITY
        elif has_dagger:
            feast_level = CATHOLIC_FEAST_LEVEL_FEAST
        elif has_double_star:
            feast_level = CATHOLIC_FEAST_LEVEL_MEMORIAL
        elif has_single_star:
            feast_level = CATHOLIC_FEAST_LEVEL_OPTIONAL
        else:
            feast_level = CATHOLIC_FEAST_LEVEL_OPTIONAL

        content_clean = re.sub(r"&#8224;", "", content)
        content_clean = re.sub(r"\s+", " ", content_clean).strip()

        parts = content_clean.split("Fer.")
        if len(parts) > 1:
            feast_name = parts[0].strip()
            saints = "Fer." + parts[1].strip()
        else:
            feast_name = None
            saints = content_clean

        return CatholicCalendarDay(
            day=day_num,
            month=month,
            year=year,
            day_of_week=day_of_week,
            saints=saints,
            feast_name=feast_name or saints,
            feast_level=feast_level,
            is_sunday=is_sunday,
        )

    def _parse_feast_row(
        self,
        day_num: int,
        day_of_week: str,
        content_cell,
        year: int,
        month: int,
        is_sunday: bool,
    ) -> CatholicCalendarDay:
        """Parse a feast day row (stil2)."""
        text = content_cell.get_text(separator=" ", strip=True)

        feast_name = None
        saints = ""

        parts = text.split("Fer.")
        if len(parts) > 1:
            feast_with_saints = parts[0].strip()
            saints_part = "Fer." + parts[1].strip()
            feast_name = feast_with_saints
            saints = saints_part
        else:
            saints = text

        feast_name = feast_name or saints
        feast_level = self._determine_feast_level(content_cell)

        return CatholicCalendarDay(
            day=day_num,
            month=month,
            year=year,
            day_of_week=day_of_week,
            saints=saints,
            feast_name=feast_name,
            feast_level=feast_level,
            is_sunday=is_sunday,
        )
