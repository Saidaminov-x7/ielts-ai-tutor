"""Report likely hard-coded secrets by file and type without printing values."""

import re
import sys
from pathlib import Path

PATTERNS = {
    "Telegram bot token": re.compile(r"\b\d{7,12}:[A-Za-z0-9_-]{30,}\b"),
    "OpenAI API key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    "Private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}
IGNORE = {".git", ".venv", "venv", "__pycache__", ".pytest_cache"}


def main() -> int:
    found = 0
    for path in Path(".").rglob("*"):
        if not path.is_file() or any(part in IGNORE for part in path.parts):
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for kind, pattern in PATTERNS.items():
            for match in pattern.finditer(content):
                line = content.count("\n", 0, match.start()) + 1
                print(f"Найден потенциальный секрет: {path}:{line} ({kind}); значение скрыто")
                found += 1
    if not found:
        print("No likely hard-coded secrets found in project text files.")
    return int(found > 0)


if __name__ == "__main__":
    sys.exit(main())
