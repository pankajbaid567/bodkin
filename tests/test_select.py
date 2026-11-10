import unittest

from bodkin import jd as jdmod, select as S
from tests.helpers import TODAY, claim, item, real_bank, real_taxonomy, tiny_bank, tiny_taxonomy

JD = "Title\nRequirements\n- alphalang\n- betalang\nPreferred\n- gammalang"   # needs: alpha 1.0, beta 1.0, gamma 0.5 (total 2.5)


def run(items, text=JD, **kw):
    tax = tiny_taxonomy()
    opts = S.Options(today=TODAY, fill=kw.pop("fill", False), **kw)
    return S.select(jdmod.analyze(text, tax), tiny_bank(items), tax, opts)


class GreedyTests(unittest.TestCase):
    def test_hand_computed_order_and_diminishing_returns(self):
        p1 = item("p1", {"alpha": 1.0, "beta": 1.0})
        p2 = item("p2", {"alpha": 1.0})
        p3 = item("p3", {"gamma": 1.0})
        sel = run([p1, p2, p3])
        self.assertEqual([p.score.item.id for p in sel.projects], ["p1", "p3", "p2"])
        gains = {p.score.item.id: p.score.gain for p in sel.projects}
        self.assertAlmostEqual(gains["p1"], 2.0)                    # alpha 1.0 + beta 1.0, quality 1.0
        self.assertAlmostEqual(gains["p3"], 0.5)                    # gamma 0.5
        self.assertAlmostEqual(gains["p2"], 1.0 * (1 - 0.85))       # alpha already 85% used up by p1

    def test_redundant_project_loses_to_complementary_one(self):
        a = item("a", {"alpha": 1.0, "beta": 1.0})
        twin = item("twin", {"alpha": 1.0, "beta": 1.0})
        other = item("other", {"gamma": 1.0})
        sel = run([a, twin, other], top=2)
        self.assertEqual({p.score.item.id for p in sel.projects}, {"a", "other"})

    def test_min_share_stops_padding(self):
        p1 = item("p1", {"alpha": 1.0, "beta": 1.0})
        weak = item("weak", {"alpha": 0.1})                          # after p1 it adds 1*0.1*0.15 = 0.015 < 3% of 2.5
        sel = run([p1, weak])
        self.assertEqual([p.score.item.id for p in sel.projects], ["p1"])
        self.assertTrue(sel.stopped_early)
        self.assertTrue(any("only 1 project" in w for w in sel.warnings))

    def test_fill_adds_marked_supporting_projects(self):
        p1 = item("p1", {"alpha": 1.0, "beta": 1.0})
        other = item("other", {"delta": 1.0})
        sel = run([p1, other], fill=True)
        self.assertEqual([(p.score.item.id, p.filler) for p in sel.projects], [("p1", False), ("other", True)])

    def test_wip_is_penalised_and_flagged_archived_excluded(self):
        good = item("good", {"alpha": 1.0})
        wip = item("wip", {"alpha": 1.0}, status="wip")
        old = item("old", {"alpha": 1.0}, status="archived")
        sel = run([wip, old, good], top=1)
        self.assertEqual(sel.projects[0].score.item.id, "good")
        scores = {s.item.id: s for s in sel.ranking}
        self.assertAlmostEqual(scores["wip"].quality, S.WIP_FACTOR)
        self.assertEqual(scores["old"].skipped, "archived")
        sel2 = run([wip], top=1)
        self.assertTrue(any("WIP" in w for w in sel2.warnings))
        self.assertEqual(run([wip], top=1, include_wip=False).projects, [])

    def test_recency_decay(self):
        fresh, mid, old = (item(i, {"alpha": 1.0}, end=e) for i, e in (("f", "2026-06"), ("m", "2024-11"), ("o", "2020-01")))
        self.assertEqual(S.recency(fresh, TODAY), 1.0)
        self.assertAlmostEqual(S.recency(mid, TODAY), 1.0 - 0.15 * (24 - 12) / 24)
        self.assertEqual(S.recency(old, TODAY), 0.85)

    def test_proof_factor(self):
        proven = item("pv", {"alpha": 1.0}, claims=[claim("pv", "c", "x", status="proven")])
        reported = item("rp", {"alpha": 1.0}, claims=[claim("rp", "c", "x", status="reported")])
        sc = {s.item.id: s.quality for s in run([proven, reported]).ranking}
        self.assertAlmostEqual(sc["pv"], 1.0)
        self.assertAlmostEqual(sc["rp"], 0.7)

    def test_item_with_only_pending_claims_is_unusable(self):
        pend = item("pend", {"alpha": 1.0}, claims=[claim("pend", "c", "SENTINEL", status="pending")])
        sel = run([pend])
        self.assertEqual(sel.projects, [])
        self.assertIn("pending", sel.ranking[0].skipped)
        sel2 = run([pend], include_pending=True)
        self.assertEqual(sel2.projects[0].bullets[0].text, "SENTINEL")

    def test_ties_break_by_id(self):
        a, b = item("aaa", {"alpha": 1.0}), item("bbb", {"alpha": 1.0})
        self.assertEqual(run([b, a], top=1).projects[0].score.item.id, "aaa")


