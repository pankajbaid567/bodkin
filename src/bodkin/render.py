"""Renderers: Markdown report, JSON, LaTeX snippet, plain text, batch matrix."""
from __future__ import annotations

import json

from .bank import Bank
from .select import Pick, Selection
from .taxonomy import Taxonomy

_TEX = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
        "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
_UNI = {"–": "--", "—": "---", "“": "``", "”": "''", "’": "'", "‘": "`", "…": r"\ldots{}", "₹": r"Rs.\,"}


def tex_escape(text: str) -> str:
    return "".join(_TEX.get(ch, _UNI.get(ch, ch)) for ch in text)


def tex_bold(text: str) -> str:
    """Escape for LaTeX and turn **x** into \\textbf{x}."""
    parts = text.split("**")
    out = []
    for i, p in enumerate(parts):
        e = tex_escape(p)
        out.append(r"\textbf{" + e + "}" if i % 2 else e)
    return "".join(out)


def _bar(v: float, n: int = 10) -> str:
    k = round(v * n)
    return "█" * k + "░" * (n - k)


def _mark(status: str) -> str:
    return {"proven": "proven", "reported": "reported (re-verify)", "pending": "PENDING"}.get(status, status)


# ---------------- JSON ----------------
def to_dict(sel: Selection, bank: Bank, tax: Taxonomy) -> dict:
    def pick(p: Pick) -> dict:
        it = p.score.item
        return {
            "id": it.id, "name": it.name, "title": it.title, "subtitle": it.subtitle, "date": it.date, "status": it.status,
            "links": it.links, "filler": p.filler, "gain": round(p.score.gain, 4), "share": round(p.score.share, 4), "quality": round(p.score.quality, 4),
            "why": [{"skill": c.label, "value": round(c.value, 4), "jd": c.jd_evidence} for c in p.score.contributions],
            "bullets": [{"claim": b.claim.uid, "text": b.text, "variant": b.variant, "proof": b.claim.proof.status,
                         "relevance": round(b.relevance, 4), "limits": b.claim.proof.limits} for b in p.bullets],
        }
    jd = sel.jd
    return {
        "title": jd.title,
        "archetypes": {k: round(v, 4) for k, v in sorted(jd.archetypes.items(), key=lambda kv: (-kv[1], kv[0]))},
        "skills": [{"id": s, "name": tax.skills[s].name, "weight": round(w, 4), "mentions": jd.skill_counts.get(s, 0),
                    "evidence": [{"section": a, "text": b, "w": c} for a, b, c in jd.evidence.get(s, [])]}
                   for s, w in sorted(jd.skill_weights.items(), key=lambda kv: (-kv[1], kv[0]))],
        "unknown_terms": jd.unknown_terms,
        "eligibility": sel.eligibility,
        "projects": [pick(p) for p in sel.projects],
        "experience": [pick(p) for p in sel.experience],
        "achievements": [pick(p) for p in sel.achievements],
        "ranking": [{"id": s.item.id, "name": s.item.name, "standalone": round(s.standalone, 4), "quality": round(s.quality, 4),
                     "picked": any(p.score.item.id == s.item.id for p in sel.projects), "skipped": s.skipped} for s in sel.ranking],
        "skills_section": {cat: [{"name": l.name, "matched": l.weight > 0, "weight": round(l.weight, 4)} for l in lines]
                           for cat, lines in sel.skills.items()},
        "gaps": {
            "listed": [{"skill": n, "weight": round(w, 4), "evidence": round(e, 2)} for n, w, e in sel.gaps.listed],
            "claimable": [{**g, "weight": round(g["weight"], 4)} for g in sel.gaps.claimable],
            "no_evidence": [{**g, "weight": round(g["weight"], 4)} for g in sel.gaps.no_evidence],
            "listed_unevidenced": [{"skill": n, "weight": round(w, 4)} for n, w in sel.gaps.listed_unevidenced],
        },
        "coverage": round(sel.coverage, 4), "uncovered": sel.uncovered,
        "warnings": sel.warnings, "limits": [{"claim": c, "limit": l} for c, l in sel.limits],
        "stopped_early": sel.stopped_early,
    }


