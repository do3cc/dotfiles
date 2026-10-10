"""Parse the logfmt lines the tools write (shared by several test modules)."""

import json
import re

_LOGFMT_PAIR = re.compile(r'(\w+)=("(?:[^"\\]|\\.)*"|\S*)')


def parse_logfmt(line: str) -> dict[str, str]:
    """Parse one logfmt line into a dict of strings (quoted values are unescaped)."""
    entry: dict[str, str] = {}
    for key, raw in _LOGFMT_PAIR.findall(line):
        entry[key] = json.loads(raw) if raw.startswith('"') else raw
    return entry
