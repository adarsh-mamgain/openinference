"""Tool definitions and handlers for function calling.

Tools are exposed to the local model via OpenAI's ``tools`` parameter and
``tool_choice="auto"``. Larger instruct models emit structured ``tool_calls``
in the completion; smaller quantized models like Qwen2.5-0.5B instead render
their tool call as text using the chat-template format::

    <tool_call>
    {"name": "get_weather", "arguments": {"location": "Tokyo"}}
    </tool_call>

We handle both: structured ``tool_calls`` when present, otherwise we parse the
Qwen text format, execute the handler, and feed the result back into the
conversation — mirroring OpenAI's tool-calling protocol.
"""

import json
import re

from inference_server.schemas import FunctionCall, Message, ToolCall


def _get_weather(location: str) -> dict[str, str]:
    return {"location": location, "conditions": "sunny", "temperature": "22C"}


def _add(a: int, b: int) -> dict[str, int]:
    return {"sum": a + b}


TOOL_HANDLERS: dict[str, callable] = {
    "get_weather": _get_weather,
    "add": _add,
}

_TOOL_NAMES = "|".join(TOOL_HANDLERS.keys())

# Matches the Qwen chat-template tool call: <tool_call>{"name": ...}</tool_call>.
# The small instruct model often doubles the braces ({{...}}), so we match one
# or more opening/closing braces and normalize them before JSON-decoding.
_TEXT_TOOL_RE = re.compile(
    r"<tool_call>\s*(\{+.*?\}+)\s*</tool_call>", re.DOTALL
)
# Also match a bare JSON tool-call object when the model omits the tags.
_BARE_TOOL_RE = re.compile(
    r'\{+\s*"name"\s*:\s*"(?:' + _TOOL_NAMES + r')"\s*,\s*"arguments"\s*:\s*\{+.*?\}+\s*\}+',
    re.DOTALL,
)

TOOL_SCHEMAS: list[dict] = [
    {
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
    {
        "type": "function",
        "function": {
            "name": "add",
            "description": "Add two integers together",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "integer", "description": "First addend"},
                    "b": {"type": "integer", "description": "Second addend"},
                },
                "required": ["a", "b"],
            },
        },
    },
]


def parse_text_tool_call(content: str) -> ToolCall | None:
    """Extract a Qwen chat-template tool call from model text output.

    Returns a :class:`ToolCall` if the text contains a tool call the server
    knows how to run, otherwise ``None``. A synthetic ``call_xxxx`` id is
    assigned because the text format carries none.
    """
    if not content:
        return None

    match = _TEXT_TOOL_RE.search(content) or _BARE_TOOL_RE.search(content)
    if match is None:
        return None

    # The small instruct model doubles braces inconsistently (e.g. opens the
    # outer object with {{ but closes with a single }). Try a few lenient
    # normalizations and use the first that is valid JSON.
    raw = match.group(1)
    if raw.startswith("{{") and not raw.endswith("}}"):
        raw = "{" + raw[2:]
    candidates = [
        raw,
        raw.replace("{{", "{").replace("}}", "}"),
        raw.replace("{{", "{"),
        raw.replace("}}", "}"),
    ]

    for candidate in candidates:
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        name = data.get("name")
        arguments = data.get("arguments")
        if name in TOOL_HANDLERS and isinstance(arguments, dict):
            import uuid

            return ToolCall(
                id=f"call_{uuid.uuid4().hex[:16]}",
                function=FunctionCall(name=name, arguments=json.dumps(arguments)),
            )

    return None


def run_tool(tool_call: ToolCall) -> str:
    """Execute a tool call and return its result as a JSON string."""
    name = tool_call.function.name
    args = json.loads(tool_call.function.arguments)
    handler = TOOL_HANDLERS[name]
    result = handler(**args)
    return json.dumps(result)


def tool_result_message(tool_call: ToolCall, result: str) -> Message:
    """Build the `role: tool` message the model expects after a tool call."""
    return Message(role="tool", content=result, tool_call_id=tool_call.id)
