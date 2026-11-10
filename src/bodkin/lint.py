"""Wording lint and the number allow-list. Both exist so a bullet cannot drift from its evidence."""
from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "lint.toml"

# A number token: digits with optional thousands commas and decimals, not glued to a
# letter before it (so p99, k6, R2, v8 are not numbers).
_NUM = re.compile(r"(?<![A-Za-z0-9.])\d[\d,]*(?:\.\d+)?")


@dataclass(frozen=True)
class Issue:
    code: str      # BANNED | WEAK | LONG | MARKUP
    message: str


def numbers_in(text: str) -> list[str]:
    """Numeric tokens of a text, with trailing commas stripped, in order of appearance."""
    out = []
    for m in _NUM.finditer(text):
        tok = m.group(0).rstrip(",")
        if tok:
            out.append(tok)
    return out


def strip_markup(text: str) -> str:
    return text.replace("**", "")


class Linter:
    def __init__(self, max_len: int, banned: list[str], weak: list[str]):
        self.max_len, self.banned, self.weak = max_len, [b.lower() for b in banned], [w.lower() for w in weak]

    @classmethod
    def load(cls, path: str | Path | None = None) -> "Linter":
        with open(Path(path) if path else DEFAULT_PATH, "rb") as f:
            d = tomllib.load(f).get("lint", {})
        return cls(int(d.get("max_len", 175)), list(d.get("banned", [])), list(d.get("weak_openers", [])))

    def check(self, text: str, allow: tuple[str, ...] = ()) -> list[Issue]:
        issues: list[Issue] = []
        plain = strip_markup(text)
        low = plain.lower()
        allowed = {a.lower() for a in allow}
        for b in self.banned:
            if b in low and b not in allowed:
                issues.append(Issue("BANNED", f"contains {b!r}, which this portfolio does not claim"))
        for w in self.weak:
            if low.startswith(w) and w not in allowed:
                issues.append(Issue("WEAK", f"starts with weak opener {w.strip()!r}"))
        if len(plain) > self.max_len:
            issues.append(Issue("LONG", f"{len(plain)} characters (limit {self.max_len}); resume lines should fit one or two lines"))
        if text.count("**") % 2:
            issues.append(Issue("MARKUP", "unbalanced ** bold markers"))
        return issues