class BulletTests(unittest.TestCase):
    def test_group_diversity_then_fill(self):
        cs = [claim("x", "c1", "one", group="g", skills={"alpha": 1.0}), claim("x", "c2", "two", group="g", skills={"alpha": 0.9}),
              claim("x", "c3", "three", group="h", skills={"alpha": 0.2})]
        sel = run([item("x", {"alpha": 1.0}, claims=cs)], bullets=2)
        self.assertEqual([b.text for b in sel.projects[0].bullets], ["one", "three"])     # c2 shares c1's group, so c3 comes first
        sel3 = run([item("x", {"alpha": 1.0}, claims=cs)], bullets=3)
        self.assertEqual(len(sel3.projects[0].bullets), 3)                                   # groups run out, then fill

    def test_relevance_orders_bullets(self):
        cs = [claim("x", "low", "low", skills={"gamma": 1.0}), claim("x", "high", "high", skills={"alpha": 1.0})]
        sel = run([item("x", {"alpha": 1.0, "gamma": 1.0}, claims=cs)], bullets=2)
        self.assertEqual([b.text for b in sel.projects[0].bullets], ["high", "low"])

    def test_variant_chosen_by_archetype(self):
        from bodkin.jd import JDProfile
        c = claim("x", "c", "default text", variants={"data": "data text", "backend": "backend text"})
        jd = JDProfile("t", {}, {}, {}, {"data": 0.9, "backend": 0.7}, [], [], {})
        self.assertEqual(S.choose_variant(c, jd, S.Options()), ("data", "data text"))
        weak = JDProfile("t", {}, {}, {}, {"data": 0.3}, [], [], {})
        self.assertEqual(S.choose_variant(c, weak, S.Options()), ("default", "default text"))
        self.assertEqual(S.choose_variant(c, jd, S.Options(variant="backend")), ("backend", "backend text"))
        self.assertEqual(S.choose_variant(c, jd, S.Options(variant="nope")), ("default", "default text"))


class SkillsGapTests(unittest.TestCase):
    def test_skills_reordered_not_added(self):
        tax = tiny_taxonomy()
        bank = tiny_bank([item("p", {"alpha": 1.0})], skills_section={"Langs": ["Delta", "Beta", "Alpha"]})
        sel = S.select(jdmod.analyze("T\nRequirements\n- alphalang\nPreferred\n- betalang", tax), bank, tax, S.Options(today=TODAY, fill=False))
        self.assertEqual([l.name for l in sel.skills["Langs"]], ["Alpha", "Beta", "Delta"])
        self.assertEqual(sorted(l.name for l in sel.skills["Langs"]), ["Alpha", "Beta", "Delta"])

    def test_gap_categories(self):
        tax = tiny_taxonomy()
        used = item("p", {"alpha": 1.0, "gamma": 0.8})                      # gamma used but not listed -> claimable
        bank = tiny_bank([used], skills_section={"Langs": ["Alpha", "Beta"]})   # beta listed, no project shows it
        from bodkin.bank import Planned
        bank.roadmap = [Planned("fixer", "Fixer: closes delta", "", {"delta": 1.0}, {})]
        sel = S.select(jdmod.analyze("T\nRequirements\n- alphalang\n- betalang\n- gammalang\n- deltalang", tax), bank, tax, S.Options(today=TODAY, fill=False))
        self.assertEqual([c["id"] for c in sel.gaps.claimable], ["gamma"])
        self.assertEqual([n for n, _ in sel.gaps.listed_unevidenced], ["Beta"])
        self.assertEqual([g["id"] for g in sel.gaps.no_evidence], ["delta"])
        self.assertEqual(sel.gaps.no_evidence[0]["roadmap"][0]["id"], "fixer")
        self.assertLess(sel.coverage, 1.0)
        self.assertIn("Delta", sel.uncovered)


class RealBankTests(unittest.TestCase):
    def test_experience_always_present_and_reordered(self):
        tax, bank = real_taxonomy(), real_bank()
        sel = S.select(jdmod.analyze("T\nRequirements\n- MongoDB, Node.js and REST APIs", tax), bank, tax, S.Options(today=TODAY))
        self.assertEqual([p.score.item.id for p in sel.experience], ["incalculate"])
        self.assertIn("REST", sel.experience[0].bullets[0].text)


if __name__ == "__main__":
    unittest.main()
