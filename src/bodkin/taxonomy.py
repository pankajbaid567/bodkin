"""Skill taxonomy: loads data/skills.toml, compiles matchers, finds skills in text."""
from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "skills.toml"

# A skill token must not be glued to identifier characters. '.' is excluded before
# the alias so that "Node.js" does not also yield "js", and after the alias only
# when it continues a word ("python.org").
_BEFORE = r"(?<![A-Za-z0-9+#.])"
_AFTER = r"(?![A-Za-z0-9+#]|\.[A-Za-z0-9])"


@dataclass(frozen=True)
class Skill:
    id: str
    name: str
    cat: str
    arch: dict[str, float]
    aliases: tuple[str, ...] = ()
    cs: tuple[str, ...] = ()
    stop: tuple[str, ...] = ()


@dataclass(frozen=True)
class Hit:
    skill: str
    start: int
    end: int
    text: str


class TaxonomyError(ValueError):
    pass


def _alt(words) -> str:
    return "|".join(re.escape(w) for w in sorted(set(words), key=lambda w: (-len(w), w)))


class Taxonomy:
    def __init__(self, data: dict):
        meta = data.get("meta", {})
        self.archetypes: list[str] = list(meta.get("archetypes", []))
        self.shared: set[str] = {a.lower() for a in meta.get("shared_aliases", [])}
        self.roles: dict[str, list[str]] = {k: [x.lower() for x in v] for k, v in data.get("roles", {}).items()}
        self.cities: list[str] = [c.lower() for c in data.get("cities", {}).get("names", [])]
        self.skills: dict[str, Skill] = {}
        for sid, d in data.get("skills", {}).items():
            name = d.get("name", sid)
            aliases = list(d.get("aliases", ()))
            cs = tuple(d.get("cs", ()))
            # The display name is an alias too, unless it is an ordinary word that must
            # match case-sensitively (Go, React, Spring) or too short to be safe.
            if len(name) >= 3 and name not in cs and "(" not in name and name.lower() not in {a.lower() for a in aliases}:
                aliases.append(name)
            self.skills[sid] = Skill(
                id=sid, name=name, cat=d.get("cat", "other"), arch=dict(d.get("arch", {})),
                aliases=tuple(aliases), cs=cs, stop=tuple(d.get("stop", ())),
            )
        self._ci: dict[str, re.Pattern] = {}
        self._cs: dict[str, re.Pattern] = {}
        self._stop: dict[str, re.Pattern] = {}
        for sid, s in self.skills.items():
            if s.aliases:
                self._ci[sid] = re.compile(_BEFORE + "(?:" + _alt(s.aliases) + ")" + _AFTER, re.I)
            if s.cs:
                self._cs[sid] = re.compile(_BEFORE + "(?:" + _alt(s.cs) + ")" + _AFTER)
            if s.stop:
                self._stop[sid] = re.compile("(?:" + _alt(s.stop) + ")", re.I)
        # substring prefilter: a skill whose aliases do not occur in the text at all needs no regex scan
        self._needles: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
            sid: (tuple(a.lower() for a in s.aliases), tuple(s.cs)) for sid, s in self.skills.items()}
        self.known_tokens: set[str] = set()
        for s in self.skills.values():
            for a in (*s.aliases, *s.cs, s.name):
                for tok in re.findall(r"[A-Za-z0-9+#.]+", a):
                    self.known_tokens.add(tok.lower())

    # ---- loading ----
    @classmethod
    def load(cls, path: str | Path | None = None) -> "Taxonomy":
        p = Path(path) if path else DEFAULT_PATH
        with open(p, "rb") as f:
            return cls(tomllib.load(f))

    # ---- validation ----
    def validate(self) -> list[str]:
        errs: list[str] = []
        arch = set(self.archetypes)
        if not arch:
            errs.append("meta.archetypes is empty")
        for a in self.roles:
            if a not in arch:
                errs.append(f"roles.{a}: unknown archetype")
        owner: dict[str, str] = {}
        for sid, s in self.skills.items():
            if not s.name:
                errs.append(f"{sid}: empty name")
            for a, w in s.arch.items():
                if a not in arch:
                    errs.append(f"{sid}: unknown archetype {a!r}")
                if not (0 < w <= 1):
                    errs.append(f"{sid}: weight for {a} must be in (0,1], got {w}")
            for al in (*s.aliases,):
                k = al.lower()
                if k in self.shared:
                    continue
                if k in owner and owner[k] != sid:
                    errs.append(f"alias {al!r} claimed by both {owner[k]} and {sid}")
                owner[k] = sid
        return errs

    # ---- matching ----
    def find(self, text: str) -> dict[str, list[Hit]]:
        """All skill hits in text. A hit strictly inside a longer hit (of any skill) is
        dropped: "React Native" is not also "React", "Spring Boot" counts once.
        Stop phrases cancel their skill. O(n log n) in the number of hits."""
        raw: list[Hit] = []
        lower = text.lower()
        for sid in self.skills:
            ci_needles, cs_needles = self._needles[sid]
            if not (any(n in lower for n in ci_needles) or any(n in text for n in cs_needles)):
                continue
            covered = None
            if sid in self._stop:
                covered = bytearray(len(text))
                for m in self._stop[sid].finditer(text):
                    covered[m.start():m.end()] = b"\x01" * (m.end() - m.start())
            for pat in (self._ci.get(sid), self._cs.get(sid)):
                if pat is None:
                    continue
                for m in pat.finditer(text):
                    if covered is not None and any(covered[m.start():m.end()]):
                        continue
                    raw.append(Hit(sid, m.start(), m.end(), m.group(0)))
        # Sweep by start: a hit is contained in a strictly longer one iff an earlier-starting
        # hit reaches at least as far, or a same-start hit reaches further.
        raw.sort(key=lambda h: (h.start, -(h.end - h.start), h.skill))
        kept: list[Hit] = []
        reach_before = -1          # furthest end among hits that start before the current group
        i = 0
        while i < len(raw):
            j = i
            while j < len(raw) and raw[j].start == raw[i].start:
                j += 1
            group_end = raw[i].end            # the longest hit of this group comes first
            for h in raw[i:j]:
                if not (reach_before >= h.end or group_end > h.end):
                    kept.append(h)
            reach_before = max(reach_before, group_end)
            i = j
        out: dict[str, list[Hit]] = {}
        for h in sorted(kept, key=lambda h: (h.start, h.skill)):
            out.setdefault(h.skill, []).append(h)
        return out
