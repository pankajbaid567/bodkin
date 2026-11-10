import unittest

from tests.helpers import real_taxonomy


class TaxonomyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t = real_taxonomy()

    def ids(self, text):
        return set(self.t.find(text))

    def test_shipped_taxonomy_is_valid(self):
        self.assertEqual(self.t.validate(), [])
        self.assertGreater(len(self.t.skills), 120)

    def test_symbol_heavy_names(self):
        got = self.ids("C++17, C#, .NET, Node.js, CI/CD, k8s, gRPC and TCP/IP")
        for s in ("cpp", "csharp", "nodejs", "cicd", "kubernetes", "grpc", "networking"):
            self.assertIn(s, got)

    def test_go_language_vs_english(self):
        self.assertIn("go", self.ids("We write services in Go and Rust."))
        self.assertIn("go", self.ids("Strong Go skills; golang preferred"))
        for bad in ("a go-getter with a go to market mindset", "Plan to go live, go beyond expectations", "We go through a lot"):
            self.assertNotIn("go", self.ids(bad), bad)

    def test_java_is_not_javascript(self):
        self.assertEqual(self.ids("JavaScript only"), {"javascript"})
        self.assertEqual(self.ids("Java only"), {"java"})

    def test_longer_match_wins(self):
        got = self.t.find("React Native apps and React web apps")
        self.assertEqual(len(got["reactnative"]), 1)
        self.assertEqual(len(got["react"]), 1)          # only the plain React
        self.assertNotIn("javascript", self.ids("Node.js backend"))

    def test_case_sensitive_words(self):
        self.assertIn("react", self.ids("Experience with React"))
        self.assertNotIn("react", self.ids("be ready to react quickly"))
        self.assertIn("rag", self.ids("We build RAG systems"))
        self.assertNotIn("rag", self.ids("a rag and a bone"))
        self.assertNotIn("c", self.ids("Plan C and vitamin C"))
        self.assertIn("c", self.ids("Systems programming in C/C++"))

    def test_name_is_alias(self):
        self.assertIn("python", self.ids("python"))
        self.assertIn("kubernetes", self.ids("KUBERNETES"))

    def test_no_double_count_inside_one_phrase(self):
        self.assertEqual(len(self.t.find("Spring Boot")["spring"]), 1)

    def test_offsets_point_at_the_text(self):
        text = "We use Redis and Kafka."
        for hits in self.t.find(text).values():
            for h in hits:
                self.assertEqual(text[h.start:h.end], h.text)


if __name__ == "__main__":
    unittest.main()
