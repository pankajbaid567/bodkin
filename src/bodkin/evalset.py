"""Labelled JD evaluation. A fixture is a text file with a small front matter:

    ---
    name: Atlassian SWE intern (paraphrased from the report)
    must: cairn
    one_of: pitbook, taskflow, cache-cluster; vitram, taskflow
    must_not: hackathons
    ---
    <JD text>

`must`: each id must be among the chosen projects. `one_of`: groups separated by ';',
at least one member of every group must be chosen. `must_not`: none of these may be chosen. `gap`: each listed skill id must appear in the
gap analysis (no evidence, or claimable), i.e. the tool must not hide it.
Labels were written by the author before tuning; they check sanity and regressions,
not general accuracy (docs/testing.md)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Case:
    path: str
    name: str
    text: str
    must: list[str] = field(default_factory=list)
    one_of: list[list[str]] = field(default_factory=list)
    must_not: list[str] = field(default_factory=list)
    gap: list[str] = field(default_factory=list)
    meta: dict[str, str] = field(default_factory=dict)


def split_front_matter(raw: str) -> tuple[dict[str, str], str]:
    lines = raw.replace("\r\n", "\n").split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, raw
    meta: dict[str, str] = {}
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return meta, "\n".join(lines[i + 1:])
        if ":" in lines[i]:
            k, v = lines[i].split(":", 1)
            meta[k.strip().lower()] = v.strip()
    return {}, raw


def _ids(v: str) -> list[str]:
    return [x.strip() for x in v.split(",") if x.strip()]


def load_case(path: Path) -> Case:
    meta, text = split_front_matter(path.read_text(encoding="utf-8"))
    return Case(path=str(path), name=meta.get("name", path.stem), text=text, must=_ids(meta.get("must", "")),
                one_of=[_ids(g) for g in meta.get("one_of", "").split(";") if g.strip()], must_not=_ids(meta.get("must_not", "")), gap=_ids(meta.get("gap", "")), meta=meta)


def load_dir(d: Path) -> list[Case]:
    return [load_case(p) for p in sorted(d.glob("*.txt"))]


def judge(case: Case, chosen: list[str], gap_ids: set[str] | None = None) -> list[str]:
    """Return the list of violated constraints (empty = pass)."""
    bad = []
    for m in case.must:
        if m not in chosen:
            bad.append(f"must include {m}")
    for grp in case.one_of:
        if not any(g in chosen for g in grp):
            bad.append("needs one of: " + ", ".join(grp))
    for m in case.must_not:
        if m in chosen:
            bad.append(f"must not include {m}")
    for g in case.gap:
        if gap_ids is not None and g not in gap_ids:
            bad.append(f"gap analysis should list {g}")
    return bad
