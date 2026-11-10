"""Job-description analysis: skill weights, archetype scores, eligibility facts."""
from __future__ import annotations

import bisect
import math
import re
import unicodedata
from dataclasses import dataclass, field

from .taxonomy import Taxonomy

SECTION_WEIGHT = {"required": 1.0, "responsibilities": 0.8, "body": 0.7, "preferred": 0.5, "about": 0.2}

# Order matters: the most specific kind is tested first ("preferred qualifications"
# contains "qualifications").
_MARKERS = [
    ("preferred", ["preferred", "nice to have", "nice-to-have", "good to have", "good-to-have", "bonus", "desirable", "added advantage",
                   "extra credit", "great if", "bonus points", "it would be great", "plus points"]),
    ("about", ["about us", "about the company", "who we are", "our mission", "why join", "why us", "benefits", "perks", "what we offer",
               "life at", "our culture", "equal opportunity", "diversity", "compensation", "how to apply", "our values", "about the team"]),
    ("required", ["requirements", "requirement", "qualifications", "qualification", "must have", "must-have", "what you need",
                  "what you'll need", "what you will need", "you have", "you bring", "what we're looking for", "what we are looking for",
                  "who you are", "skills required", "required skills", "minimum qualifications", "basic qualifications", "eligibility",
                  "technical skills", "key skills", "you should have", "what you should have", "about you", "your profile",
                  "candidate profile", "skills and experience", "skills & experience", "what we expect", "ideal candidate"]),
    ("responsibilities", ["responsibilities", "responsibility", "what you'll do", "what you will do", "what you’ll do", "your role",
                          "the role", "role overview", "about the role", "job description", "day to day", "day-to-day", "key responsibilities",
                          "in this role", "what you'll be doing", "what you will be doing", "your impact", "the opportunity", "overview"]),
]

_INLINE_WEAK = ["a plus", "is a plus", "nice to have", "preferred", "bonus", "good to have", "added advantage", "an advantage", "is an advantage", "desirable"]
_INLINE_STRONG = ["must", "required", "mandatory", "strong", "proficient", "proficiency", "hands-on", "expert", "deep understanding",
                  "solid understanding", "solid foundation", "strong foundation"]

_BULLET = re.compile(r"^[\s\-\*•●▪‣·–—>#]+")

_STOP_CAPS = set("""
We The You Our Your They This That These Those It Its A An And Or But If In On At By For From Of To With Without As Is Are Be Been
Will Would Can Could Should May Might Must Have Has Had Do Does Did Not No Yes All Any Some Each Every More Most Other Such Than Then
Experience Strong Knowledge Understanding Good Excellent Ability Able Skills Skill Software Engineer Engineers Engineering Developer Development
Team Teams Company Role Work Working Join Looking Candidate Candidates Computer Science Bachelor Bachelors Degree Years Year Intern Interns
Internship India Please Apply Job Description Requirements Responsibilities Qualifications Preferred Benefits Equal Opportunity Employer
Responsibilities Familiarity Proficiency Hands Experience Required Plus Bonus Good Nice Great Opportunity Opportunities Build Design Develop
Collaborate Write Work Participate Contribute Ensure Deliver Support Manage Lead Drive Own Learn Understand Help Use Using Including Such
Monday Tuesday Wednesday Thursday Friday January February March April May June July August September October November December
Location Duration Stipend Salary Batch Graduates Graduate Graduating Eligibility Education Fresher Freshers Fulltime Full Time Part Remote Hybrid
Bengaluru Bangalore Hyderabad Pune Mumbai Chennai Delhi Gurgaon Gurugram Noida Kolkata Ahmedabad
Who What When Where Why How Which While During About Within Across Over Under Between Through Into Also Both Either Well Very Just Only
Ideal Basic Minimum Additional Key Core Senior Junior Associate Staff Principal Manager Intern Apprentice Trainee
""".split())


@dataclass
class Fact:
    kind: str          # cgpa | percent | batch | role | experience | location | duration | stipend
    value: object
    text: str          # the matched text
    line: int
    confidence: float  # 0..1: how sure the extraction is


@dataclass
class JDProfile:
    title: str
    skill_weights: dict[str, float]
    skill_counts: dict[str, int]
    evidence: dict[str, list[tuple[str, str, float]]]   # skill -> [(section, snippet, weight)]
    archetypes: dict[str, float]                          # normalised, max 1
    facts: list[Fact]
    unknown_terms: list[tuple[str, int]]
    sections: dict[str, int]                              # lines per section kind
    chars: int = 0

    def top_skills(self, n: int = 10) -> list[tuple[str, float]]:
        return sorted(self.skill_weights.items(), key=lambda kv: (-kv[1], kv[0]))[:n]


