import json
from datetime import datetime
from typing import Any

from src.tools.google_calendar import (
    cancel_appointment,
    check_availability,
    create_appointment,
    find_appointment,
    reschedule_appointment,
)
from src.tools.google_sheets import (
    record_customer_interaction,
)


def _parse_datetime(value: str) -> datetime:

    if not value:
        raise ValueError(
            "start_time is required"
        )

    try:
        return datetime.fromisoformat(value)

    except ValueError as exc:
        raise ValueError(
            f"Invalid start_time: {value}. "
            "Expected ISO 8601 format."
        ) from exc


def _normalise_arguments(
    arguments: Any,
) -> dict[str, Any]:

    if isinstance(arguments, str):
        arguments = json.loads(arguments)

    if not isinstance(arguments, dict):
        raise TypeError(
            "Tool arguments must be a JSON object"
        )

    return arguments


def execute_vapi_tool(
    tool_name: str,
    arguments: dict[str, Any] | str,
) -> Any:

    arguments = _normalise_arguments(arguments)

    print()
    print("=" * 70)
    print("EXECUTING VAPI TOOL")
    print(f"Tool: {tool_name}")
    print(
        "Arguments:",
        json.dumps(
            arguments,
            indent=2,
            default=str,
        ),
    )
    print("=" * 70)

    if tool_name == "check_availability":

        start_time = _parse_datetime(
            arguments.get("start_time", "")
        )

        duration_minutes = int(
            arguments.get(
                "duration_minutes",
                0,
            )
        )

        if duration_minutes <= 0:
            raise ValueError(
                "duration_minutes must be greater than 0"
            )

        result = check_availability(
            start_time=start_time,
            duration_minutes=duration_minutes,
        )

        return {
            "available": result["available"],
            "conflicts": result.get(
                "conflicts",
                [],
            ),
        }

    elif tool_name == "create_appointment":

        required_fields = [
            "customer_name",
            "phone",
            "dog_name",
            "service_name",
            "start_time",
            "duration_minutes",
        ]

        for field in required_fields:

            if not arguments.get(field):

                raise ValueError(
                    f"Missing required field: {field}"
                )

        start_time = _parse_datetime(
            arguments["start_time"]
        )

        duration_minutes = int(
            arguments["duration_minutes"]
        )

        if duration_minutes <= 0:
            raise ValueError(
                "duration_minutes must be greater than 0"
            )

        # ALWAYS check before booking
        availability = check_availability(
            start_time=start_time,
            duration_minutes=duration_minutes,
        )

        if not availability["available"]:

            return {
                "booked": False,
                "reason": "time_unavailable",
                "message": (
                    "The requested appointment "
                    "time is not available."
                ),
            }

        appointment = create_appointment(
            customer_name=arguments["customer_name"],
            phone=arguments["phone"],
            dog_name=arguments["dog_name"],
            service_name=arguments["service_name"],
            start_time=start_time,
            duration_minutes=duration_minutes,
        )

        # Save booking to Sheets
        record_customer_interaction(
            name=arguments["customer_name"],
            phone=arguments["phone"],
            dog_name=arguments["dog_name"],
            intent="booking",
            outcome="booked",
            summary=(
                f"Booked {arguments['service_name']} "
                f"appointment."
            ),
            calendar_event_link=appointment.get(
                "htmlLink",
                "",
            ),
        )

        return {
            "booked": True,
            "appointment_id": appointment.get(
                "id"
            ),
            "event_link": appointment.get(
                "htmlLink",
                "",
            ),
            "start_time": appointment.get(
                "start",
                {},
            ).get("dateTime"),
            "end_time": appointment.get(
                "end",
                {},
            ).get("dateTime"),
        }

    elif tool_name == "find_appointment":

        appointment_id = arguments.get(
            "appointment_id"
        )

        if not appointment_id:

            raise ValueError(
                "appointment_id is required"
            )

        appointment = find_appointment(
            appointment_id=appointment_id
        )

        return {
            "found": True,
            "appointment_id": appointment.get(
                "id"
            ),
            "summary": appointment.get(
                "summary",
                "",
            ),
            "start_time": appointment.get(
                "start",
                {},
            ).get("dateTime"),
            "end_time": appointment.get(
                "end",
                {},
            ).get("dateTime"),
            "description": appointment.get(
                "description",
                "",
            ),
        }
    
    elif tool_name == "reschedule_appointment":

        required_fields = [
            "appointment_id",
            "start_time",
            "duration_minutes",
        ]

        for field in required_fields:

            if not arguments.get(field):

                raise ValueError(
                    f"Missing required field: {field}"
                )

        appointment_id = arguments[
            "appointment_id"
        ]

        start_time = _parse_datetime(
            arguments["start_time"]
        )

        duration_minutes = int(
            arguments["duration_minutes"]
        )

        # Check new time first
        availability = check_availability(
            start_time=start_time,
            duration_minutes=duration_minutes,
        )

        if not availability["available"]:

            return {
                "rescheduled": False,
                "reason": "time_unavailable",
                "message": (
                    "The requested new time "
                    "is not available."
                ),
            }

        appointment = reschedule_appointment(
            appointment_id=appointment_id,
            start_time=start_time,
            duration_minutes=duration_minutes,
        )

        return {
            "rescheduled": True,
            "appointment_id": appointment.get(
                "id"
            ),
            "start_time": appointment.get(
                "start",
                {},
            ).get("dateTime"),
            "end_time": appointment.get(
                "end",
                {},
            ).get("dateTime"),
        }
    
    elif tool_name == "cancel_appointment":

        appointment_id = arguments.get(
            "appointment_id"
        )

        if not appointment_id:

            raise ValueError(
                "appointment_id is required"
            )

        result = cancel_appointment(
            appointment_id=appointment_id
        )

        return result

    elif tool_name == "record_customer_interaction":

        phone = arguments.get("phone")

        if not phone:

            raise ValueError(
                "phone is required"
            )

        result = record_customer_interaction(

            name=arguments.get(
                "name",
                "",
            ),

            phone=phone,

            dog_name=arguments.get(
                "dog_name",
                "",
            ),

            notes=arguments.get(
                "notes",
                "",
            ),

            intent=arguments.get(
                "intent",
                "general",
            ),

            outcome=arguments.get(
                "outcome",
                "completed",
            ),

            summary=arguments.get(
                "summary",
                "",
            ),

            handoff=arguments.get(
                "handoff",
                "no",
            ),

        )

        return {
            "recorded": True
        }

    raise ValueError(
        f"Unknown Vapi tool: {tool_name}"
    )