# git/RAG/langchain/booking/booking_tools.py

import logging
from pathlib import Path

from langchain.tools import tool

# ── path setup ───────────────────────────────────────────────────────────────

from booking.calendar_service import (
    get_available_slots,
    create_appointment
)

logger = logging.getLogger(__name__)


@tool
def check_available_slots(date: str) -> str:
    """
    Check available 30-minute appointment slots at Denta
    Clinic for a given date.

    Use this when a patient asks what times are free, or before confirming
    a booking to verify their preferred slot is still available.

    Args:
        date: The date to check in YYYY-MM-DD format (e.g. "2025-04-29")

    Returns:
        A plain string listing available time slots, or a message explaining
        why no slots are available (clinic closed, fully booked, etc.)
    """
    slots = get_available_slots(date)

    if not slots:
        return (
            f"No available slots on {date}. "
            "The clinic may be closed or fully booked on that day."
        )

    slots_str = ", ".join(slots)
    return f"Available slots on {date}: {slots_str}"


@tool
def book_appointment(
    patient_name: str,
    phone: str,
    date: str,
    time: str,
    service: str
) -> str:
    """
    Book a dental appointment at Denta Clinic and create
    a Google Calendar event.

    Only call this after:
    1. Confirming the patient's preferred date and time using check_available_slots
    2. The patient has explicitly confirmed their chosen slot
    3. You have collected: patient name, phone number, date, time, and service type

    Do not guess any of these details — ask the patient if any are missing.

    Args:
        patient_name: Patient's full name as they stated it
        phone:        Patient's WhatsApp number (e.g. "+254712345678")
        date:         Appointment date in YYYY-MM-DD format (e.g. "2025-04-29")
        time:         Appointment time in HH:MM 24hr format (e.g. "14:00")
        service:      Type of dental treatment (e.g. "cleaning", "extraction",
                      "braces consultation", "root canal")

    Returns:
        Confirmation message with event ID, or an error message if booking failed.
    """
    result = create_appointment(
        patient_name=patient_name,
        phone=phone,
        date_str=date,
        time_str=time,
        service=service
    )

    if not result:
        return (
            "Sorry, I was unable to create the booking. "
            "Please call the clinic directly on 0700 000000."
        )

    return (
        f"Appointment confirmed! Here are your details:\n"
        f"  Patient:  {result['patient_name']}\n"
        f"  Service:  {result['service']}\n"
        f"  Date:     {result['date']}\n"
        f"  Time:     {result['time']}\n"
        f"  Ref ID:   {result['event_id']}\n\n"
        f"Please arrive 5 minutes early. "
        f"Call 0700 000 000 if you need to make any changes."
    )
# ── export all tools as a list for easy import into the agent ─────────────────
BOOKING_TOOLS = [
    check_available_slots,
    book_appointment]

'''
@tool
def cancel_appointment(event_id: str) -> str:
    """
    Cancel an existing dental appointment using its reference ID.

    Use this when a patient explicitly asks to cancel their appointment
    and provides their booking reference ID.

    If the patient does not have their reference ID, ask them to provide
    their name and preferred date instead, then use check_available_slots
    to locate the booking before cancelling.

    Args:
        event_id: The booking reference ID provided at the time of booking
                  (e.g. "abc123xyz")

    Returns:
        Confirmation that the appointment was cancelled, or an error message.
    """
    success = cancel_appointment_by_id(event_id)

    if not success:
        return (
            f"Could not cancel appointment with ID {event_id}. "
            "Please call the clinic directly on 0762 223 925."
        )

    return (
        f"Your appointment (Ref: {event_id}) has been successfully cancelled. "
        "To rebook, just let me know your preferred date and time."
    )


@tool
def reschedule_appointment(
    event_id: str,
    new_date: str,
    new_time: str
) -> str:
    """
    Reschedule an existing appointment to a new date and time.

    Use this when a patient wants to move their appointment to a different
    slot. Always confirm the new slot is available using check_available_slots
    before calling this tool.

    Args:
        event_id: The booking reference ID of the appointment to reschedule
        new_date: The new appointment date in YYYY-MM-DD format
        new_time: The new appointment time in HH:MM 24hr format

    Returns:
        Confirmation of the rescheduled appointment, or an error message.
    """
    # Cancel the existing appointment first
    cancelled = cancel_appointment_by_id(event_id)

    if not cancelled:
        return (
            f"Could not reschedule — unable to cancel appointment {event_id}. "
            "Please call the clinic directly on 0762 223 925."
        )

    # The agent will need patient details to rebook — ask it to use book_appointment
    return (
        f"Previous appointment (Ref: {event_id}) cancelled. "
        f"I now need your name and service type to complete the rebooking "
        f"for {new_date} at {new_time}."
    )


# ── export all tools as a list for easy import into the agent ─────────────────
BOOKING_TOOLS = [
    check_available_slots,
    book_appointment,
    cancel_appointment,
    reschedule_appointment,
]
'''