def normalize(text: str) -> str:
    t = unicodedata.normalize("NFKC", text)
    t = t.replace("\r\n", "\n").replace("\r", "\n").replace(" ", " ").replace("\t", " ")
    t = re.sub(r"[ ]{2,}", " ", t)
    return t


def _header_kind(line: str) -> str | None:
    raw = _BULLET.sub("", line).strip().strip(":*_ ").lower()
    if not raw or len(raw) > 70 or raw.endswith("."):
        return None
    # A header is short and consists mostly of the marker; "Experience with X is preferred" is not a header.
    if len(raw.split()) > 8:
        return None
    for kind, marks in _MARKERS:
        if any(raw == m or raw.startswith(m) or raw.endswith(m) or m in raw for m in marks):
            return kind
    return None


def _line_sections(lines: list[str]) -> list[str]:
    cur = "body"
    out = []
    for ln in lines:
        k = _header_kind(ln)
        if k is not None and (ln.strip().endswith(":") or len(ln.strip()) <= 45 or ln.lstrip().startswith("#")):
            cur = k
            out.append("header")
            continue
        out.append(cur)
    return out


def _line_weight(line: str, section: str) -> float:
    w = SECTION_WEIGHT.get(section, 0.7)
    low = line.lower()
    if section != "about":
        if any(m in low for m in _INLINE_WEAK):
            w = min(w, 0.5)
        elif any(m in low for m in _INLINE_STRONG):
            w = max(w, 0.9)
    return w


# ---------------- eligibility facts ----------------
_NUM = r"(\d{1,2}(?:\.\d{1,3})?)"
_CGPA_A = re.compile(r"(?:c\.?g\.?p\.?a\.?|gpa|cpi)\s*(?:of|:|-|–|>=|≥|above|minimum|min\.?|at least|greater than|more than)?\s*(?:of\s*)?" + _NUM
                     + r"\s*(\+|and above|or above|or higher|and higher|/\s*10|/\s*4|out of 10|out of 4)?", re.I)
_CGPA_B = re.compile(_NUM + r"\s*(\+|and above|or above|or higher)?\s*(?:c\.?g\.?p\.?a\.?|gpa|cpi)\b", re.I)
_PERCENT = re.compile(r"(\d{2}(?:\.\d+)?)\s*%", re.I)
_PERCENT_CTX = re.compile(r"marks|aggregate|percentage|academic|throughout|10th|12th|graduation|cgpa|score|grades", re.I)
_BATCH_A = re.compile(r"(?:class of|batch of|batch|graduating in|graduate in|graduating|graduation(?: year)?(?: in| by)?|passing out(?: in)?|pass[- ]out(?: in)?|"
                      r"expected graduation|degree in|complet\w+ (?:their|your|the) (?:degree|course|studies)(?: in| by)?)\D{0,30}?(20\d\d)(?:\s*(?:-|–|to|and|/)\s*(20\d\d))?", re.I)
_BATCH_B = re.compile(r"(20\d\d)\s*(?:batch|graduates|graduating|passouts?|pass-outs?|grads|passing out|class)", re.I)
_ROLE = re.compile(r"\b(summer intern(?:ship)?|winter intern(?:ship)?|internship|intern|new grad(?:uate)?s?|fresher|freshers|entry[- ]level|"
                   r"sde[- ]?(?:1|i)\b|sde intern|software engineer intern|graduate engineer trainee|trainee|apprentice|campus hire)", re.I)
_EXPERIENCE = re.compile(r"(\d{1,2})\s*(?:\+|[-–]|to)?\s*(\d{1,2})?\s*\+?\s*years?(?: of)?(?: relevant)?(?: work)? experience", re.I)
_DURATION = re.compile(r"(\d{1,2})\s*(?:[-–]|to)?\s*(\d{1,2})?\s*(?:months?|weeks?)\b", re.I)
_STIPEND = re.compile(r"(?:stipend|salary|ctc|compensation|pay)[^.\n]{0,45}?(?:₹|rs\.?|inr|\$|usd)\s*[\d,\.]+(?:\s*(?:k|lpa|lakhs?))?(?:\s*(?:[-–]|to)\s*[\d,\.]+(?:\s*(?:k|lpa|lakhs?))?)?", re.I)


