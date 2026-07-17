import logging
import re
from typing import Any


SECRET_RE = re.compile(
    r"(?i)(sk-[a-z0-9_\-]{12,}|"
    r"api[_\- ]?key['\"]?\s*[:=]\s*['\"]?[^'\"\s,]{8,}|"
    r"authorization['\"]?\s*[:=]\s*['\"]?bearer\s+[^'\"\s,]{8,})"
)


def redact_secret(value: Any) -> str:
    text = str(value)

    def replace(match: re.Match[str]) -> str:
        raw = match.group(0)
        if len(raw) <= 10:
            return "***"
        return f"{raw[:4]}...{raw[-4:]}"

    return SECRET_RE.sub(replace, text)


class SecretRedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_secret(record.msg)
        if record.args:
            record.args = tuple(redact_secret(arg) for arg in record.args)
        return True


def install_log_redaction() -> None:
    root = logging.getLogger()
    root.addFilter(SecretRedactionFilter())
    for handler in root.handlers:
        handler.addFilter(SecretRedactionFilter())
