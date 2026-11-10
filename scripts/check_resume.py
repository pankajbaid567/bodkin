#!/usr/bin/env python3
"""Checks the bank against your resume PDF: every claim that came from the resume must appear in it word for word,
and the skills lines, CGPA and batch must match. Needs `pdftotext` (poppler). The PDF is not stored in this repository.

  python3 scripts/check_resume.py /path/to/SDE_Backend.pdf
"""
import glob
import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def norm(s: str) -> str:
    for a, b in (("’", "'"), ("–", "-"), ("∼", "~"), ("•", ""), ("", "")):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def main(pdf: str) -> int:
    text = norm(subprocess.run(["pdftotext", "-layout", pdf, "-"], capture_output=True, text=True, check=True).stdout)
    problems = 0
    for f in sorted(glob.glob(str(ROOT / "bank" / "items" / "*.toml"))):
        d = tomllib.load(open(f, "rb"))
        if not any(c["proof"].get("note", "").startswith("From the resume") for c in d["claims"]):
            continue                         # items that are not on the resume (built later) are checked by their own proof artifacts
        for c in d["claims"]:
            if c["proof"].get("note", "").startswith("From the resume") and norm(c["text"].replace("**", "")) not in text:
                problems += 1
                print(f"NOT IN RESUME: {d['id']}/{c['id']}: {c['text'][:90]}")
        for k in ("date",):
            if d.get(k) and norm(d[k]) not in text:
                problems += 1
                print(f"DATE NOT IN RESUME: {d['id']}: {d[k]}")
    prof = tomllib.load(open(ROOT / "bank" / "profile.toml", "rb"))
    for cat, items in prof["skills"].items():
        if norm(f"{cat}: " + ", ".join(items)) not in text:
            problems += 1
            print(f"SKILLS LINE DIFFERS: {cat}")
    if str(prof["person"]["cgpa"]) not in text:
        problems += 1
        print("CGPA not in resume")
    if f"2024-{prof['person']['batch']}" not in text:
        problems += 1
        print("batch years not in resume")
    print("bank matches the resume" if not problems else f"{problems} difference(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]) if len(sys.argv) > 1 else sys.exit(__doc__))
