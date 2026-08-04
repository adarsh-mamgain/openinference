"""A tiny in-memory model that stands in for a real LLM backend.

For learning purposes it does not call an external API. It echoes the last
user message back with a friendly prefix, so the whole request path
(schema -> route -> model -> response) is exercised end to end.

It also provides a simple token counter so the response `usage` field
contains believable numbers.
"""

from inference_server.schemas import Message


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
