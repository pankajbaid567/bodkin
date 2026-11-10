"""Honesty properties H1-H5 (docs/architecture.md): Bodkin never writes, never uses pending claims,
never emits banned wording or undeclared numbers, and is deterministic."""
import json
import os
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from bodkin import jd as jdmod, select as S
from bodkin.bank import Bank
from bodkin.lint import Linter, numbers_in, strip_markup
from tests.helpers import ROOT, TODAY, copy_bank, real_taxonomy

SENTINEL = "PENDING-SENTINEL-SHOULD-NEVER-APPEAR"


def fixture_sentences() -> list[str]:
    out = []
    for p in sorted((ROOT / "jds" / "fixtures").glob("*.txt")):
        out += [ln.strip("-* ").strip() for ln in p.read_text().splitlines() if len(ln.strip()) > 8]
    return out


def random_jd(rng: random.Random, tax, sentences: list[str]) -> str:
    words = [a for s in tax.skills.values() for a in s.aliases]
    parts = []
    for _ in range(rng.randint(1, 25)):
        r = rng.random()
        if r < 0.5:
            parts.append(rng.choice(sentences))
        elif r < 0.8:
            parts.append(" ".join(rng.choice(words) for _ in range(rng.randint(1, 6))))
        elif r < 0.9:
            parts.append(rng.choice(["Requirements", "Preferred qualifications", "About us", "Responsibilities", "Nice to have:"]))
        else:
            parts.append("".join(chr(rng.randint(32, 0x2fff)) for _ in range(rng.randint(1, 40))))
    return "\n".join(parts)


class HonestyProperties(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tax = real_taxonomy()
        cls.tmp = tempfile.TemporaryDirectory()
        root = copy_bank(Path(cls.tmp.name))
        # add a project whose only claims are pending, with a sentinel text
        (root / "items" / "ghost.toml").write_text(f'''
id = "ghost"
kind = "project"
name = "Ghost"
title = "Ghost project"
status = "shipped"
date = "November 2026"
end = "2026-11"
archetypes = {{ backend = 1.0, systems = 1.0, genai = 1.0, fintech = 1.0 }}
skills = {{ python = 1.0, go = 1.0, rest = 1.0, concurrency = 1.0, llm = 1.0, payments = 1.0, docker = 1.0, postgres = 1.0 }}
[[claims]]
id = "p"
text = "{SENTINEL}"
numbers = []
[claims.proof]
status = "pending"
''')
        cls.bank = Bank.load(root)
        cls.all_texts = {t for it in cls.bank.items.values() for c in it.claims for t in c.all_texts()}
        cls.declared = {c.uid: set(c.numbers) for it in cls.bank.items.values() for c in it.claims}
        cls.lint = Linter.load()
        cls.sentences = fixture_sentences()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_h1_h2_h3_h4_over_1000_random_jds(self):
        rng = random.Random(20261110)
        chosen_ghost_with_flag = 0
        for n in range(1000):
            text = random_jd(rng, self.tax, self.sentences)
            opts = S.Options(top=rng.randint(1, 5), bullets=rng.randint(1, 6), include_pending=False, include_wip=rng.random() < 0.8,
                             fill=rng.random() < 0.7, variant=rng.choice(["auto", "auto", "backend", "genai", "nonsense"]), today=TODAY)
            sel = S.select(jdmod.analyze(text, self.tax), self.bank, self.tax, opts)
            picks = sel.projects + sel.experience + sel.achievements
            self.assertLessEqual(len(sel.projects), opts.top)
            self.assertEqual(len({p.score.item.id for p in sel.projects}), len(sel.projects), "duplicate project")
            for p in picks:
                for b in p.bullets:
                    self.assertIn(b.text, self.all_texts, f"#{n}: emitted text is not verbatim bank text")                       # H1
                    self.assertNotEqual(b.claim.proof.status, "pending")                                                          # H2
                    self.assertNotIn(SENTINEL, b.text)                                                                            # H2
                    for tok in numbers_in(b.text):
                        self.assertIn(tok, self.declared[b.claim.uid], f"{b.claim.uid}: number {tok}")                            # H3
                    banned = [x for x in self.lint.check(b.text, b.claim.allow) if x.code == "BANNED"]
                    self.assertEqual(banned, [], b.text)                                                                          # H4
            self.assertNotIn("ghost", [p.score.item.id for p in sel.projects])

    def test_pending_only_used_with_explicit_flag(self):
        text = "T\nRequirements\n- Python, Go, REST APIs, concurrency, LLM, payments, Docker, PostgreSQL"
        sel = S.select(jdmod.analyze(text, self.tax), self.bank, self.tax, S.Options(today=TODAY, include_pending=True))
        self.assertTrue(any(b.text == SENTINEL for p in sel.projects for b in p.bullets), "the flag must make pending claims usable")
        sel0 = S.select(jdmod.analyze(text, self.tax), self.bank, self.tax, S.Options(today=TODAY))
        self.assertFalse(any(b.text == SENTINEL for p in sel0.projects for b in p.bullets))

    def test_h5_deterministic_in_process(self):
        rng = random.Random(5)
        for _ in range(40):
            text = random_jd(rng, self.tax, self.sentences)
            a = S.select(jdmod.analyze(text, self.tax), self.bank, self.tax, S.Options(today=TODAY))
            b = S.select(jdmod.analyze(text, self.tax), self.bank, self.tax, S.Options(today=TODAY))
            self.assertEqual([(p.score.item.id, [x.text for x in p.bullets]) for p in a.projects],
                             [(p.score.item.id, [x.text for x in p.bullets]) for p in b.projects])

    def test_h5_deterministic_across_hash_seeds(self):
        fx = str(ROOT / "jds" / "fixtures" / "01-atlassian-swe-intern.txt")
        outs = []
        for seed in ("0", "1", "12345"):
            env = {**os.environ, "PYTHONHASHSEED": seed, "PYTHONPATH": str(ROOT / "src")}
            r = subprocess.run([sys.executable, "-m", "bodkin", "analyze", fx, "--format", "json", "--today", "2026-11-10"],
                               capture_output=True, text=True, env=env, cwd=ROOT)
            self.assertEqual(r.returncode, 0, r.stderr)
            outs.append(r.stdout)
        self.assertEqual(outs[0], outs[1])
        self.assertEqual(outs[0], outs[2])


class WordingFixtures(unittest.TestCase):
    def test_shipped_bank_never_contains_banned_wording(self):
        lint = Linter.load()
        bank = Bank.load(ROOT / "bank")
        for it in bank.items.values():
            for c in it.claims:
                for t in c.all_texts():
                    self.assertEqual([x for x in lint.check(t, c.allow) if x.code == "BANNED"], [], c.uid)


if __name__ == "__main__":
    unittest.main()
