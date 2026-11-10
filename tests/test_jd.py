import unittest

from bodkin import jd
from tests.helpers import real_taxonomy, tiny_taxonomy


class JDTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t = real_taxonomy()

    def test_required_beats_preferred_beats_about(self):
        text = """Role
About us
We love Kafka.

Requirements
- Python and Docker.

Preferred qualifications
- Kubernetes.
"""
        p = jd.analyze(text, self.t)
        w = p.skill_weights
        self.assertGreater(w["python"], w["kubernetes"])
        self.assertGreater(w["kubernetes"], w["kafka"])

    def test_hand_computed_weights_on_tiny_taxonomy(self):
        t = tiny_taxonomy()
        text = "Title\nRequirements\n- alphalang is needed\n- betalang is needed\nPreferred\n- gammalang"
        p = jd.analyze(text, t)
        self.assertAlmostEqual(p.skill_weights["alpha"], 1.0)
        self.assertAlmostEqual(p.skill_weights["beta"], 1.0)
        self.assertAlmostEqual(p.skill_weights["gamma"], 0.5)

    def test_repetition_raises_weight_but_is_capped(self):
        t = tiny_taxonomy()
        once = jd.analyze("Title\nBody line alphalang\nBody betalang", t).skill_weights
        many = jd.analyze("Title\n" + "\n".join(["body alphalang"] * 50) + "\nbody betalang", t).skill_weights
        self.assertEqual(once["alpha"], once["beta"])
        self.assertGreater(many["alpha"], many["beta"])
        self.assertLessEqual(many["alpha"], 1.0)

    def test_inline_weak_and_strong_markers(self):
        t = tiny_taxonomy()
        p = jd.analyze("Title\nRequirements\n- alphalang is a plus\n- betalang is required", t)
        self.assertLess(p.skill_weights["alpha"], p.skill_weights["beta"])

    def test_archetype_from_skills_and_title(self):
        p = jd.analyze("Site Reliability Engineer Intern\nRequirements\n- Kubernetes, Terraform and Prometheus", self.t)
        self.assertEqual(max(p.archetypes, key=p.archetypes.get), "infra")
        self.assertAlmostEqual(max(p.archetypes.values()), 1.0)

    def test_eligibility_phrasings(self):
        cases = {
            "CGPA 8+": 8.0, "minimum CGPA of 7.5": 7.5, "GPA: 7": 7.0, "at least 6.5 CGPA": 6.5, "8.0 CGPA and above": 8.0,
            "CGPA >= 7": 7.0, "a CPI of 7.2 or higher": 7.2,
        }
        for phrase, want in cases.items():
            facts = [f for f in jd.analyze("T\n" + phrase, self.t).facts if f.kind == "cgpa"]
            self.assertTrue(facts, phrase)
            self.assertAlmostEqual(facts[0].value, want, msg=phrase)

    def test_batch_phrasings(self):
        cases = {"graduating in 2028": (2028, 2028), "batch of 2027": (2027, 2027), "2027 graduates": (2027, 2027),
                 "class of 2026-2027": (2026, 2027), "passing out in 2028": (2028, 2028), "2028 batch": (2028, 2028)}
        for phrase, want in cases.items():
            facts = [f for f in jd.analyze("T\n" + phrase, self.t).facts if f.kind == "batch"]
            self.assertTrue(facts, phrase)
            self.assertEqual(facts[0].value, want, phrase)

    def test_role_location_and_noise(self):
        p = jd.analyze("Intern - Hyderabad (hybrid)\nstipend Rs. 50,000 per month for 6 months\n3-5 years experience", self.t)
        kinds = {f.kind for f in p.facts}
        self.assertTrue({"role", "location", "experience", "stipend"} <= kinds)
        self.assertEqual({f.value for f in p.facts if f.kind == "location"}, {"hyderabad", "hybrid"})

    def test_eligibility_check_against_profile(self):
        facts = jd.analyze("T\nCGPA 8+\nGraduating in 2027\nBengaluru", self.t).facts
        res = {e["label"]: e["status"] for e in jd.check_eligibility(facts, {"cgpa": 7.0, "batch": 2028, "locations_ok": ["pune"]})}
        self.assertEqual(res["CGPA"], "fail")
        self.assertEqual(res["Batch"], "fail")
        self.assertEqual(res["Location"], "unknown")
        ok = {e["label"]: e["status"] for e in jd.check_eligibility(facts, {"cgpa": 8.6, "batch": 2027, "locations_ok": ["bengaluru"]})}
        self.assertEqual((ok["CGPA"], ok["Batch"], ok["Location"]), ("ok", "ok", "ok"))

    def test_unknown_terms_surface(self):
        p = jd.analyze("T\nWe use Zorblax internally. Zorblax is great. Zorblax everywhere.", self.t)
        self.assertIn("Zorblax", dict(p.unknown_terms))

    def test_empty_and_noise_do_not_crash(self):
        for text in ("", "   \n\n", "!!!???", "\x00\x01"):
            p = jd.analyze(text, self.t)
            self.assertEqual(p.skill_weights, {})


if __name__ == "__main__":
    unittest.main()
