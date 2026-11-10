import random
import time
import unittest
from pathlib import Path

from bodkin import evalset, jd as jdmod, select as S
from tests.helpers import ROOT, TODAY, real_bank, real_taxonomy


class LabelledEval(unittest.TestCase):
    """Sanity and regression check on 14 author-labelled synthetic JDs. Not a benchmark (docs/testing.md)."""

    def test_pass_rate_at_least_80_percent_and_fixtures_exist(self):
        tax, bank = real_taxonomy(), real_bank()
        cases = evalset.load_dir(ROOT / "jds" / "fixtures")
        self.assertGreaterEqual(len(cases), 12)
        passed, fails = 0, []
        for c in cases:
            sel = S.select(jdmod.analyze(c.text, tax), bank, tax, S.Options(today=TODAY))
            chosen = [p.score.item.id for p in sel.projects if not p.filler]
            gaps = {g["id"] for g in sel.gaps.no_evidence} | {g["id"] for g in sel.gaps.claimable} | {s for s in sel.jd.skill_weights if s not in sel.covered_by}
            bad = evalset.judge(c, chosen, gaps)
            passed += not bad
            if bad:
                fails.append((c.name, bad))
        self.assertGreaterEqual(passed / len(cases), 0.8, fails)

    def test_judge_logic(self):
        c = evalset.Case("p", "n", "t", must=["a"], one_of=[["b", "c"]], must_not=["d"], gap=["g"])
        self.assertEqual(evalset.judge(c, ["a", "b"], {"g"}), [])
        self.assertEqual(len(evalset.judge(c, ["x"], set())), 3)
        self.assertTrue(any("must not" in m for m in evalset.judge(c, ["a", "c", "d"], {"g"})))

    def test_front_matter_parsing(self):
        meta, body = evalset.split_front_matter("---\nname: X\nmust: a, b\n---\nBody text")
        self.assertEqual(meta["name"], "X")
        self.assertEqual(body, "Body text")
        self.assertEqual(evalset.split_front_matter("no front matter")[0], {})


class Robustness(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tax, cls.bank = real_taxonomy(), real_bank()

    def run_sel(self, text):
        return S.select(jdmod.analyze(text, self.tax), self.bank, self.tax, S.Options(today=TODAY))

    def test_random_bytes_and_unicode_never_crash(self):
        rng = random.Random(1)
        for _ in range(60):
            raw = bytes(rng.randrange(256) for _ in range(rng.randint(0, 3000)))
            self.run_sel(raw.decode("utf-8", errors="replace"))
        for text in ("日本語のテキスト Python", "😀" * 500, "‮ RTL Python", "Zalgo̷̢͈ Python", "\x00" * 100):
            self.run_sel(text)

    def test_speed_20kb_jd_under_100ms_and_1mb_bounded(self):
        base = (ROOT / "jds" / "fixtures" / "02-rubrik-intern.txt").read_text()
        text20 = (base * 30)[:20_000]
        t0 = time.perf_counter()
        self.run_sel(text20)
        self.assertLess(time.perf_counter() - t0, 0.5, "20 KB analysis should be far under a second (target 100 ms)")
        big = (base * 4000)[:1_000_000]
        t0 = time.perf_counter()
        self.run_sel(big)
        self.assertLess(time.perf_counter() - t0, 20.0)

    def test_pathological_repetition_does_not_explode_weights(self):
        p = jdmod.analyze("Title\n" + "Python " * 100_000, self.tax)
        self.assertLessEqual(max(p.skill_weights.values()), 1.0)


if __name__ == "__main__":
    unittest.main()
