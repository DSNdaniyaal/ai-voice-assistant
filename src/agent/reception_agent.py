import json
import os
from datetime import datetime
from urllib.error import URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from google.genai import types

from src.agent.prompts import SYSTEM_PROMPT
from src.agent.state import ConversationState
from src.config import BUSINESS_INFO
from src.tools.google_calendar import (
    cancel_appointment,
    check_availability,
    create_appointment,
    find_appointment,
    reschedule_appointment,
)
from src.tools.google_sheets import record_customer_interaction

load_dotenv()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/chat")
MODEL_NAME = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

TOOLS = [
    types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="check_availability",
                description=(
                    "Check whether a grooming appointment slot is available. "
                    "Always use this before booking or rescheduling an appointment."
                ),
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "start_time": {
                            "type": "STRING",
                            "description": (
                                "Appointment start time in ISO 8601 format, "
                                "including timezone."
                            ),
                        },
                        "duration_minutes": {
                            "type": "INTEGER",
                            "description": "Appointment duration in minutes.",
                        },
                    },
                    "required": ["start_time", "duration_minutes"],
                },
            ),
            types.FunctionDeclaration(
                name="create_appointment",
                description=(
                    "Create a grooming appointment in Google Calendar. "
                    "Only use this after availability has been confirmed "
                    "and the customer has confirmed the appointment details."
                ),
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "customer_name": {"type": "STRING"},
                        "phone": {"type": "STRING"},
                        "dog_name": {"type": "STRING"},
                        "service_name": {"type": "STRING"},
                        "start_time": {
                            "type": "STRING",
                            "description": "ISO 8601 datetime with timezone.",
                        },
                        "duration_minutes": {"type": "INTEGER"},
                    },
                    "required": [
                        "customer_name",
                        "phone",
                        "dog_name",
                        "service_name",
                        "start_time",
                        "duration_minutes",
                    ],
                },
            ),
            types.FunctionDeclaration(
                name="find_appointment",
                description=(
                    "Find an existing appointment using its Google Calendar event ID."
                ),
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "appointment_id": {"type": "STRING"},
                    },
                    "required": ["appointment_id"],
                },
            ),
            types.FunctionDeclaration(
                name="reschedule_appointment",
                description=(
                    "Move an existing appointment to a new time. "
                    "Always check availability before using this."
                ),
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "appointment_id": {"type": "STRING"},
                        "start_time": {
                            "type": "STRING",
                            "description": "New start time in ISO 8601 format.",
                        },
                        "duration_minutes": {"type": "INTEGER"},
                    },
                    "required": [
                        "appointment_id",
                        "start_time",
                        "duration_minutes",
                    ],
                },
            ),
            types.FunctionDeclaration(
                name="cancel_appointment",
                description="Cancel an existing grooming appointment.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "appointment_id": {"type": "STRING"},
                    },
                    "required": ["appointment_id"],
                },
            ),
            types.FunctionDeclaration(
                name="record_customer_interaction",
                description=(
                    "Record the details and outcome of the current customer call "
                    "in the Grooming Log. Use this after handling a customer "
                    "interaction to maintain the customer's history."
                ),
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "phone": {
                            "type": "STRING",
                            "description": "Customer phone number.",
                        },
                        "name": {
                            "type": "STRING",
                            "description": "Customer's name.",
                        },
                        "dog_name": {
                            "type": "STRING",
                            "description": "Name of the customer's dog.",
                        },
                        "intent": {
                            "type": "STRING",
                            "description": (
                                "Reason for the call, such as booking, "
                                "rescheduling, cancellation, pricing, hours, "
                                "vaccination, breed_question, complaint, or "
                                "late_arrival."
                            ),
                        },
                        "outcome": {
                            "type": "STRING",
                            "description": (
                                "Final outcome of the interaction, such as "
                                "booked, rescheduled, cancelled, answered, "
                                "escalated, or unresolved."
                            ),
                        },
                        "summary": {
                            "type": "STRING",
                            "description": "Short summary of the customer interaction.",
                        },
                        "notes": {
                            "type": "STRING",
                            "description": "Additional notes relevant to the customer or dog.",
                        },
                        "handoff": {
                            "type": "STRING",
                            "description": (
                                "Whether the interaction was handed off to a human. "
                                "Use 'yes' or 'no'."
                            ),
                            "enum": ["yes", "no"],
                        },
                    },
                    "required": [
                        "phone",
                        "intent",
                        "outcome",
                        "summary",
                    ],
                },
            ),
        ]
    )
]

