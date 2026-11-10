import contextlib
import http.client
import io
import json
import socket
import threading
import unittest
from http.server import ThreadingHTTPServer

from bodkin import cli, jd as jdmod, render, select as S
from bodkin.server import make_handler
from tests.helpers import ROOT, TODAY, real_bank, real_taxonomy

FX = ROOT / "jds" / "fixtures"


def run_cli(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = cli.main(list(argv))
        except SystemExit as e:
            code = e.code if isinstance(e.code, int) else 2
    return code, out.getvalue(), err.getvalue()


class RenderTests(unittest.TestCase):
    def test_tex_escape_every_special_character(self):
        self.assertEqual(render.tex_escape(r"a & b % c $ d # e _ f { g } h ~ i ^ j \ k"),
                         r"a \& b \% c \$ d \# e \_ f \{ g \} h \textasciitilde{} i \textasciicircum{} j \textbackslash{} k")
        self.assertIn("--", render.tex_escape("a – b"))

    def test_bold_markup(self):
        self.assertEqual(render.tex_bold("up to **11.5** points & more"), r"up to \textbf{11.5} points \& more")
        self.assertEqual(render.tex_bold("**a** and **b**"), r"\textbf{a} and \textbf{b}")

    def test_all_formats_render_and_json_round_trips(self):
        tax, bank = real_taxonomy(), real_bank()
        text = (FX / "09-quant-developer-intern.txt").read_text()
        sel = S.select(jdmod.analyze(text, tax), bank, tax, S.Options(today=TODAY))
        md, tx, tex = render.to_markdown(sel, bank, tax), render.to_text(sel), render.to_tex(sel)
        d = json.loads(render.to_json(sel, bank, tax))
        self.assertIn("Pitbook", md)
        self.assertIn("PROJECTS", tx)
        self.assertIn(r"\begin{itemize}", tex)
        self.assertEqual(d["projects"][0]["id"], "pitbook")
        self.assertEqual(tex.count(r"\begin{itemize}"), tex.count(r"\end{itemize}"))
        # no stray markdown bold markers in plain text or LaTeX output
        self.assertNotIn("**", tx)
        self.assertNotIn("**", tex)


class CliTests(unittest.TestCase):
    def test_validate_list_claims_taxonomy(self):
        self.assertEqual(run_cli("validate", "--today", "2026-11-10")[0], 0)
        code, out, _ = run_cli("list")
        self.assertEqual(code, 0)
        self.assertIn("pitbook", out)
        self.assertEqual(run_cli("taxonomy")[0], 0)
        self.assertEqual(run_cli("claims", "--check")[0], 0)

    def test_analyze_formats_and_stdin_style_flags(self):
        f = str(FX / "03-razorpay-product-engineer-intern.txt")
        for fmt in ("md", "json", "tex", "txt"):
            code, out, _ = run_cli("analyze", f, "--format", fmt, "--today", "2026-11-10", "--top", "2")
            self.assertEqual(code, 0, fmt)
            self.assertTrue(out.strip(), fmt)
        d = json.loads(run_cli("analyze", f, "--format", "json", "--today", "2026-11-10", "--no-fill")[1])
        self.assertTrue(all(not p["filler"] for p in d["projects"]))

    def test_global_flags_work_after_the_subcommand(self):
        self.assertEqual(run_cli("validate", "--bank", str(ROOT / "bank"), "--today", "2026-11-10")[0], 0)

    def test_batch_and_explain(self):
        code, out, _ = run_cli("batch", str(FX), "--today", "2026-11-10")
        self.assertEqual(code, 0)
        self.assertIn("build next", out)
        code, out, _ = run_cli("explain", "pitbook", str(FX / "09-quant-developer-intern.txt"), "--today", "2026-11-10")
        self.assertEqual(code, 0)
        self.assertIn("Trading systems", out)
        self.assertNotEqual(run_cli("explain", "nope", str(FX / "09-quant-developer-intern.txt"))[0], 0)

    def test_errors_are_clean(self):
        self.assertEqual(run_cli("analyze", "/definitely/not/here.txt")[0], 2)
        self.assertNotEqual(run_cli("validate", "--bank", "/definitely/not/a/bank")[0], 0)


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        cls.port = s.getsockname()[1]
        s.close()
        cls.srv = ThreadingHTTPServer(("127.0.0.1", cls.port), make_handler(str(ROOT / "bank"), None, None, cls.port))
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def req(self, method, path, body=None, host=None, headers=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        h = {"Host": host or f"127.0.0.1:{self.port}", **(headers or {})}
        c.request(method, path, body=body, headers=h)
        r = c.getresponse()
        return r.status, r.read(), dict(r.getheaders())

    def test_index_and_bank(self):
        st, body, hd = self.req("GET", "/")
        self.assertEqual(st, 200)
        self.assertIn(b"Bodkin", body)
        self.assertIn("default-src 'self'", hd["Content-Security-Policy"])
        st, body, _ = self.req("GET", "/api/bank")
        self.assertEqual(st, 200)
        self.assertTrue(any(i["id"] == "pitbook" for i in json.loads(body)["items"]))

    def test_analyze(self):
        payload = json.dumps({"jd": (FX / "09-quant-developer-intern.txt").read_text(), "top": 2, "bullets": 3})
        st, body, _ = self.req("POST", "/api/analyze", payload, headers={"Content-Type": "application/json", "Content-Length": str(len(payload))})
        self.assertEqual(st, 200)
        d = json.loads(body)
        self.assertEqual(d["projects"][0]["id"], "pitbook")
        self.assertIn("tex", d)

    def test_rejects_foreign_host_oversize_and_garbage(self):
        self.assertEqual(self.req("GET", "/", host="evil.example")[0], 403)
        self.assertEqual(self.req("POST", "/api/analyze", "x" * 10, headers={"Content-Length": str(2_000_000)})[0], 413)
        self.assertEqual(self.req("POST", "/api/analyze", "not json")[0], 400)
        self.assertEqual(self.req("GET", "/nope")[0], 404)


if __name__ == "__main__":
    unittest.main()