def _facts(lines: list[str], tax: Taxonomy) -> list[Fact]:
    facts: list[Fact] = []
    city_re = re.compile(r"(?<![A-Za-z])(" + "|".join(re.escape(c) for c in sorted(tax.cities, key=len, reverse=True)) + r")(?![A-Za-z])", re.I) if tax.cities else None
    seen_loc: set[str] = set()
    for i, ln in enumerate(lines):
        for m in _CGPA_A.finditer(ln):
            v = float(m.group(1)); suf = (m.group(2) or "").lower().replace(" ", "")
            scale = 4 if ("/4" in suf or "outof4" in suf or (v <= 4.5 and not suf)) else 10
            if 0 < v <= 10:
                val = v if scale == 10 else round(v / 4 * 10, 2)
                facts.append(Fact("cgpa", val, m.group(0).strip(), i, 0.85 if scale == 10 else 0.5))
        for m in _CGPA_B.finditer(ln):
            v = float(m.group(1))
            if 0 < v <= 10:
                val = v if v > 4.5 else round(v / 4 * 10, 2)
                facts.append(Fact("cgpa", val, m.group(0).strip(), i, 0.8 if v > 4.5 else 0.5))
        if _PERCENT_CTX.search(ln):
            for m in _PERCENT.finditer(ln):
                v = float(m.group(1))
                if 40 <= v <= 100 and not any(f.kind == "cgpa" and f.line == i for f in facts):
                    facts.append(Fact("percent", v, m.group(0).strip(), i, 0.6))
        for m in _BATCH_A.finditer(ln):
            ys = [int(g) for g in m.groups() if g]
            facts.append(Fact("batch", (min(ys), max(ys)), m.group(0).strip(), i, 0.85))
        for m in _BATCH_B.finditer(ln):
            y = int(m.group(1)); facts.append(Fact("batch", (y, y), m.group(0).strip(), i, 0.8))
        for m in _ROLE.finditer(ln):
            facts.append(Fact("role", m.group(1).lower(), m.group(0).strip(), i, 0.7))
        for m in _EXPERIENCE.finditer(ln):
            lo = int(m.group(1)); hi = int(m.group(2)) if m.group(2) else None
            facts.append(Fact("experience", (lo, hi), m.group(0).strip(), i, 0.8))
        for m in _DURATION.finditer(ln):
            if re.search(r"intern|duration|period|stipend|contract|term|full[- ]time", ln, re.I):
                facts.append(Fact("duration", m.group(0).strip(), m.group(0).strip(), i, 0.6))
        for m in _STIPEND.finditer(ln):
            facts.append(Fact("stipend", m.group(0).strip(), m.group(0).strip(), i, 0.6))
        if city_re:
            for m in city_re.finditer(ln):
                c = m.group(1).lower()
                if c not in seen_loc:
                    seen_loc.add(c)
                    facts.append(Fact("location", c, m.group(0), i, 0.7))
    # keep the first occurrence of identical (kind, value)
    out, seen = [], set()
    for f in facts:
        k = (f.kind, f.value)
        if k not in seen:
            seen.add(k)
            out.append(f)
    return out


def check_eligibility(facts: list[Fact], person: dict) -> list[dict]:
    """Compare extracted facts with the profile. Advice only: extraction from free text can be wrong."""
    res: list[dict] = []
    cgpa = person.get("cgpa")
    batch = person.get("batch")
    locs = {x.lower() for x in person.get("locations_ok", [])}
    cg = [f for f in facts if f.kind == "cgpa"]
    if cg and cgpa is not None:
        need = max(f.value for f in cg)
        f = max(cg, key=lambda f: f.value)
        ok = cgpa >= need
        res.append({"label": "CGPA", "status": "ok" if ok else "fail", "detail": f"JD asks {need:g}+ ({f.text!r}); you have {cgpa:g}", "confidence": f.confidence})
    pc = [f for f in facts if f.kind == "percent"]
    if pc and not cg:
        res.append({"label": "Percentage", "status": "unknown", "detail": f"JD mentions {pc[0].value:g}% ({pc[0].text!r}); check your marks", "confidence": pc[0].confidence})
    bt = [f for f in facts if f.kind == "batch"]
    if bt and batch is not None:
        years = sorted({y for f in bt for y in range(f.value[0], f.value[1] + 1)})
        ok = batch in years
        res.append({"label": "Batch", "status": "ok" if ok else "fail",
                    "detail": f"JD targets {', '.join(map(str, years))}; your batch is {batch}", "confidence": max(f.confidence for f in bt)})
    ex = [f for f in facts if f.kind == "experience"]
    if ex:
        lo = min(f.value[0] for f in ex)
        res.append({"label": "Experience", "status": "fail" if lo >= 2 else "unknown",
                    "detail": f"JD mentions {ex[0].text!r}; you are a student/intern-level candidate", "confidence": ex[0].confidence})
    lc = [f.value for f in facts if f.kind == "location"]
    if lc:
        if not locs:
            res.append({"label": "Location", "status": "unknown", "detail": f"JD mentions {', '.join(lc)}", "confidence": 0.7})
        else:
            hit = [c for c in lc if c in locs or c in ("remote", "hybrid", "work from home")]
            res.append({"label": "Location", "status": "ok" if hit else "unknown",
                        "detail": f"JD mentions {', '.join(lc)}; you listed {', '.join(sorted(locs))}", "confidence": 0.7})
    return res


