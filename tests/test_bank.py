import tempfile
import shutil
import unittest
from pathlib import Path

from bodkin.bank import Bank, BankError
from bodkin.lint import Linter, numbers_in
from tests.helpers import TODAY, copy_bank, real_bank, real_taxonomy


class ShippedBankTests(unittest.TestCase):
    def test_shipped_bank_validates_strictly_except_known_long_line(self):
        bank, tax, lint = real_bank(), real_taxonomy(), Linter.load()
        issues = bank.validate(tax, lint, strict=False, today=TODAY)
        self.assertEqual([i for i in issues if i.level == "error"], [])
        # warnings are only length notes on lines that come straight from the resume
        self.assertTrue(all("LONG" in i.message for i in issues), [i.message for i in issues])

    def test_proof_artifacts_exist_for_proven_claims(self):
        bank = real_bank()
        errs = [i for i in bank.check_proofs() if i.level == "error"]
        self.assertEqual(errs, [], errs)

    def test_every_proven_claim_has_command_and_artifact(self):
        for it in real_bank().items.values():
            for c in it.claims:
                if c.proof.status == "proven":
                    self.assertTrue(c.proof.command and c.proof.artifact, c.uid)


class RuleTests(unittest.TestCase):
    def setUp(self):
        self.tax, self.lint = real_taxonomy(), Linter.load()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = copy_bank(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def edit(self, name, old, new):
        p = self.root / "items" / name
        s = p.read_text()
        self.assertIn(old, s)
        p.write_text(s.replace(old, new))

    def issues(self, strict=False):
        return Bank.load(self.root).validate(self.tax, self.lint, strict=strict, today=TODAY)

    def test_number_not_declared_is_an_error(self):
        self.edit("codechef.toml", "rating **1638**", "rating **1639**")
        self.assertTrue(any("1639" in i.message and i.level == "error" for i in self.issues()))

    def test_declared_number_that_never_appears_warns(self):
        self.edit("codechef.toml", 'numbers = ["3", "1638", "600"]', 'numbers = ["3", "1638", "600", "999"]')
        self.assertTrue(any("999" in i.message for i in self.issues()))

    def test_banned_phrase_is_an_error_unless_allowed(self):
        self.edit("codechef.toml", "CodeChef 3-star", "Fault-tolerant CodeChef 3-star")
        self.assertTrue(any(i.level == "error" and "BANNED" in i.message for i in self.issues()))
        self.edit("codechef.toml", 'numbers = ["3", "1638", "600"]', 'numbers = ["3", "1638", "600"]\nallow = ["fault-tolerant"]')
        self.assertFalse(any("BANNED" in i.message for i in self.issues()))

    def test_unknown_skill_id_and_archetype(self):
        self.edit("codechef.toml", "skills = { dsa = 1.0 }", "skills = { dsa = 1.0, nonsense = 0.5 }")
        self.assertTrue(any("nonsense" in i.message for i in self.issues()))
        self.edit("codechef.toml", "archetypes = { backend = 0.3 }", "archetypes = { backendz = 0.3 }")
        self.assertTrue(any("backendz" in i.message for i in self.issues()))

    def test_proven_without_command_is_an_error(self):
        self.edit("pitbook.toml", 'command = "make bench"\nartifact = "bench/results/loadgen-*.csv"', 'artifact = "bench/results/loadgen-*.csv"')
        self.assertTrue(any("needs proof.command" in i.message for i in self.issues()))

    def test_strict_turns_warnings_into_errors(self):
        self.assertEqual([i for i in self.issues(strict=False) if i.level == "error"], [])
        self.assertTrue([i for i in self.issues(strict=True) if i.level == "error"])

    def test_stale_proof_warns(self):
        self.edit("pitbook.toml", 'date = "2026-11-10"\nlimits = "Simulator: one venue, no real money."', 'date = "2025-01-01"\nlimits = "Simulator: one venue, no real money."')
        self.assertTrue(any("days old" in i.message for i in self.issues()))

    def test_duplicate_id_and_bad_toml(self):
        (self.root / "items" / "dup.toml").write_text((self.root / "items" / "codechef.toml").read_text())
        with self.assertRaises(BankError):
            Bank.load(self.root)
        (self.root / "items" / "dup.toml").write_text("this is = = not toml")
        with self.assertRaises(BankError):
            Bank.load(self.root)

    def test_missing_proof_artifact_detected(self):
        self.edit("pitbook.toml", 'artifact = "bench/results/property-*.txt"', 'artifact = "bench/results/nope-*.txt"')
        # Self-contained: repo paths are relative to the bank, so build x/y/bank next to a real x/Pitbook directory that exists
        # but lacks the artifact. (The test used to rely on a sibling Pitbook checkout and failed on a fresh clone.)
        root = Path(self.tmp.name) / "x" / "y" / "bank"
        shutil.copytree(self.root, root)
        (root / ".." / ".." / "Pitbook" / "bench" / "results").resolve().mkdir(parents=True)
        bank = Bank.load(root)
        self.assertTrue(any("nope" in i.message for i in bank.check_proofs()))


class NumberTokenTests(unittest.TestCase):
    def test_numbers(self):
        self.assertEqual(numbers_in("**1,000,000** commands, p99 346 ms, k6, R2 and 3.5x, 0.25 ms, PR #42373"),
                         ["1,000,000", "346", "3.5", "0.25", "42373"])
        self.assertEqual(numbers_in("no digits"), [])


if __name__ == "__main__":
    unittest.main()
