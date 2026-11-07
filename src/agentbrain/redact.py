"""Mask secret-looking values in file content before it reaches the model.

The model never needs a credential's value to work with a file: it needs to know
that one is there. Each masked value is replaced by a short fingerprint, so the
same secret in two places is recognisably the same without being readable.
"""
from __future__ import annotations

import hashlib
import re

SECRET_KEY = (r"(?:password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|secret[_-]?key|"
              r"client[_-]?secret|private[_-]?key|credentials?|(?<![a-z0-9])pass(?![a-z0-9]))")

# key: value / key = value / "key": "value", where the key names a secret.
KEY_VALUE = re.compile(
    # [ \t]* rather than \s*: a value is on the key's own line ("secret:\n  name: x" is not a pair).
    rf"""(?P<key>["']?[\w.-]*{SECRET_KEY}[\w.-]*["']?[ \t]*[:=][ \t]*)(?P<q>["']?)(?P<value>[^\s"'#,}}]+)(?P=q)""",
    re.IGNORECASE,
)
# user:password@host in URLs.
URL_PASSWORD = re.compile(r"(?P<pre>[a-z][a-z0-9+.-]*://[^\s:/@]+:)(?P<value>[^\s@/]+)(?P<post>@)", re.IGNORECASE)
PEM = re.compile(r"-----BEGIN (?P<kind>[A-Z ]*PRIVATE KEY)-----.*?-----END (?P=kind)-----", re.DOTALL)

# Values that point at a secret instead of being one.
REFERENCE = re.compile(
    r"^(?:\{|\[|\$\{|\$\(|<|%|secretKeyRef|valueFrom|vault:|ref\+|true$|false$|null$|none$|\*+$"
    r"|[a-z0-9_-]+(?:/[a-z0-9._-]+)+$)",  # a lowercase path such as a Vault key: where a secret is
)
# Keys that name where a secret is, not the secret itself.
REFERENCE_KEY = re.compile(r"(?:ref|name|names|path|file|key_?id|existing\w*|secret_?name|from)[\"']?[ \t]*[:=][ \t]*$", re.IGNORECASE)


def fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:8]


def mask(value: str) -> str:
    return f"«masked:{fingerprint(value)}»"


def redact(text: str) -> tuple[str, int]:
    count = 0

    def pem(m: re.Match[str]) -> str:
        nonlocal count
        count += 1
        return f"-----BEGIN {m['kind']}----- {mask(m[0])} -----END {m['kind']}-----"

    def key_value(m: re.Match[str]) -> str:
        nonlocal count
        value = m["value"]
        if len(value) < 4 or REFERENCE.match(value) or REFERENCE_KEY.search(m["key"]):
            return m[0]
        count += 1
        return f"{m['key']}{m['q']}{mask(value)}{m['q']}"

    def url(m: re.Match[str]) -> str:
        nonlocal count
        if REFERENCE.match(m["value"]):
            return m[0]
        count += 1
        return f"{m['pre']}{mask(m['value'])}{m['post']}"

    text = PEM.sub(pem, text)
    text = KEY_VALUE.sub(key_value, text)
    text = URL_PASSWORD.sub(url, text)
    return text, count