def execute_tool(name: str, arguments: dict):
    """
    Execute a tool requested by the model.

    `arguments` arrives as a plain dict already (Gemini parses function-call
    args for you — no json.loads needed like with OpenAI's Responses API).
    """

    if name == "check_availability":
        start_time = datetime.fromisoformat(arguments["start_time"])

        return check_availability(
            start_time=start_time,
            duration_minutes=arguments["duration_minutes"],
        )

    elif name == "create_appointment":
        start_time = datetime.fromisoformat(arguments["start_time"])

        appointment = create_appointment(
            customer_name=arguments["customer_name"],
            phone=arguments["phone"],
            dog_name=arguments["dog_name"],
            service_name=arguments["service_name"],
            start_time=start_time,
            duration_minutes=arguments["duration_minutes"],
        )

        interaction = record_customer_interaction(
            name=arguments["customer_name"],
            phone=arguments["phone"],
            dog_name=arguments["dog_name"],
            intent="booking",
            outcome="booked",
            summary=f"Booked {arguments['service_name']} appointment.",
            calendar_event_link=appointment.get("htmlLink", ""),
        )
        return {"appointment": appointment, "interaction": interaction}

    elif name == "find_appointment":
        return find_appointment(appointment_id=arguments["appointment_id"])

    elif name == "reschedule_appointment":
        start_time = datetime.fromisoformat(arguments["start_time"])

        return reschedule_appointment(
            appointment_id=arguments["appointment_id"],
            start_time=start_time,
            duration_minutes=arguments["duration_minutes"],
        )

    elif name == "cancel_appointment":
        return cancel_appointment(appointment_id=arguments["appointment_id"])

    elif name == "record_customer_interaction":
        return record_customer_interaction(
            name=arguments.get("name", ""),
            phone=arguments["phone"],
            dog_name=arguments.get("dog_name", ""),
            notes=arguments.get("notes", ""),
            intent=arguments["intent"],
            outcome=arguments["outcome"],
            summary=arguments["summary"],
            handoff=arguments.get("handoff", "no"),
        )

    else:
        raise ValueError(f"Unknown tool: {name}")


def build_system_prompt():
    """
    Add business information to the base system prompt.
    """

    current_time = datetime.now().astimezone()
 
    breeds = BUSINESS_INFO["breeds"]
    breed_policy = (
        f"Accepted: {breeds['accepted']}. "
        f"Special cases: {breeds['special_cases']}"
    )
 
    business_context = f"""

CURRENT DATE AND TIME

Today is {current_time.strftime("%A, %B %d, %Y")}.
The current time is {current_time.strftime("%I:%M %p %Z")}.
Use this date and time when interpreting relative dates. Never use a date in the past.
 
BUSINESS INFORMATION
 
Business:
{BUSINESS_INFO["name"]}
 
Hours:
{json.dumps(BUSINESS_INFO["hours"], indent=2)}
 
Services:
{json.dumps(BUSINESS_INFO["services"], indent=2)}
 
Vaccination requirements:
{json.dumps(BUSINESS_INFO["vaccination_requirements"], indent=2)}
 
Breed policy:
{breed_policy}
"""
 
    return SYSTEM_PROMPT + business_context


def _ollama_tools() -> list[dict]:
    declarations = [
        declaration
        for declaration in TOOLS[0].function_declarations
        if declaration.name != "record_customer_interaction"
    ]
    return [
        {
            "type": "function",
            "function": declaration.model_dump(),
        }
        for declaration in declarations
    ]


def _generate_response(messages: list[dict]) -> dict:
    payload = json.dumps(
        {
            "model": MODEL_NAME,
            "messages": messages,
            "tools": _ollama_tools(),
            "stream": False,
        }
    ).encode("utf-8")
    request = Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=120) as response:
            return json.loads(response.read())
    except URLError as error:
        raise RuntimeError(
            "Ollama is not running. Start Ollama and run `ollama pull qwen2.5:7b`."
        ) from error

def process_message(
    message: str,
    state: ConversationState,
):

    if not state.contents:
        state.system_instruction = build_system_prompt()

    state.contents.append({"role": "user", "content": message})
    messages = [
        {"role": "system", "content": state.system_instruction},
        *state.contents,
    ]

    while True:
        response = _generate_response(messages)
        assistant_message = response.get("message", {})
        state.contents.append(assistant_message)
        messages.append(assistant_message)

        function_calls = assistant_message.get("tool_calls", [])
        if not function_calls:
            return assistant_message.get("content", "")

        for tool_call in function_calls:
            function = tool_call.get("function", {})
            try:
                result = execute_tool(
                    function.get("name", ""),
                    function.get("arguments", {}),
                )
                tool_result = {"success": True, "result": result}

            except Exception as e:
                if function.get("name") == "create_appointment":
                    raise RuntimeError(
                        f"Appointment was not created in Google Calendar: {e}"
                    ) from e
                tool_result = {"success": False, "error": str(e)}

            tool_message = {
                "role": "tool",
                "content": json.dumps(tool_result),
            }
            state.contents.append(tool_message)
            messages.append(tool_message)
