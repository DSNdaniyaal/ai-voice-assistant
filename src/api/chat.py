import json
from pathlib import Path
from threading import Lock

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.agent.reception_agent import process_message
from src.agent.state import ConversationState
from src.tools.vapi_tools import execute_vapi_tool


class ChatRequest(BaseModel):
    conversation_id: str = Field(min_length=1)
    message: str = Field(min_length=1)


class ChatResponse(BaseModel):
    conversation_id: str
    response: str


app = FastAPI(title="Maple Street Dog Grooming API")

FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

_conversations: dict[str, ConversationState] = {}
_conversations_lock = Lock()


def _get_conversation(conversation_id: str) -> ConversationState:
    with _conversations_lock:
        return _conversations.setdefault(conversation_id, ConversationState())


@app.get("/")
def home():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """Send a message to the receptionist while preserving conversation state."""
    try:
        state = _get_conversation(request.conversation_id)
        response = process_message(request.message, state)
    except Exception as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    return ChatResponse(
        conversation_id=request.conversation_id,
        response=response,
    )

@app.post("/vapi/tools")
async def vapi_tools(request: Request):
    body = await request.json()

    print("\n" + "=" * 70)
    print("VAPI TOOL REQUEST")
    print("=" * 70)
    print(json.dumps(body, indent=2, default=str))

    message = body.get("message", {})
    tool_calls = message.get("toolCallList", [])

    print("\nTOOL CALLS:")
    print(json.dumps(tool_calls, indent=2, default=str))

    results = []

    for tool_call in tool_calls:
        print("\n" + "-" * 70)
        print("RAW TOOL CALL")
        print("-" * 70)
        print(json.dumps(tool_call, indent=2, default=str))

        tool_call_id = tool_call.get("id", "")

        function = tool_call.get("function") or {}

        tool_name = (
            tool_call.get("name")
            or function.get("name")
            or ""
        )

        arguments = (
            tool_call.get("arguments")
            or function.get("arguments")
            or function.get("parameters")
            or {}
        )

        print("\nEXTRACTED:")
        print("ID:", tool_call_id)
        print("NAME:", tool_name)
        print("ARGUMENTS:", arguments)

        if not tool_name:
            results.append({
                "toolCallId": tool_call_id,
                "result": json.dumps({
                    "success": False,
                    "error": "Tool name was missing from Vapi request."
                })
            })
            continue

        try:
            result = execute_vapi_tool(
                tool_name=tool_name,
                arguments=arguments,
            )

            print("\nTOOL RESULT:")
            print(json.dumps(result, indent=2, default=str))

            results.append({
                "toolCallId": tool_call_id,
                "result": json.dumps(result, default=str),
            })

        except Exception as error:
            print("\nTOOL ERROR:")
            print(repr(error))

            results.append({
                "toolCallId": tool_call_id,
                "result": json.dumps({
                    "success": False,
                    "error": str(error),
                }),
            })

    response = {
        "results": results
    }

    print("\n" + "=" * 70)
    print("VAPI TOOL RESPONSE")
    print("=" * 70)
    print(json.dumps(response, indent=2, default=str))

    return response

@app.delete("/chat/{conversation_id}", status_code=204)
def reset_chat(conversation_id: str):
    with _conversations_lock:
        _conversations.pop(conversation_id, None)