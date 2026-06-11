# git/RAG/langchain/booking/calendar_service.py

import logging
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from googleapiclient.errors import HttpError

# ── path setup ──────────────────────────────────────────────────────────────
# Resolve three levels up to reach git/RAG/ where config.py lives

from config import GOOGLE_CALENDAR_ID
from booking.calendar_auth import get_calendar_service

logger = logging.getLogger(__name__)

# ── constants ────────────────────────────────────────────────────────────────
TIMEZONE = ZoneInfo("Africa/Nairobi")
SLOT_DURATION = 30  # minutes

# Clinic opening hours per weekday (0=Monday ... 6=Sunday)
OPENING_HOURS = {
    0: ("08:30", "17:00"),  # Monday
    1: ("08:30", "17:00"),  # Tuesday
    2: ("08:30", "17:00"),  # Wednesday
    3: ("08:30", "17:00"),  # Thursday
    4: ("08:30", "17:00"),  # Friday
    5: ("09:00", "14:00"),  # Saturday
    # Sunday → not in dict → clinic closed
}


# ── helpers ──────────────────────────────────────────────────────────────────

def _parse_time(date: datetime.date, time_str: str) -> datetime:
    """Combine a date and 'HH:MM' string into a timezone-aware datetime."""
    hour, minute = map(int, time_str.split(":"))
    return datetime(
        date.year, date.month, date.day,
        hour, minute, tzinfo=TIMEZONE
    )


def _generate_slots(date: datetime.date) -> list[datetime]:
    """
    Generate all possible 30-minute slots for a given date
    based on the clinic's opening hours.
    Returns empty list if the clinic is closed that day.
    """
    weekday = date.weekday()
    if weekday not in OPENING_HOURS:
        return []  # Clinic closed (Sunday)

    open_str, close_str = OPENING_HOURS[weekday]
    open_time = _parse_time(date, open_str)
    close_time = _parse_time(date, close_str)

    slots = []
    current = open_time
    while current + timedelta(minutes=SLOT_DURATION) <= close_time:
        slots.append(current)
        current += timedelta(minutes=SLOT_DURATION)

    return slots


def _get_booked_times(service, date: datetime.date) -> list[tuple]:
    """
    Fetch all existing calendar events for a given date.
    Returns a list of (start, end) datetime tuples.
    """
    # Google Calendar API expects RFC3339 format with timezone
    day_start = _parse_time(date, "00:00").isoformat()
    day_end = _parse_time(date, "23:59").isoformat()

    try:
        result = service.events().list(
            calendarId=GOOGLE_CALENDAR_ID,
            timeMin=day_start,
            timeMax=day_end,
            singleEvents=True,
            orderBy="startTime"
        ).execute()
    except HttpError as e:
        logger.error(f"Failed to fetch events: {e}")
        return []

    booked = []
    for event in result.get("items", []):
        start = event["start"].get("dateTime")
        end = event["end"].get("dateTime")
        if start and end:
            booked.append((
                datetime.fromisoformat(start),
                datetime.fromisoformat(end)
            ))

    return booked


def _is_slot_free(slot: datetime, booked: list[tuple]) -> bool:
    """
    Check if a 30-minute slot overlaps with any existing booking.
    A slot is free if it doesn't overlap with any booked period.
    """
    slot_end = slot + timedelta(minutes=SLOT_DURATION)
    for booked_start, booked_end in booked:
        # Overlap exists if slot starts before booking ends
        # AND slot ends after booking starts
        if slot < booked_end and slot_end > booked_start:
            return False
    return True


# ── public functions ─────────────────────────────────────────────────────────

def get_available_slots(date_str: str) -> list[str]:
    """
    Return available 30-minute appointment slots for a given date.

    Args:
        date_str: Date in YYYY-MM-DD format (e.g. "2025-04-24")

    Returns:
        List of available time strings in HH:MM format (e.g. ["08:30", "09:00"])
        Empty list if clinic is closed or no slots are available.
    """
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        logger.error(f"Invalid date format: {date_str}")
        return []

    service = get_calendar_service()
    all_slots = _generate_slots(date)

    if not all_slots:
        logger.info(f"Clinic closed on {date_str}")
        return []

    booked = _get_booked_times(service, date)
    free_slots = [
        slot.strftime("%H:%M")
        for slot in all_slots
        if _is_slot_free(slot, booked)
    ]

    logger.info(f"Found {len(free_slots)} free slots on {date_str}")
    return free_slots


def create_appointment(
    patient_name: str,
    phone: str,
    date_str: str,
    time_str: str,
    service: str
) -> dict:
    """
    Create a dental appointment in Google Calendar.

    Args:
        patient_name: Full name of the patient
        phone:        Patient's WhatsApp number (e.g. +254712345678)
        date_str:     Appointment date in YYYY-MM-DD format
        time_str:     Appointment time in HH:MM format (e.g. "14:00")
        service:      Type of dental service (e.g. "cleaning", "extraction")

    Returns:
        Dict with keys: event_id, date, time, patient_name, service
        Returns empty dict if booking failed.
    """
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d").date()
        start = _parse_time(date, time_str)
        end = start + timedelta(minutes=SLOT_DURATION)
    except ValueError as e:
        logger.error(f"Invalid date/time format: {e}")
        return {}

    event = {
        "summary": f"Dental Appointment — {patient_name}",
        "description": (
            f"Service: {service}\n"
            f"Patient: {patient_name}\n"
            f"Phone: {phone}"
        ),
        "start": {
            "dateTime": start.isoformat(),
            "timeZone": "Africa/Nairobi",
        },
        "end": {
            "dateTime": end.isoformat(),
            "timeZone": "Africa/Nairobi",
        },
    }

    try:
        calendar_service = get_calendar_service()
        created_event = calendar_service.events().insert(
            calendarId=GOOGLE_CALENDAR_ID,
            body=event
        ).execute()

        logger.info(f"Appointment created: {created_event['id']}")
        return {
            "event_id": created_event["id"],
            "date": date_str,
            "time": time_str,
            "patient_name": patient_name,
            "service": service,
        }

    except HttpError as e:
        logger.error(f"Failed to create appointment: {e}")
        return {}