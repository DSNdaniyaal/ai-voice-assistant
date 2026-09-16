import os
from datetime import datetime, time, timedelta, timezone
from threading import Lock

from dotenv import load_dotenv
from googleapiclient.discovery import build

from src.config import BUSINESS_INFO, get_service_duration
from src.services.google_service import get_google_credentials

load_dotenv()

CALENDAR_ID = os.environ.get("GOOGLE_CALENDAR_ID")
_booking_lock = Lock()


def _require_future_time(start_time: datetime) -> datetime:
    """Reject past times and attach the local timezone to naive values."""

    if start_time.tzinfo is None:
        local_timezone = datetime.now().astimezone().tzinfo
        start_time = start_time.replace(tzinfo=local_timezone)

    now = datetime.now(start_time.tzinfo)
    if start_time <= now:
        raise ValueError(
            f"Appointment start time {start_time.isoformat()} is in the past. "
            "Use the current date and a future time."
        )

    return start_time


def _require_business_hours(
    start_time: datetime,
    duration_minutes: int,
) -> datetime:
    """Reject appointments outside the configured business hours."""

    end_time = start_time + timedelta(minutes=duration_minutes)
    day_name = start_time.strftime("%A").lower()
    hours = BUSINESS_INFO["hours"].get(day_name, "Closed")

    if hours == "Closed":
        raise ValueError(
            f"Appointments are not available on {start_time.strftime('%A')}."
        )

    opening_text, closing_text = hours.split(" - ")

    def parse_business_time(value: str) -> time:
        clock, period = value.rsplit(" ", 1)
        hour_text, minute_text = clock.split(":")
        hour = int(hour_text) % 12
        if period == "PM":
            hour += 12
        return time(hour=hour, minute=int(minute_text))

    opening_time = parse_business_time(opening_text)
    closing_time = parse_business_time(closing_text)
    opening = start_time.replace(
        hour=opening_time.hour,
        minute=opening_time.minute,
        second=0,
        microsecond=0,
    )
    closing = start_time.replace(
        hour=closing_time.hour,
        minute=closing_time.minute,
        second=0,
        microsecond=0,
    )

    if start_time < opening or end_time > closing:
        raise ValueError(
            f"Appointments on {start_time.strftime('%A')} must be between "
            f"{opening_text} and {closing_text}."
        )

    return end_time


def get_calendar_service():

    creds = get_google_credentials()

    return build(
        "calendar",
        "v3",
        credentials=creds
    )

def get_upcoming_events():

    service = get_calendar_service()

    now = datetime.now(timezone.utc).isoformat()

    events_result = (
        service.events()
        .list(
            calendarId=CALENDAR_ID,
            timeMin=now,
            maxResults=20,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    events = events_result.get("items", [])

    return events


def check_availability(
    start_time: datetime,
    duration_minutes: int,
):
    start_time = _require_future_time(start_time)

    service = get_calendar_service()

    duration_minutes = int(duration_minutes)

    if duration_minutes <= 0:
        raise ValueError(
            "duration_minutes must be greater than 0"
        )

    end_time = start_time + timedelta(
        minutes=duration_minutes
    )

    events_result = (
        service.events()
        .list(
            calendarId=CALENDAR_ID,
            timeMin=start_time.isoformat(),
            timeMax=end_time.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    events = events_result.get("items", [])

    conflicts = []

    for event in events:
        conflicts.append({
            "id": event.get("id"),
            "summary": event.get("summary", ""),
            "start": event.get("start", {}).get("dateTime"),
            "end": event.get("end", {}).get("dateTime"),
        })

    return {
        "available": len(conflicts) == 0,
        "conflicts": conflicts,
    }


def create_appointment(
    customer_name: str,
    phone: str,
    dog_name: str,
    service_name: str,
    start_time: datetime,
):
    if not CALENDAR_ID:
        raise ValueError(
            "GOOGLE_CALENDAR_ID is not configured in .env"
        )

    duration_minutes = get_service_duration(service_name)

    start_time = _require_future_time(start_time)
    _require_business_hours(start_time, duration_minutes)

    # Keep the availability check and insert together within this process.
    with _booking_lock:
        availability = check_availability(start_time, duration_minutes)
        if not availability["available"]:
            raise ValueError("The requested appointment time is already booked.")

        service = get_calendar_service()

        end_time = start_time + timedelta(minutes=duration_minutes)
        event = {
            "summary": f"{service_name} - {dog_name}",
            "description": (
                f"Customer: {customer_name}\n"
                f"Phone: {phone}\n"
                f"Dog: {dog_name}\n"
                f"Service: {service_name}"
            ),
            "start": {"dateTime": start_time.isoformat()},
            "end": {"dateTime": end_time.isoformat()},
        }

        return (
            service.events()
            .insert(calendarId=CALENDAR_ID, body=event)
            .execute()
        )

def find_appointment(appointment_id: str):
    service = get_calendar_service()
    return (
        service.events()
        .get(calendarId=CALENDAR_ID, eventId=appointment_id)
        .execute()
    )


def reschedule_appointment(
    appointment_id: str,
    start_time: datetime,
    duration_minutes: int,
):
    duration_minutes = int(duration_minutes)
    if duration_minutes <= 0:
        raise ValueError("duration_minutes must be greater than 0")

    start_time = _require_future_time(start_time)
    _require_business_hours(start_time, duration_minutes)

    with _booking_lock:
        availability = check_availability(start_time, duration_minutes)
        conflicts = [
            conflict
            for conflict in availability["conflicts"]
            if conflict.get("id") != appointment_id
        ]
        if conflicts:
            raise ValueError("The requested appointment time is already booked.")

        service = get_calendar_service()
        end_time = start_time + timedelta(minutes=duration_minutes)
        event = {
            "start": {"dateTime": start_time.isoformat()},
            "end": {"dateTime": end_time.isoformat()},
        }

        return (
            service.events()
            .patch(calendarId=CALENDAR_ID, eventId=appointment_id, body=event)
            .execute()
        )


def cancel_appointment(appointment_id: str):
    service = get_calendar_service()
    service.events().delete(
        calendarId=CALENDAR_ID,
        eventId=appointment_id,
    ).execute()
    return {"cancelled": True, "appointment_id": appointment_id}
