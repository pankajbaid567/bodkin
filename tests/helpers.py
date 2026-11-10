"""Shared builders for tests."""
import shutil
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from bodkin.bank import Bank, Claim, Item, Planned, Proof  # noqa: E402
from bodkin.lint import Linter  # noqa: E402
from bodkin.taxonomy import Taxonomy  # noqa: E402

TODAY = date(2026, 11, 10)


def real_taxonomy() -> Taxonomy:
    return Taxonomy.load()


def real_bank() -> Bank:
    return Bank.load(ROOT / "bank")


def tiny_taxonomy() -> Taxonomy:
    return Taxonomy({
        "meta": {"archetypes": ["backend", "data"]},
        "roles": {},
        "cities": {"names": ["bengaluru", "remote"]},
        "skills": {
            "alpha": {"name": "Alpha", "cat": "x", "aliases": ["alphalang"], "arch": {}},
            "beta": {"name": "Beta", "cat": "x", "aliases": ["betalang"], "arch": {}},
            "gamma": {"name": "Gamma", "cat": "x", "aliases": ["gammalang"], "arch": {}},
            "delta": {"name": "Delta", "cat": "x", "aliases": ["deltalang"], "arch": {}},
        },
    })


def claim(item_id, cid, text, status="proven", numbers=(), skills=None, group="", variants=None, limits=""):
    return Claim(id=cid, item_id=item_id, text=text, variants=variants or {}, numbers=tuple(numbers), skills=skills or {},
                 archetypes={}, group=group, proof=Proof(status=status, command="make x", artifact="a", date="2026-11-01", limits=limits))


def item(iid, skills, claims=None, kind="project", status="shipped", end="2026-11", archetypes=None, title=None):
    claims = claims if claims is not None else [claim(iid, "c1", f"Did {iid} thing", skills={k: v for k, v in skills.items()})]
    return Item(id=iid, kind=kind, name=iid, title=title or iid.upper(), subtitle="", status=status, date="Nov 2026", end=end, links={},
                repo="", archetypes=archetypes or {}, skills=skills, tech=(), claims=tuple(claims), note="")


def tiny_bank(items, skills_section=None, roadmap=()):
    return Bank(root=Path("."), person={"name": "T", "batch": 2028, "cgpa": 8.0, "locations_ok": ["bengaluru"]},
                skills=skills_section or {"Langs": ["Alpha"]}, items={i.id: i for i in items}, roadmap=list(roadmap))


def copy_bank(tmp: Path) -> Path:
    dst = tmp / "bank"
    shutil.copytree(ROOT / "bank", dst)
    return dst