def to_json(sel: Selection, bank: Bank, tax: Taxonomy) -> str:
    return json.dumps(to_dict(sel, bank, tax), indent=2, ensure_ascii=False, sort_keys=False)


# ---------------- Markdown ----------------
def to_markdown(sel: Selection, bank: Bank, tax: Taxonomy) -> str:
    jd, L = sel.jd, []
    L += [f"# Bodkin report: {jd.title or 'job description'}", "",
          "Every bullet below is verbatim text from your bank; Bodkin selected and ordered, it wrote nothing. "
          "`proven` = backed by a proof command and result file; `reported` = from your resume or a README, re-verify.", ""]
    L += ["## 1. What the JD is about", ""]
    for a, v in sorted(jd.archetypes.items(), key=lambda kv: (-kv[1], kv[0]))[:6]:
        L.append(f"- `{a:<11}` {_bar(v)} {v:.2f}")
    L += ["", "Top skills (weight, where it was said):", ""]
    for s, w in jd.top_skills(12):
        ev = jd.evidence.get(s, [("", "", 0)])[0]
        L.append(f"- **{tax.skills[s].name}** {w:.2f} ({jd.skill_counts.get(s, 1)}x, {ev[0]}): {ev[1][:90]}")
    if jd.unknown_terms:
        L += ["", "Terms the taxonomy did not recognise (add to `data/skills.toml` if they matter): " + ", ".join(f"{t} ({c})" for t, c in jd.unknown_terms)]
    if sel.eligibility:
        L += ["", "Eligibility (advice; extracted from free text, check the JD yourself):", ""]
        for e in sel.eligibility:
            icon = {"ok": "OK ", "fail": "NO ", "unknown": "?  "}[e["status"]]
            L.append(f"- {icon} **{e['label']}**: {e['detail']}")
    L += ["", f"## 2. Recommended projects (top {sel.options.top})", ""]
    if not sel.projects:
        L.append("_No project is relevant enough for this JD._")
    for n, p in enumerate(sel.projects, 1):
        it = p.score.item
        link = " · ".join(f"[{k}]({v})" for k, v in it.links.items())
        L += [f"### {n}. {it.title}  ({it.date}) {'**[WIP]**' if it.status == 'wip' else ''}{' _(supporting, not JD-specific)_' if p.filler else ''}", ""]
        if link:
            L += [link, ""]
        if p.filler:
            L.append("Supporting project: not chosen for this JD; included as your strongest proven work.")
        else:
            L.append(f"Covers {p.score.share * 100:.0f}% of this JD's weighted need. Why: " + "; ".join(f"{c.label} ({c.value:.2f})" for c in p.score.contributions[:5]))
        L.append("")
        for b in p.bullets:
            tag = _mark(b.claim.proof.status) + ("" if b.variant == "default" else f", {b.variant} variant")
            L.append(f"- {b.text}  _[{tag}]_")
        L.append("")
    if sel.experience:
        L += ["## 3. Experience (bullets ordered for this JD)", ""]
        for p in sel.experience:
            it = p.score.item
            L += [f"### {it.title}, {it.subtitle}  ({it.date})", ""]
            L += [f"- {b.text}  _[{_mark(b.claim.proof.status)}]_" for b in p.bullets] + [""]
    if sel.achievements:
        L += ["## 4. Achievements", ""]
        L += [f"- {b.text}  _[{_mark(b.claim.proof.status)}]_" for p in sel.achievements for b in p.bullets] + [""]
    L += ["## 5. Skills section (re-ordered; **bold** = the JD mentions it)", ""]
    for cat, lines in sel.skills.items():
        L.append(f"- **{cat}:** " + ", ".join(f"**{l.name}**" if l.weight > 0 else l.name for l in lines))
    g = sel.gaps
    L += ["", "## 6. Gaps and coverage", "", f"JD skill coverage (profile skills + chosen items): **{sel.coverage * 100:.0f}%**"]
    if sel.uncovered:
        L.append("Not covered: " + ", ".join(sel.uncovered[:10]))
    if g.claimable:
        L += ["", "You have used these (the bank shows it) but your skills line does not list them. Add them if true:", ""]
        for c in g.claimable[:10]:
            L.append(f"- **{c['skill']}** (JD weight {c['weight']:.2f}): evidence in {', '.join(c['evidence'])}")
    if g.no_evidence:
        L += ["", "No proven evidence anywhere in the bank:", ""]
        for c in g.no_evidence[:10]:
            fix = ", ".join(f"{r['name'].split(':')[0]}" for r in c["roadmap"]) or "no planned project covers it"
            L.append(f"- **{c['skill']}** (JD weight {c['weight']:.2f}): would be closed by: {fix}")
    if g.listed_unevidenced:
        L += ["", "Listed in your skills but no project demonstrates them: " + ", ".join(n for n, _ in g.listed_unevidenced)]
    L += ["", "## 7. Ranking of all projects (stand-alone relevance)", "", "| project | relevance | quality | used |", "|---|---|---|---|"]
    for s in sel.ranking:
        used = "yes" if any(p.score.item.id == s.item.id for p in sel.projects) else (s.skipped or "")
        L.append(f"| {s.item.name} | {s.standalone:.2f} | {s.quality:.2f} | {used} |")
    if sel.warnings or sel.limits:
        L += ["", "## 8. Read before you use this", ""]
        L += [f"- {w}" for w in sel.warnings]
        L += [f"- limit ({c}): {l}" for c, l in sel.limits]
    return "\n".join(L).rstrip() + "\n"


