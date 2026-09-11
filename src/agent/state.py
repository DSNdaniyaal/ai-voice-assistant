from dataclasses import dataclass, field


@dataclass
class ConversationState:
    # Ollama-compatible conversation history.
    contents: list[dict] = field(default_factory=list)
 
    # Set once, on the first turn, from build_system_prompt().
    system_instruction: str | None = None
 
    # Slot values extracted/confirmed over the course of the call.
    customer_name: str | None = None
    phone: str | None = None
    dog_name: str | None = None
 
    service_name: str | None = None
    appointment_id: str | None = None
 
    intent: str | None = None