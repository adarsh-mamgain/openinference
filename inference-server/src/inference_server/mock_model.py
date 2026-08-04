"""A tiny in-memory model that stands in for a real LLM backend.

For learning purposes it does not call an external API. It echoes the last
user message back with a friendly prefix, so the whole request path
(schema -> route -> model -> response) is exercised end to end.

It also provides a simple token counter so the response `usage` field
contains believable numbers, plus a small tool registry that demonstrates
function calling without a real model.
"""

import json

from inference_server.schemas import FunctionCall, Message, ToolCall


def count_tokens(text: str) -> int:
    """Rough token estimate: ~4 characters per token."""
    return max(1, len(text) // 4)


def generate(messages: list[Message], max_tokens: int = 64) -> tuple[str, int]:
    """Return (completion_text, completion_tokens) for a conversation."""
    last_user = next(
        (m.content or "" for m in reversed(messages) if m.role == "user"),
        "Hello!",
    )
    reply = f"Echo: {last_user}"
    completion = reply[: max_tokens * 4]
    return completion, count_tokens(completion)


def stream_chunks(messages: list[Message], max_tokens: int = 64) -> list[str]:
    """Split the full completion into word-level chunks for streaming."""
    completion, _ = generate(messages, max_tokens=max_tokens)
    return completion.split(" ")


# Tool registry: name -> handler. Handlers take JSON-decoded arguments and
# return a JSON-serializable result, mirroring how real function calling works.
def _get_weather(location: str) -> dict[str, str]:
    return {"location": location, "conditions": "sunny", "temperature": "22C"}


def _add(a: int, b: int) -> dict[str, int]:
    return {"sum": a + b}


TOOL_HANDLERS: dict[str, callable] = {
    "get_weather": _get_weather,
    "add": _add,
}

TOOL_SCHEMAS: dict[str, dict] = {
    "get_weather": {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City name"}
                },
                "required": ["location"],
            },
        },
    },
    "add": {
        "type": "function",
        "function": {
            "name": "add",
            "description": "Add two integers",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "integer"},
                    "b": {"type": "integer"},
                },
                "required": ["a", "b"],
            },
        },
    },
}


def tool_trigger(user_text: str) -> tuple[str, dict] | None:
    """Decide whether the last user message should trigger a tool call.

    Returns (function_name, arguments) or None. This stands in for the model's
    own decision to emit a tool call.
    """
    lowered = user_text.lower()
    if "weather" in lowered:
        return "get_weather", {"location": user_text.split()[-1]}
    if lowered.startswith("add ") or " plus " in lowered:
        numbers = [int(part) for part in lowered.split() if part.lstrip("-").isdigit()]
        if len(numbers) == 2:
            return "add", {"a": numbers[0], "b": numbers[1]}
    return None


def run_tool(name: str, arguments: dict) -> dict:
    """Execute a registered tool and return its result."""
    handler = TOOL_HANDLERS[name]
    return handler(**arguments)


def maybe_tool_call(messages: list[Message], tool_call_id: str) -> tuple[ToolCall | None, str]:
    """Return (tool_call, finish_reason). finish_reason is 'tool_calls' when a
    tool should be called, otherwise 'stop'."""
    last_user = next(
        (m.content or "" for m in reversed(messages) if m.role == "user"),
        "",
    )
    triggered = tool_trigger(last_user)
    if triggered is None:
        return None, "stop"

    name, arguments = triggered
    tool_call = ToolCall(
        id=tool_call_id,
        function=FunctionCall(name=name, arguments=json.dumps(arguments)),
    )
    return tool_call, "tool_calls"