# ---------------- main entry ----------------
def analyze(text: str, tax: Taxonomy, max_chars: int = 400_000) -> JDProfile:
    text = normalize(text)[:max_chars]
    lines = text.split("\n")
    starts, pos = [], 0
    for ln in lines:
        starts.append(pos)
        pos += len(ln) + 1
    sections = _line_sections(lines)
    sec_count: dict[str, int] = {}
    for s in sections:
        sec_count[s] = sec_count.get(s, 0) + 1

    hits = tax.find(text)
    per_skill: dict[str, list[float]] = {}
    evidence: dict[str, list[tuple[str, str, float]]] = {}
    line_w: dict[int, float] = {}          # each line's weight is computed once, not once per hit
    for sid, hs in hits.items():
        for h in hs:
            li = bisect.bisect_right(starts, h.start) - 1
            sec = sections[li]
            if sec == "header":
                sec = "body"
            w = line_w.get(li)
            if w is None:
                w = line_w[li] = _line_weight(lines[li], sec)
            per_skill.setdefault(sid, []).append(w)
            ev = evidence.setdefault(sid, [])
            if len(ev) < 12:                # evidence is for display; bound the work on pathological input
                line = lines[li]
                if len(line) > 160:         # a huge line: show the window around the hit
                    col = h.start - starts[li]
                    line = line[max(0, col - 70):col + 70]
                snippet = _BULLET.sub("", line).strip()
                if all(snippet != e[1] for e in ev):
                    ev.append((sec, snippet[:140], w))
    for ev in evidence.values():
        ev.sort(key=lambda e: -e[2])          # show the strongest mention first, not the first one in the text
        del ev[3:]
    raw = {sid: min(1.5, max(ws) + 0.25 * math.log2(len(ws))) for sid, ws in per_skill.items()}
    top = max(raw.values()) if raw else 0.0
    weights = {sid: round(v / top, 6) for sid, v in raw.items()} if top else {}
    counts = {sid: len(ws) for sid, ws in per_skill.items()}

    arch: dict[str, float] = {}
    for sid, w in weights.items():
        for a, k in tax.skills[sid].arch.items():
            arch[a] = arch.get(a, 0.0) + w * k
    head = " ".join([ln for ln in lines if ln.strip()][:6]).lower()
    for a, pats in tax.roles.items():
        if any(p in head for p in pats):
            arch[a] = arch.get(a, 0.0) + 1.0
    amax = max(arch.values()) if arch else 0.0
    archetypes = {a: round(v / amax, 6) for a, v in sorted(arch.items()) if v > 0} if amax else {}

    title = next((ln.strip() for ln in lines if ln.strip()), "")[:120]
    facts = _facts(lines, tax)

    counts_caps: dict[str, int] = {}
    for m in re.finditer(r"\b[A-Z][A-Za-z0-9]*(?:[+#.][A-Za-z0-9]+)*\b|\b[A-Z]{2,}[0-9]*\b", text):
        tok = m.group(0)
        if tok in _STOP_CAPS or tok.lower() in tax.known_tokens or len(tok) < 3:
            continue
        counts_caps[tok] = counts_caps.get(tok, 0) + 1
    unknown = sorted(((t, c) for t, c in counts_caps.items() if c >= 2), key=lambda kv: (-kv[1], kv[0]))[:12]

    return JDProfile(title=title, skill_weights=weights, skill_counts=counts, evidence=evidence, archetypes=archetypes,
                     facts=facts, unknown_terms=unknown, sections=sec_count, chars=len(text))
