"""Constants for the Calendar Ortodox integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "calendar_ortodox"

# API Configuration
BASE_URL = "https://www.noutati-ortodoxe.ro/calendar-ortodox/"
CATHOLIC_BASE_URL = "https://www.catholica.ro/calendar-romano-catolic-"
DEFAULT_YEAR = None  # None means current year

# Calendar types
CALENDAR_TYPE_ORTHODOX = "orthodox"
CALENDAR_TYPE_CATHOLIC = "catholic"
CALENDAR_TYPE_BOTH = "both"

# Update interval
SCAN_INTERVAL = timedelta(hours=6)  # Update 4 times per day

# Configuration
CONF_LANGUAGE = "language"
CONF_INCLUDE_FASTING = "include_fasting"
CONF_INCLUDE_READINGS = "include_readings"
CONF_CALENDAR_TYPE = "calendar_type"

# Default values
DEFAULT_LANGUAGE = "ro"
DEFAULT_INCLUDE_FASTING = True
DEFAULT_INCLUDE_READINGS = True
DEFAULT_CALENDAR_TYPE = CALENDAR_TYPE_ORTHODOX

# Entity attributes
ATTR_SAINTS = "saints"
ATTR_FEAST_DAY = "feast_day"
ATTR_FEAST_LEVEL = "feast_level"
ATTR_FASTING = "fasting"
ATTR_FASTING_TYPE = "fasting_type"
ATTR_FASTING_DESCRIPTION = "fasting_description"
ATTR_READINGS = "readings"
ATTR_MOON_PHASE = "moon_phase"
ATTR_DAY_OF_WEEK = "day_of_week"
ATTR_LITURGICAL_INFO = "liturgical_info"
ATTR_COMMENTS = "comments"

# Feast levels (based on crosses/daggers in HTML)
FEAST_LEVEL_MAJOR = "major"  # † symbol (sarbatoare with crosses)
FEAST_LEVEL_GREAT = "great"  # (†) symbol (great feasts)
FEAST_LEVEL_NORMAL = "normal"  # No special marking

# CSS classes for feast days
CSS_CLASS_SARBATOARE = "sarbatoare"
CSS_CLASS_DUMINICA = "duminica"

# Fasting icons mapping
FASTING_ICONS = {
    "post-4.png": "strict_fast",  # Strict fasting
    "luna-0.png": "new_moon",
    "luna-1.png": "first_quarter",
    "luna-2.png": "full_moon",
    "luna-3.png": "last_quarter",
}

# Romanian day names
DAY_NAMES = {
    "L": "Luni",
    "M": "Marți",
    "M": "Miercuri",
    "J": "Joi",
    "V": "Vineri",
    "S": "Sâmbătă",
    "D": "Duminică",
}

# Fasting type translations
FASTING_TRANSLATIONS = {
    "Post": "Fasting",
    "Post negru": "Strict fasting (bread and water)",
    "Numai seara, pâine și apă": "Only evening, bread and water",
    "Dezlegare la pește": "Fish allowed",
    "Dezlegare la ulei și vin": "Oil and wine allowed",
    "Dezlegare la brânză, lapte și ouă": "Dairy and eggs allowed",
    "Zi aliturgică": "No liturgy",
}
