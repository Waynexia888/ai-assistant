from typing import Any


SENSITIVE_KEYS = {
    "api_key",
    "authorization",
    "cookie",
    "password",
    "secret",
    "token",
}
REDACTED_VALUE = "[REDACTED]"


def sanitize_tool_data(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): (
                REDACTED_VALUE
                if str(key).lower() in SENSITIVE_KEYS
                else sanitize_tool_data(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [sanitize_tool_data(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_tool_data(item) for item in value]
    return value
