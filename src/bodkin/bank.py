"""The bank: profile, items (projects, experience, achievements), claims, roadmap."""
from __future__ import annotations

import glob
import re
import tomllib
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from .lint import Linter, numbers_in
from .taxonomy import Taxonomy

KINDS = ("project", "experience", "achievement")
STATUSES = ("shipped", "wip", "archived")
PROOF = ("proven", "reported", "pending")
_ID = re.compile(r"^[a-z0-9][a-z0-9\-]*$")


class BankError(ValueError):
    def __init__(self, issues: list["Issue"]):
        super().__init__("; ".join(f"{i.where}: {i.message}" for i in issues[:8]) + (" ..." if len(issues) > 8 else ""))
        self.issues = issues


@dataclass(frozen=True)
class Issue:
    level: str      # error | warn
    where: str
    message: str


@dataclass(frozen=True)
class Proof:
    status: str = "pending"
    command: str = ""
    artifact: str = ""
    date: str = ""
    limits: str = ""
    note: str = ""


@dataclass(frozen=True)
class Claim:
    id: str
    item_id: str
    text: str
    variants: dict[str, str]
    numbers: tuple[str, ...]
    skills: dict[str, float]
    archetypes: dict[str, float]
    group: str
    proof: Proof
    allow: tuple[str, ...] = ()

    @property
    def uid(self) -> str:
        return f"{self.item_id}/{self.id}"

    def all_texts(self) -> list[str]:
        return [self.text, *self.variants.values()]


@dataclass(frozen=True)
class Item:
    id: str
    kind: str
    name: str
    title: str
    subtitle: str
    status: str
    date: str
    end: str                      # YYYY-MM, used for recency
    links: dict[str, str]
    repo: str
    archetypes: dict[str, float]
    skills: dict[str, float]
    tech: tuple[str, ...]
    claims: tuple[Claim, ...]
    note: str = ""
    path: str = ""


@dataclass(frozen=True)
class Planned:
    id: str
    name: str
    summary: str
    skills: dict[str, float]
    archetypes: dict[str, float]


