"""Command line interface."""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path

from . import __version__, evalset, jd as jdmod, render, select as sel_mod
from .bank import Bank, BankError
from .lint import Linter
from .taxonomy import Taxonomy

ROOT = Path(__file__).resolve().parent.parent.parent


def _load(args) -> tuple[Bank, Taxonomy, Linter]:
    tax = Taxonomy.load(args.taxonomy)
    errs = tax.validate()
    if errs:
        raise SystemExit("taxonomy errors:\n  " + "\n  ".join(errs))
    try:
        bank = Bank.load(args.bank)
    except BankError as e:
        raise SystemExit("bank could not be loaded:\n  " + "\n  ".join(f"{i.where}: {i.message}" for i in e.issues))
    return bank, tax, Linter.load(args.lint)


def _today(args) -> date:
    return date.fromisoformat(args.today) if args.today else date.today()


def _read_jd(path: str) -> str:
    raw = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8", errors="replace")
    return evalset.split_front_matter(raw)[1]


def _options(args) -> sel_mod.Options:
    return sel_mod.Options(top=args.top, bullets=args.bullets, include_pending=args.include_pending, include_wip=not args.no_wip,
                           include_archived=args.include_archived, fill=not args.no_fill, variant=args.variant, today=_today(args))


def _select(args, bank, tax, text: str) -> sel_mod.Selection:
    return sel_mod.select(jdmod.analyze(text, tax), bank, tax, _options(args))


def _emit(text: str, out: str | None) -> None:
    if out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(text, encoding="utf-8")
        print(f"wrote {out}", file=sys.stderr)
    else:
        sys.stdout.write(text)


# ---------------- commands ----------------
def cmd_validate(args) -> int:
    bank, tax, lint = _load(args)
    issues = bank.validate(tax, lint, strict=args.strict, today=_today(args))
    for i in issues:
        print(f"{i.level.upper():5} {i.where}: {i.message}")
    errors = [i for i in issues if i.level == "error"]
    n_claims = sum(len(i.claims) for i in bank.items.values())
    print(f"{len(bank.items)} items, {n_claims} claims: {len(errors)} errors, {len(issues) - len(errors)} warnings")
    return 1 if errors else 0


def cmd_taxonomy(args) -> int:
    tax = Taxonomy.load(args.taxonomy)
    errs = tax.validate()
    for e in errs:
        print("ERROR", e)
    print(f"{len(tax.skills)} skills, {len(tax.archetypes)} archetypes, {sum(len(s.aliases) + len(s.cs) for s in tax.skills.values())} aliases: {len(errs)} errors")
    return 1 if errs else 0


def cmd_list(args) -> int:
    bank, _, _ = _load(args)
    print(f"{'id':<16}{'kind':<12}{'status':<10}{'claims':>7}{'proven':>8}{'reported':>9}  title")
    for it in sorted(bank.items.values(), key=lambda i: (i.kind, i.id)):
        pr = sum(1 for c in it.claims if c.proof.status == "proven")
        rp = sum(1 for c in it.claims if c.proof.status == "reported")
        print(f"{it.id:<16}{it.kind:<12}{it.status:<10}{len(it.claims):>7}{pr:>8}{rp:>9}  {it.title}")
    if bank.roadmap:
        print("\nplanned: " + ", ".join(p.id for p in bank.roadmap))
    return 0


def cmd_claims(args) -> int:
    bank, _, _ = _load(args)
    for it in sorted(bank.items.values(), key=lambda i: i.id):
        for c in it.claims:
            print(f"{c.uid:<34}{c.proof.status:<9}{c.proof.date or '-':<12}{c.proof.command or '-'}")
    if args.check:
        issues = bank.check_proofs()
        for i in issues:
            print(f"{i.level.upper():5} {i.where}: {i.message}")
        bad = [i for i in issues if i.level == "error"]
        print(f"proof check: {len(issues)} issues ({len(bad)} errors)")
        return 1 if bad else 0
    return 0


def cmd_analyze(args) -> int:
    bank, tax, _ = _load(args)
    sel = _select(args, bank, tax, _read_jd(args.jd))
    fmt = args.format
    text = {"md": lambda: render.to_markdown(sel, bank, tax), "json": lambda: render.to_json(sel, bank, tax),
            "tex": lambda: render.to_tex(sel), "txt": lambda: render.to_text(sel)}[fmt]()
    _emit(text, args.out)
    return 0


def cmd_batch(args) -> int:
    bank, tax, _ = _load(args)
    files: list[Path] = []
    for p in args.paths:
        pp = Path(p)
        files += sorted(pp.glob("*.txt")) if pp.is_dir() else [pp]
    results = []
    for f in files:
        meta, text = evalset.split_front_matter(f.read_text(encoding="utf-8", errors="replace"))
        results.append((meta.get("name", f.stem), _select(args, bank, tax, text)))
    _emit(render.batch_markdown(results, bank, tax), args.out)
    return 0


def cmd_explain(args) -> int:
    bank, tax, _ = _load(args)
    if args.item not in bank.items:
        raise SystemExit(f"unknown item {args.item!r}; try `bodkin list`")
    jd = jdmod.analyze(_read_jd(args.jd), tax)
    opts = _options(args)
    needs = sel_mod.needs_of(jd)
    sc = sel_mod.score_item(bank.items[args.item], bank, needs, jd, tax, opts, _today(args))
    it = sc.item
    print(f"{it.title}\n  status={it.status} quality={sc.quality:.3f} usable_claims={sc.eligible_claims} stand-alone relevance={sc.standalone:.3f}"
          + (f"  SKIPPED: {sc.skipped}" if sc.skipped else ""))
    print(f"\n  {'need':<26}{'jd need':>8}{'item cov':>9}{'contrib':>9}")
    rows = []
    for key, need in needs.items():
        cv = sel_mod._item_cov(it, key)
        if cv > 0:
            rows.append((need * cv * sc.quality, key, need, cv))
    for v, key, need, cv in sorted(rows, reverse=True):
        print(f"  {sel_mod._label(tax, key):<26}{need:>8.2f}{cv:>9.2f}{v:>9.3f}")
    print("\n  bullets it would use:")
    for b in sel_mod.pick_bullets(it, bank, needs, jd, opts, opts.bullets):
        print(f"   - ({b.relevance:.2f}, {b.claim.proof.status}) {b.text}")
    return 0


