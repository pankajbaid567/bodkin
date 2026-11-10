"""Local web UI: a thin client over the same analysis code (ADR-009). Binds 127.0.0.1 only."""
from __future__ import annotations

import json
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import jd as jdmod, render, select as sel_mod
from .bank import Bank, BankError
from .lint import Linter
from .taxonomy import Taxonomy

WEB = Path(__file__).resolve().parent.parent.parent / "web" / "index.html"
MAX_BODY = 1_000_000


def analyze_request(bank_dir, tax_path, lint_path, payload: dict) -> dict:
    """Run one analysis for a JSON payload. Reloads the bank each time so edits show immediately."""
    tax = Taxonomy.load(tax_path)
    bank = Bank.load(bank_dir)
    opts = sel_mod.Options(
        top=max(1, min(int(payload.get("top", 3)), 6)), bullets=max(1, min(int(payload.get("bullets", 4)), 8)),
        include_pending=bool(payload.get("include_pending", False)), include_wip=bool(payload.get("include_wip", True)),
        variant=str(payload.get("variant", "auto")), fill=bool(payload.get("fill", True)), today=date.today())
    jd = jdmod.analyze(str(payload.get("jd", "")), tax)
    sel = sel_mod.select(jd, bank, tax, opts)
    out = render.to_dict(sel, bank, tax)
    out["tex"] = render.to_tex(sel)
    out["text"] = render.to_text(sel)
    out["markdown"] = render.to_markdown(sel, bank, tax)
    return out


def make_handler(bank_dir, tax_path, lint_path, port: int):
    allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}

    class H(BaseHTTPRequestHandler):
        server_version = "bodkin"

        def log_message(self, fmt, *a):  # quiet
            pass

        def _send(self, code: int, body: bytes, ctype: str = "application/json") -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'")
            self.end_headers()
            self.wfile.write(body)

        def _host_ok(self) -> bool:  # refuse DNS-rebinding style requests
            return self.headers.get("Host", "") in allowed_hosts

        def do_GET(self):
            if not self._host_ok():
                return self._send(403, b'{"error":"bad host"}')
            if self.path in ("/", "/index.html"):
                return self._send(200, WEB.read_bytes(), "text/html; charset=utf-8")
            if self.path == "/api/bank":
                try:
                    bank = Bank.load(bank_dir)
                except BankError as e:
                    return self._send(500, json.dumps({"error": str(e)}).encode())
                items = [{"id": i.id, "kind": i.kind, "status": i.status, "title": i.title, "claims": len(i.claims)} for i in bank.items.values()]
                return self._send(200, json.dumps({"items": items}).encode())
            self._send(404, b'{"error":"not found"}')

        def do_POST(self):
            if not self._host_ok():
                return self._send(403, b'{"error":"bad host"}')
            if self.path != "/api/analyze":
                return self._send(404, b'{"error":"not found"}')
            n = int(self.headers.get("Content-Length", "0") or 0)
            if n <= 0 or n > MAX_BODY:
                return self._send(413, b'{"error":"body must be 1 byte to 1 MB"}')
            try:
                payload = json.loads(self.rfile.read(n))
                return self._send(200, json.dumps(analyze_request(bank_dir, tax_path, lint_path, payload), ensure_ascii=False).encode())
            except (ValueError, KeyError, BankError) as e:
                return self._send(400, json.dumps({"error": str(e)}).encode())

    return H


def serve(bank_dir, tax_path, lint_path, port: int = 8787) -> None:
    srv = ThreadingHTTPServer(("127.0.0.1", port), make_handler(bank_dir, tax_path, lint_path, port))
    print(f"Bodkin UI on http://127.0.0.1:{port}  (Ctrl+C to stop; nothing leaves this machine)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