# ---------------- plain text and LaTeX ----------------
def _sections(sel: Selection):
    return (("PROJECTS", sel.projects), ("EXPERIENCE", sel.experience), ("ACHIEVEMENTS", sel.achievements))


def to_text(sel: Selection) -> str:
    out = []
    for name, picks in (("EXPERIENCE", sel.experience), ("PROJECTS", sel.projects)):
        out += [name, ""]
        for p in picks:
            it = p.score.item
            head = it.title + (f", {it.subtitle}" if it.subtitle else "")
            out.append(f"{head}    {it.date}")
            out += [f"  • {b.text.replace('**', '')}" for b in p.bullets] + [""]
    out += ["ACHIEVEMENTS", ""]
    out += [f"  • {b.text.replace('**', '')}" for p in sel.achievements for b in p.bullets] + [""]
    out += ["SKILLS", ""] + [f"  {cat}: " + ", ".join(l.name for l in lines) for cat, lines in sel.skills.items()]
    return "\n".join(out) + "\n"


def to_tex(sel: Selection) -> str:
    """A generic LaTeX snippet (itemize); adapt the macros to your resume class."""
    L = ["% Generated by Bodkin. Every bullet is verbatim bank text; edit the bank, not this file.",
         "% Requires: \\usepackage{enumitem,hyperref}", ""]

    def block(picks: list[Pick], heading: str):
        L.append(f"\\section*{{{heading}}}")
        for p in picks:
            it = p.score.item
            links = " ".join(f"(\\href{{{v}}}{{{tex_escape(k.capitalize())}}})" for k, v in it.links.items())
            head = tex_bold(it.title) + (f", {tex_escape(it.subtitle)}" if it.subtitle else "")
            L.append(f"\\textbf{{{head}}} {links} \\hfill {tex_escape(it.date)}\\\\")
            L.append("\\begin{itemize}[leftmargin=1.4em,itemsep=1pt,topsep=2pt,parsep=0pt]")
            L.extend(f"  \\item {tex_bold(b.text)}" for b in p.bullets)
            L.extend(["\\end{itemize}", ""])

    block(sel.experience, "EXPERIENCE")
    block(sel.projects, "PROJECTS")
    L.append("\\section*{ACHIEVEMENTS}\n\\begin{itemize}[leftmargin=1.4em,itemsep=1pt,topsep=2pt,parsep=0pt]")
    L += [f"  \\item {tex_bold(b.text)}" for p in sel.achievements for b in p.bullets]
    L += ["\\end{itemize}", "", "\\section*{SKILLS}\n\\begin{itemize}[leftmargin=1.4em,itemsep=1pt,topsep=2pt,parsep=0pt]"]
    L += [f"  \\item \\textbf{{{tex_escape(cat)}:}} " + ", ".join(tex_escape(l.name) for l in lines) for cat, lines in sel.skills.items()]
    L.append("\\end{itemize}")
    return "\n".join(L) + "\n"