def cmd_eval(args) -> int:
    bank, tax, _ = _load(args)
    cases = evalset.load_dir(Path(args.dir))
    if not cases:
        raise SystemExit(f"no *.txt cases in {args.dir}")
    passed = 0
    for c in cases:
        sel = _select(args, bank, tax, c.text)
        chosen = [p.score.item.id for p in sel.projects if not p.filler]   # fillers are not judged
        gap_ids = {g["id"] for g in sel.gaps.no_evidence} | {g["id"] for g in sel.gaps.claimable} | {sid for sid in sel.jd.skill_weights if sid not in sel.covered_by}
        bad = evalset.judge(c, chosen, gap_ids)
        passed += not bad
        print(f"{'PASS' if not bad else 'FAIL'}  {c.name:<46} -> {', '.join(chosen) or '(none relevant)'}" + ("" if not bad else "\n        " + "; ".join(bad)))
    rate = passed / len(cases)
    print(f"\n{passed}/{len(cases)} cases satisfied ({rate * 100:.0f}%); labels are author-written (see docs/testing.md)")
    return 0 if rate >= args.min_pass else 1


def cmd_serve(args) -> int:
    from .server import serve
    serve(args.bank, args.taxonomy, args.lint, args.port, public=args.public)
    return 0


# ---------------- parser ----------------
def build_parser() -> argparse.ArgumentParser:
    def common_args(p, suppress: bool):
        d = argparse.SUPPRESS if suppress else None
        p.add_argument("--bank", default=d if suppress else os.environ.get("BODKIN_BANK", str(ROOT / "bank")), help="bank directory")
        p.add_argument("--taxonomy", default=d, help="skills.toml path")
        p.add_argument("--lint", default=d, help="lint.toml path")
        p.add_argument("--today", default=d, help="fix the date (YYYY-MM-DD) for reproducible output")

    ap = argparse.ArgumentParser(prog="bodkin", description="Thread your proven claims to each job description. Select and re-order, never write.")
    ap.add_argument("--version", action="version", version=f"bodkin {__version__}")
    common_args(ap, suppress=False)
    shared = argparse.ArgumentParser(add_help=False)   # the same flags are accepted after the subcommand
    common_args(shared, suppress=True)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def sel_opts(p):
        p.add_argument("--top", type=int, default=3)
        p.add_argument("--bullets", type=int, default=4)
        p.add_argument("--include-pending", action="store_true", help="also use claims whose proof is pending (never use in a real resume)")
        p.add_argument("--no-wip", action="store_true", help="exclude work-in-progress items")
        p.add_argument("--include-archived", action="store_true")
        p.add_argument("--no-fill", action="store_true", help="show only projects that are relevant to the JD")
        p.add_argument("--variant", default="auto", help="force a bullet variant (archetype id) when a claim has one")

    p = sub.add_parser("validate", help="check the bank (numbers, wording, ids, proof fields)", parents=[shared])
    p.add_argument("--strict", action="store_true", help="treat warnings as errors")
    p.set_defaults(fn=cmd_validate)
    sub.add_parser("taxonomy", help="validate the skill taxonomy", parents=[shared]).set_defaults(fn=cmd_taxonomy)
    sub.add_parser("list", help="list items", parents=[shared]).set_defaults(fn=cmd_list)
    p = sub.add_parser("claims", help="list claims and their proof status", parents=[shared])
    p.add_argument("--check", action="store_true", help="verify proof artifacts exist in each project's repo")
    p.set_defaults(fn=cmd_claims)
    p = sub.add_parser("analyze", help="analyse one JD (file or - for stdin)", parents=[shared])
    p.add_argument("jd")
    p.add_argument("--format", choices=["md", "json", "tex", "txt"], default="md")
    p.add_argument("--out")
    sel_opts(p)
    p.set_defaults(fn=cmd_analyze)
    p = sub.add_parser("batch", help="analyse many JDs and summarise the portfolio gaps", parents=[shared])
    p.add_argument("paths", nargs="+")
    p.add_argument("--out")
    sel_opts(p)
    p.set_defaults(fn=cmd_batch)
    p = sub.add_parser("explain", help="why does an item score what it does for a JD", parents=[shared])
    p.add_argument("item")
    p.add_argument("jd")
    sel_opts(p)
    p.set_defaults(fn=cmd_explain)
    p = sub.add_parser("eval", help="run the labelled JD set", parents=[shared])
    p.add_argument("dir", nargs="?", default=str(ROOT / "jds" / "fixtures"))
    p.add_argument("--min-pass", type=float, default=0.8)
    sel_opts(p)
    p.set_defaults(fn=cmd_eval)
    p = sub.add_parser("serve", help="local web UI on 127.0.0.1 (or --public for hosting)", parents=[shared])
    p.add_argument("--port", type=int, default=8787)
    p.add_argument("--public", action="store_true", help="bind 0.0.0.0, read PORT, allow only BODKIN_ALLOWED_HOSTS / RENDER_EXTERNAL_HOSTNAME, cap body size and concurrency")
    p.set_defaults(fn=cmd_serve)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.fn(args)
    except BrokenPipeError:
        return 0
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
