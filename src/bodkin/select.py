"""Selection: which projects, which bullets, which skills order, which gaps.

Pure function of (JD profile, bank, taxonomy, options). Nothing here writes text:
every bullet returned is a verbatim string from the bank (honesty property H1)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from . import jd as jdmod
from .bank import Bank, Claim, Item
from .jd import JDProfile
from .taxonomy import Taxonomy

ARCH_NEED_SCALE = 0.6      # archetype needs count less than named skills
DIMINISH = 0.85            # how much of a covered need a chosen item uses up
WIP_FACTOR = 0.7
ARCHIVED_FACTOR = 0.4
STATUS_FACTOR = {"shipped": 1.0, "wip": WIP_FACTOR, "archived": ARCHIVED_FACTOR}
VARIANT_MIN = 0.5          # a variant is used only if its archetype score reaches this


@dataclass
class Options:
    top: int = 3
    bullets: int = 4
    exp_bullets: int = 4
    achievements: int = 3
    include_pending: bool = False
    include_wip: bool = True
    include_archived: bool = False
    fill: bool = True             # fill unused slots with your strongest proven projects, marked as supporting
    variant: str = "auto"
    min_gain: float = 0.05
    min_share: float = 0.03       # a project must cover at least this share of the JD's total weighted need (ADR-011)
    gap_min_weight: float = 0.3
    today: date | None = None


@dataclass
class Contribution:
    key: str          # "s:go" or "a:systems"
    label: str
    value: float
    jd_evidence: str = ""


@dataclass
class ItemScore:
    item: Item
    quality: float
    standalone: float
    eligible_claims: int
    skipped: str = ""             # reason the item cannot be used, if any
    gain: float = 0.0             # gain at the moment it was picked (0 if not picked)
    share: float = 0.0            # gain as a share of the JD's total weighted need
    contributions: list[Contribution] = field(default_factory=list)


@dataclass
class Bullet:
    claim: Claim
    text: str
    variant: str                  # archetype key of the variant used, or "default"
    relevance: float


@dataclass
class Pick:
    score: ItemScore
    bullets: list[Bullet]
    filler: bool = False          # supporting project, not chosen for relevance to this JD


@dataclass
class SkillLine:
    name: str
    skill_id: str | None
    weight: float                 # JD weight, 0 if not mentioned


@dataclass
class Gaps:
    listed: list[tuple[str, float, float]] = field(default_factory=list)          # (skill name, jd weight, best bank evidence)
    claimable: list[dict] = field(default_factory=list)                            # you used it; profile does not list it
    no_evidence: list[dict] = field(default_factory=list)                          # neither listed nor used
    listed_unevidenced: list[tuple[str, float]] = field(default_factory=list)     # listed but no project shows it


@dataclass
class Selection:
    jd: JDProfile
    options: Options
    eligibility: list[dict]
    projects: list[Pick]
    ranking: list[ItemScore]
    experience: list[Pick]
    achievements: list[Pick]
    skills: dict[str, list[SkillLine]]
    gaps: Gaps
    coverage: float
    covered_by: dict[str, str]
    uncovered: list[str]
    warnings: list[str]
    limits: list[tuple[str, str]]      # (claim uid, limit to remember when this bullet is used)
    stopped_early: bool = False


def _months_between(end: str, today: date) -> int | None:
    try:
        y, m = int(end[:4]), int(end[5:7])
    except (ValueError, IndexError):
        return None
    return (today.year - y) * 12 + (today.month - m)


def recency(item: Item, today: date) -> float:
    m = _months_between(item.end, today) if item.end else None
    if m is None or m <= 12:
        return 1.0
    if m >= 36:
        return 0.85
    return 1.0 - 0.15 * (m - 12) / 24.0


def needs_of(jd: JDProfile) -> dict[str, float]:
    n: dict[str, float] = {f"s:{s}": w for s, w in jd.skill_weights.items()}
    for a, v in jd.archetypes.items():
        n[f"a:{a}"] = ARCH_NEED_SCALE * v
    return n


def _item_cov(item: Item, key: str) -> float:
    kind, name = key.split(":", 1)
    return item.skills.get(name, 0.0) if kind == "s" else item.archetypes.get(name, 0.0)


def _claim_cov(claim: Claim, item: Item, key: str) -> float:
    kind, name = key.split(":", 1)
    own = claim.skills if kind == "s" else claim.archetypes
    if own:
        return own.get(name, 0.0)
    return 0.7 * _item_cov(item, key)


def _label(tax: Taxonomy, key: str) -> str:
    kind, name = key.split(":", 1)
    return tax.skills[name].name if kind == "s" and name in tax.skills else f"{name} (role type)"


def _usable(item: Item, opts: Options) -> str:
    if item.status == "archived" and not opts.include_archived:
        return "archived"
    if item.status == "wip" and not opts.include_wip:
        return "wip (excluded by option)"
    return ""


def score_item(item: Item, bank: Bank, needs: dict[str, float], jd: JDProfile, tax: Taxonomy, opts: Options, today: date) -> ItemScore:
    claims = bank.eligible_claims(item, opts.include_pending)
    why = _usable(item, opts)
    if not claims and not why:
        why = "no usable claims (all pending)"
    proven = sum(1 for c in claims if c.proof.status == "proven")
    pf = 0.7 + 0.3 * (proven / len(claims)) if claims else 0.0
    q = STATUS_FACTOR.get(item.status, 1.0) * pf * recency(item, today)
    contribs = []
    total = 0.0
    for key, need in needs.items():
        cv = _item_cov(item, key)
        if cv > 0:
            v = need * cv * q
            total += v
            ev = ""
            if key.startswith("s:"):
                e = jd.evidence.get(key[2:])
                if e:
                    ev = f"[{e[0][0]}] {e[0][1]}"
            contribs.append(Contribution(key, _label(tax, key), v, ev))
    contribs.sort(key=lambda c: (-c.value, c.key))
    return ItemScore(item=item, quality=q, standalone=total, eligible_claims=len(claims), skipped=why, contributions=contribs[:6])


def choose_variant(claim: Claim, jd: JDProfile, opts: Options) -> tuple[str, str]:
    if opts.variant != "auto":
        return (opts.variant, claim.variants[opts.variant]) if opts.variant in claim.variants else ("default", claim.text)
    best, best_a = "default", 0.0
    for k in sorted(claim.variants):
        a = jd.archetypes.get(k, 0.0)
        if a >= VARIANT_MIN and a > best_a:
            best, best_a = k, a
    return (best, claim.variants[best]) if best != "default" else ("default", claim.text)


def pick_bullets(item: Item, bank: Bank, needs: dict[str, float], jd: JDProfile, opts: Options, limit: int) -> list[Bullet]:
    scored = []
    for idx, c in enumerate(bank.eligible_claims(item, opts.include_pending)):
        rel = sum(need * _claim_cov(c, item, key) for key, need in needs.items())
        rel += 0.15 * (1 if c.numbers else 0) + 0.10 * (1 if c.proof.status == "proven" else 0)
        scored.append((-rel, idx, c))
    scored.sort(key=lambda t: (t[0], t[1]))
    chosen: list[tuple[float, Claim]] = []
    groups: set[str] = set()
    for nrel, _, c in scored:                       # first pass: one bullet per group
        if len(chosen) >= limit:
            break
        if c.group and c.group in groups:
            continue
        chosen.append((-nrel, c))
        if c.group:
            groups.add(c.group)
    if len(chosen) < limit:                         # second pass: fill, ignoring groups
        have = {c.id for _, c in chosen}
        for nrel, _, c in scored:
            if len(chosen) >= limit:
                break
            if c.id not in have:
                chosen.append((-nrel, c))
    chosen.sort(key=lambda t: -t[0])
    out = []
    for rel, c in chosen:
        v, text = choose_variant(c, jd, opts)
        out.append(Bullet(c, text, v, rel))
    return out


def select(jd: JDProfile, bank: Bank, tax: Taxonomy, opts: Options | None = None) -> Selection:
    opts = opts or Options()
    today = opts.today or date.today()
    needs = needs_of(jd)
    projects_all = [i for i in bank.items.values() if i.kind == "project"]
    scores = {i.id: score_item(i, bank, needs, jd, tax, opts, today) for i in projects_all}

    # greedy marginal coverage with diminishing returns (ADR-006)
    rem = dict(needs)
    total_need = sum(needs.values()) or 1.0
    picked: list[Pick] = []
    stopped = False
    pool = [s for s in scores.values() if not s.skipped]
    while len(picked) < opts.top and pool:
        best, best_gain = None, -1.0
        for s in sorted(pool, key=lambda s: s.item.id):
            g = s.quality * sum(rem[k] * _item_cov(s.item, k) for k in rem)
            if g > best_gain + 1e-12:
                best, best_gain = s, g
        if best is None or best_gain < max(opts.min_gain, opts.min_share * total_need):
            stopped = best is not None or not picked
            break
        contribs = []
        for key in rem:
            cv = _item_cov(best.item, key)
            if cv > 0:
                v = rem[key] * cv * best.quality
                ev = ""
                if key.startswith("s:"):
                    e = jd.evidence.get(key[2:])
                    if e:
                        ev = f"[{e[0][0]}] {e[0][1]}"
                contribs.append(Contribution(key, _label(tax, key), v, ev))
        contribs.sort(key=lambda c: (-c.value, c.key))
        best.gain = best_gain
        best.share = best_gain / total_need
        best.contributions = contribs[:6]
        picked.append(Pick(best, pick_bullets(best.item, bank, needs, jd, opts, opts.bullets)))
        for key in rem:
            rem[key] *= 1.0 - DIMINISH * _item_cov(best.item, key)
        pool.remove(best)

    if opts.fill and len(picked) < opts.top:
        chosen = {p.score.item.id for p in picked}
        extra = [s for s in scores.values() if not s.skipped and s.item.id not in chosen]
        extra.sort(key=lambda s: (-s.quality, -sum(1 for c in s.item.claims if c.proof.status == "proven"), s.item.id))
        for s in extra[: opts.top - len(picked)]:
            picked.append(Pick(s, pick_bullets(s.item, bank, needs, jd, opts, opts.bullets), filler=True))

    ranking = sorted(scores.values(), key=lambda s: (bool(s.skipped), -s.standalone, s.item.id))

    # experience: always shown, bullets re-ordered
    experience = []
    for it in sorted((i for i in bank.items.values() if i.kind == "experience" and i.status != "archived"), key=lambda i: i.id):
        sc = score_item(it, bank, needs, jd, tax, opts, today)
        if not sc.skipped:
            experience.append(Pick(sc, pick_bullets(it, bank, needs, jd, opts, opts.exp_bullets)))

    # achievements: ranked by relevance, with a small floor so generic strong lines still appear
    ach_scores = []
    for it in bank.items.values():
        if it.kind != "achievement" or it.status == "archived":
            continue
        sc = score_item(it, bank, needs, jd, tax, opts, today)
        if not sc.skipped:
            ach_scores.append((-(sc.standalone + 0.05 * sc.quality), it.id, sc))
    ach_scores.sort(key=lambda t: (t[0], t[1]))
    achievements = [Pick(sc, pick_bullets(sc.item, bank, needs, jd, opts, 1)) for _, _, sc in ach_scores[: opts.achievements]]

    # skills section: JD-mentioned skills first inside each category; nothing is added
    skills_section: dict[str, list[SkillLine]] = {}
    profile_ids: dict[str, str] = {}
    for cat, names in bank.skills.items():
        lines = []
        for n in names:
            hit = tax.find(n)
            sid = next(iter(hit)) if hit else None
            lines.append(SkillLine(n, sid, jd.skill_weights.get(sid, 0.0) if sid else 0.0))
            if sid:
                profile_ids[sid] = n
        order = {id(l): i for i, l in enumerate(lines)}
        lines.sort(key=lambda l: (-l.weight, order[id(l)]))
        skills_section[cat] = lines

    # evidence in the bank for each skill (any non-archived item, eligible claims only)
    evidence: dict[str, tuple[float, list[str]]] = {}
    for it in bank.items.values():
        if it.status == "archived" or not bank.eligible_claims(it, opts.include_pending):
            continue
        for s, v in it.skills.items():
            cur = evidence.get(s, (0.0, []))
            if v > cur[0]:
                evidence[s] = (v, [it.id])
            elif v == cur[0] and v > 0:
                evidence[s] = (v, sorted(cur[1] + [it.id]))
    gaps = Gaps()
    for sid, w in sorted(jd.skill_weights.items(), key=lambda kv: (-kv[1], kv[0])):
        if w < opts.gap_min_weight:
            continue
        name = tax.skills[sid].name
        ev, who = evidence.get(sid, (0.0, []))
        if sid in profile_ids:
            if ev >= 0.3:
                gaps.listed.append((name, w, ev))
            else:
                gaps.listed_unevidenced.append((name, w))
        elif ev >= 0.5:
            gaps.claimable.append({"skill": name, "id": sid, "weight": w, "evidence": who, "strength": ev})
        else:
            fixes = sorted(((p.skills[sid], p.id, p.name) for p in bank.roadmap if p.skills.get(sid, 0) >= 0.5), reverse=True)
            gaps.no_evidence.append({"skill": name, "id": sid, "weight": w, "weak_evidence": who if ev > 0 else [],
                                     "roadmap": [{"id": i, "name": n, "strength": s} for s, i, n in fixes[:3]]})

    # coverage of the JD's weighted skills
    sel_ids = {p.score.item.id for p in picked if not p.filler} | {p.score.item.id for p in experience}
    total = sum(jd.skill_weights.values())
    covered_by: dict[str, str] = {}
    for sid in jd.skill_weights:
        if sid in profile_ids:
            covered_by[sid] = "profile"
        else:
            for iid in sorted(sel_ids):
                if bank.items[iid].skills.get(sid, 0) >= 0.5:
                    covered_by[sid] = iid
                    break
    cov = sum(jd.skill_weights[s] for s in covered_by) / total if total else 0.0
    uncovered = [tax.skills[s].name for s, _ in sorted(jd.skill_weights.items(), key=lambda kv: (-kv[1], kv[0])) if s not in covered_by]

    # warnings: things you should know before using the output
    warns: list[str] = []
    limits: list[tuple[str, str]] = []
    for p in picked:
        it = p.score.item
        if it.status == "wip":
            warns.append(f"{it.name} is WIP: {it.note or 'not public yet'}")
        rep = [b for b in p.bullets if b.claim.proof.status == "reported"]
        if rep:
            warns.append(f"{it.name}: {len(rep)} of {len(p.bullets)} bullets are 'reported' (from your resume or a README, not re-run by the bank's author); re-verify before an interview")
        for b in p.bullets:
            if b.claim.proof.limits:
                limits.append((b.claim.uid, b.claim.proof.limits))
    elig = jdmod.check_eligibility(jd.facts, bank.person) if jd.facts else []
    for e in elig:
        if e["status"] == "fail":
            warns.append(f"eligibility: {e['label']}: {e['detail']}")
    if len(jd.skill_weights) < 4:
        warns.append("fewer than 4 skills were recognised in this JD: paste the full text, or extend data/skills.toml")
    if not picked:
        warns.append("no project is relevant enough (all gains below the minimum); the JD may be outside the taxonomy")
    relevant = [p for p in picked if not p.filler]
    if stopped and len(relevant) < opts.top and relevant:
        warns.append(f"only {len(relevant)} project(s) are relevant: the next one would cover under {opts.min_share * 100:.0f}% of this JD's weighted need"
                     + ("; the rest are supporting projects (your strongest proven work, not JD-specific)" if len(picked) > len(relevant) else ""))

    return Selection(jd=jd, options=opts, eligibility=elig, projects=picked, ranking=ranking, experience=experience,
                     achievements=achievements, skills=skills_section, gaps=gaps, coverage=cov, covered_by=covered_by,
                     uncovered=uncovered, warnings=warns, limits=limits, stopped_early=stopped)