# ---------------- batch ----------------
def batch_markdown(results: list[tuple[str, Selection]], bank: Bank, tax: Taxonomy) -> str:
    L = ["# Bodkin batch report", "", f"{len(results)} job descriptions.", "",
         "| JD | top archetypes | project 1 | project 2 | project 3 | coverage | eligibility |", "|---|---|---|---|---|---|---|"]
    for name, sel in results:
        arch = ", ".join(a for a, _ in sorted(sel.jd.archetypes.items(), key=lambda kv: (-kv[1], kv[0]))[:2])
        ps = [p.score.item.name for p in sel.projects] + ["-"] * 3
        bad = [e["label"] for e in sel.eligibility if e["status"] == "fail"]
        L.append(f"| {name} | {arch} | {ps[0]} | {ps[1]} | {ps[2]} | {sel.coverage * 100:.0f}% | {'NO: ' + ', '.join(bad) if bad else 'ok'} |")
    # how often each project is used, and what the gaps say about the roadmap
    use: dict[str, int] = {}
    for _, sel in results:
        for p in sel.projects:
            if not p.filler:
                use[p.score.item.name] = use.get(p.score.item.name, 0) + 1
    L += ["", "## How often each project is chosen", ""]
    L += [f"- {n}: {c} of {len(results)} JDs" for n, c in sorted(use.items(), key=lambda kv: (-kv[1], kv[0]))]
    unused = [i.name for i in bank.items.values() if i.kind == "project" and i.name not in use]
    if unused:
        L.append("- never chosen: " + ", ".join(unused))
    demand: dict[str, float] = {}
    skill_demand: dict[str, float] = {}
    for _, sel in results:
        for g in sel.gaps.no_evidence:
            skill_demand[g["skill"]] = skill_demand.get(g["skill"], 0.0) + g["weight"]
            for r in g["roadmap"]:
                demand[r["name"]] = demand.get(r["name"], 0.0) + g["weight"] * r["strength"]
    L += ["", "## Skills with no proven evidence, by total JD weight", ""]
    L += [f"- {s}: {w:.2f}" for s, w in sorted(skill_demand.items(), key=lambda kv: (-kv[1], kv[0]))[:12]] or ["- none"]
    L += ["", "## Which planned project would close the most gap weight (build next)", ""]
    L += [f"- {n}: {w:.2f}" for n, w in sorted(demand.items(), key=lambda kv: (-kv[1], kv[0]))] or ["- none"]
    claim: dict[str, float] = {}
    for _, sel in results:
        for g in sel.gaps.claimable:
            claim[g["skill"]] = claim.get(g["skill"], 0.0) + g["weight"]
    L += ["", "## Skills you could truthfully add to your resume (used in the bank, not listed), by total JD weight", ""]
    L += [f"- {s}: {w:.2f}" for s, w in sorted(claim.items(), key=lambda kv: (-kv[1], kv[0]))[:12]] or ["- none"]
    return "\n".join(L) + "\n"
