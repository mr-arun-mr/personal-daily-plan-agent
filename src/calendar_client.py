import os
import logging
from datetime import datetime, timedelta
from typing import Optional
import pytz

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
TOKEN_FILE = "token.json"
CREDENTIALS_FILE = os.environ.get("GOOGLE_CREDENTIALS_FILE", "credentials.json")


def _get_service():
    """Build and return an authenticated Google Calendar service."""
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        creds = None
        if os.path.exists(TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_FILE, "w") as f:
                f.write(creds.to_json())

        if not creds or not creds.valid:
            return None

        return build("calendar", "v3", credentials=creds)
    except Exception as e:
        logger.warning("Google Calendar unavailable: %s", e)
        return None


def is_calendar_configured() -> bool:
    """Check if Google Calendar credentials are available."""
    return os.path.exists(TOKEN_FILE)


def get_today_events(timezone: str = "UTC") -> list[dict]:
    """Fetch today's calendar events. Returns empty list if calendar not configured."""
    service = _get_service()
    if not service:
        return []

    try:
        tz = pytz.timezone(timezone)
        now = datetime.now(tz)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)

        result = service.events().list(
            calendarId="primary",
            timeMin=start.isoformat(),
            timeMax=end.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        events = result.get("items", [])
        formatted = []
        for event in events:
            start_info = event.get("start", {})
            end_info = event.get("end", {})

            if "dateTime" in start_info:
                start_dt = datetime.fromisoformat(start_info["dateTime"])
                end_dt = datetime.fromisoformat(end_info["dateTime"])
                time_str = f"{start_dt.strftime('%H:%M')}–{end_dt.strftime('%H:%M')}"
            else:
                time_str = "All day"

            formatted.append({
                "title": event.get("summary", "Untitled"),
                "time": time_str,
            })

        return formatted
    except Exception as e:
        logger.warning("Failed to fetch today's events: %s", e)
        return []


def get_week_events(timezone: str = "UTC") -> dict[str, list[dict]]:
    """Fetch this week's calendar events grouped by date."""
    service = _get_service()
    if not service:
        return {}

    try:
        tz = pytz.timezone(timezone)
        now = datetime.now(tz)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=7)

        result = service.events().list(
            calendarId="primary",
            timeMin=start.isoformat(),
            timeMax=end.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        events = result.get("items", [])
        by_day: dict[str, list[dict]] = {}

        for event in events:
            start_info = event.get("start", {})
            end_info = event.get("end", {})

            if "dateTime" in start_info:
                start_dt = datetime.fromisoformat(start_info["dateTime"])
                end_dt = datetime.fromisoformat(end_info["dateTime"])
                day_key = start_dt.strftime("%Y-%m-%d")
                time_str = f"{start_dt.strftime('%H:%M')}–{end_dt.strftime('%H:%M')}"
            else:
                day_key = start_info.get("date", "")
                time_str = "All day"

            if day_key not in by_day:
                by_day[day_key] = []
            by_day[day_key].append({
                "title": event.get("summary", "Untitled"),
                "time": time_str,
            })

        return by_day
    except Exception as e:
        logger.warning("Failed to fetch week events: %s", e)
        return {}