@dataclass
class Bank:
    root: Path
    person: dict
    skills: dict[str, list[str]]          # resume skills section: category -> display names
    items: dict[str, Item]
    roadmap: list[Planned]

    # ---- loading ----
    @classmethod
    def load(cls, root: str | Path) -> "Bank":
        root = Path(root).resolve()
        issues: list[Issue] = []

        def read(p: Path) -> dict:
            try:
                with open(p, "rb") as f:
                    return tomllib.load(f)
            except (OSError, tomllib.TOMLDecodeError) as e:
                issues.append(Issue("error", str(p.relative_to(root)) if p.is_relative_to(root) else str(p), f"cannot read: {e}"))
                return {}

        prof = read(root / "profile.toml")
        person = dict(prof.get("person", {}))
        skills = {k: list(v) for k, v in prof.get("skills", {}).items()}
        items: dict[str, Item] = {}
        for p in sorted((root / "items").glob("*.toml")):
            d = read(p)
            if not d:
                continue
            iid = d.get("id", p.stem)
            claims = []
            for i, c in enumerate(d.get("claims", [])):
                claims.append(Claim(
                    id=c.get("id", f"c{i+1}"), item_id=iid, text=c.get("text", ""), variants=dict(c.get("variants", {})),
                    numbers=tuple(str(x) for x in c.get("numbers", [])), skills=dict(c.get("skills", {})),
                    archetypes=dict(c.get("archetypes", {})), group=c.get("group", ""),
                    proof=Proof(**{k: str(v) for k, v in c.get("proof", {}).items() if k in Proof.__dataclass_fields__}),
                    allow=tuple(c.get("allow", ())),
                ))
            if iid in items:
                issues.append(Issue("error", iid, f"duplicate item id (also in {items[iid].path})"))
            items[iid] = Item(
                id=iid, kind=d.get("kind", "project"), name=d.get("name", iid), title=d.get("title", d.get("name", iid)),
                subtitle=d.get("subtitle", ""), status=d.get("status", "shipped"), date=d.get("date", ""), end=d.get("end", ""),
                links=dict(d.get("links", {})), repo=d.get("repo", ""), archetypes=dict(d.get("archetypes", {})),
                skills=dict(d.get("skills", {})), tech=tuple(d.get("tech", ())), claims=tuple(claims), note=d.get("note", ""),
                path=str(p.relative_to(root)),
            )
        road = []
        rp = root / "roadmap.toml"
        if rp.exists():
            for r in read(rp).get("planned", []):
                road.append(Planned(id=r.get("id", ""), name=r.get("name", ""), summary=r.get("summary", ""),
                                    skills=dict(r.get("skills", {})), archetypes=dict(r.get("archetypes", {}))))
        if issues:
            raise BankError(issues)
        return cls(root=root, person=person, skills=skills, items=items, roadmap=road)

    # ---- validation ----
    def validate(self, tax: Taxonomy, linter: Linter, strict: bool = False, today: date | None = None) -> list[Issue]:
        out: list[Issue] = []
        arch = set(tax.archetypes)

        def err(where, msg):
            out.append(Issue("error", where, msg))

        def warn(where, msg):
            out.append(Issue("error" if strict else "warn", where, msg))

        if not self.person.get("name"):
            err("profile", "person.name is required")
        if not isinstance(self.person.get("batch"), int):
            warn("profile", "person.batch (graduation year) is missing; eligibility checks will be skipped")
        if not self.items:
            err("bank", "no items found in items/")
        for cat, names in self.skills.items():
            for n in names:
                if not tax.find(n):
                    warn("profile.skills", f"{n!r} ({cat}) is not in the taxonomy, so it cannot be matched to JDs")

        for it in self.items.values():
            w = it.id
            if not _ID.match(it.id):
                err(w, "id must be lowercase letters, digits and dashes")
            if it.kind not in KINDS:
                err(w, f"kind must be one of {KINDS}")
            if it.status not in STATUSES:
                err(w, f"status must be one of {STATUSES}")
            if not it.title:
                err(w, "title is required")
            if it.kind in ("project", "experience") and not it.date:
                err(w, "date is required for projects and experience")
            if it.end and not re.fullmatch(r"\d{4}-\d{2}", it.end):
                err(w, "end must look like 2026-11")
            for a, v in it.archetypes.items():
                if a not in arch:
                    err(w, f"unknown archetype {a!r}")
                if not (0 < v <= 1):
                    err(w, f"archetype {a} strength must be in (0,1]")
            for s, v in it.skills.items():
                if s not in tax.skills:
                    err(w, f"unknown skill id {s!r} (see data/skills.toml)")
                if not (0 < v <= 1):
                    err(w, f"skill {s} strength must be in (0,1]")
            if not it.claims:
                warn(w, "no claims; this item can never be selected")
            seen = set()
            for c in it.claims:
                cw = c.uid
                if c.id in seen:
                    err(cw, "duplicate claim id")
                seen.add(c.id)
                if not c.text.strip():
                    err(cw, "text is empty")
                if c.proof.status not in PROOF:
                    err(cw, f"proof.status must be one of {PROOF}")
                if c.proof.status == "proven" and not (c.proof.command and c.proof.artifact):
                    err(cw, "a proven claim needs proof.command and proof.artifact")
                if c.proof.status == "reported" and not c.proof.note:
                    warn(cw, "a reported claim should say where it comes from in proof.note")
                for a in c.archetypes:
                    if a not in arch:
                        err(cw, f"unknown archetype {a!r}")
                for s in c.skills:
                    if s not in tax.skills:
                        err(cw, f"unknown skill id {s!r}")
                for a in c.variants:
                    if a not in arch:
                        err(cw, f"variant key {a!r} is not an archetype")
                allowed = set(c.numbers)
                for t in c.all_texts():
                    for n in numbers_in(t):
                        if n not in allowed:
                            err(cw, f"number {n!r} appears in the text but is not declared in numbers = [...]")
                    for iss in linter.check(t, c.allow):
                        (err if iss.code in ("BANNED", "MARKUP") else warn)(cw, f"{iss.code}: {iss.message}")
                for n in allowed:
                    if not any(n in numbers_in(t) for t in c.all_texts()):
                        warn(cw, f"declared number {n!r} does not appear in any text")
                if c.proof.date:
                    try:
                        d = date.fromisoformat(c.proof.date)
                        if today and (today - d).days > 120:
                            warn(cw, f"proof is {(today - d).days} days old; re-run {c.proof.command or 'the proof'}")
                    except ValueError:
                        err(cw, "proof.date must be YYYY-MM-DD")
        for p in self.roadmap:
            for s in p.skills:
                if s not in tax.skills:
                    err(f"roadmap/{p.id}", f"unknown skill id {s!r}")
        return out

    # ---- proof paths ----
    def check_proofs(self) -> list[Issue]:
        """Check that each claim's proof artifact exists in its item's repo."""
        out: list[Issue] = []
        for it in self.items.values():
            if not it.repo:
                continue
            repo = (self.root / it.repo).resolve()
            if not repo.is_dir():
                out.append(Issue("warn", it.id, f"repo {it.repo!r} not found at {repo}"))
                continue
            for c in it.claims:
                art = c.proof.artifact
                if not art or c.proof.status == "pending":
                    continue
                if not glob.glob(str(repo / art)):
                    out.append(Issue("error" if c.proof.status == "proven" else "warn", c.uid, f"proof artifact {art!r} not found in {repo.name}"))
        return out

    # ---- helpers ----
    def eligible_claims(self, item: Item, include_pending: bool = False) -> list[Claim]:
        return [c for c in item.claims if c.proof.status != "pending" or include_pending]
