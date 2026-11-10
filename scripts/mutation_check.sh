#!/usr/bin/env bash
# Injects deliberate bugs into a scratch copy of Bodkin and requires the test suite to fail for each.
# The repository itself is never modified.
set -uo pipefail
cd "$(dirname "$0")/.."
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
rsync -a --exclude .git --exclude __pycache__ ./ "$TMP/src/"
# the shipped bank points at sibling projects for proof checks; keep those resolvable
ln -s "$(cd .. && pwd)" "$TMP/flagships" 2>/dev/null || true
cd "$TMP/src"
caught=0; total=0
mut() { # name, file, python expression old, new
  cp "$2" "$2.orig"
  python3 - "$2" "$3" "$4" <<'PY'
import sys
p, old, new = sys.argv[1:4]
s = open(p).read()
if old not in s:
    print("MUTATION TEXT NOT FOUND"); sys.exit(3)
open(p, "w").write(s.replace(old, new, 1))
PY
  rc=$?
  total=$((total+1))
  if [ $rc -ne 0 ]; then echo "$1: mutation did not apply"; mv "$2.orig" "$2"; return; fi
  if python3 -m unittest discover -s tests -t . >/dev/null 2>&1; then echo "$1: SURVIVED (tests did not notice)"; else echo "$1: killed"; caught=$((caught+1)); fi
  mv "$2.orig" "$2"
}
mut "section weights ignored (every line weighs 1.0)"      src/bodkin/jd.py       'w = SECTION_WEIGHT.get(section, 0.7)' 'w = 1.0'
mut "no diminishing returns after picking a project"        src/bodkin/select.py   'rem[key] *= 1.0 - DIMINISH * _item_cov(best.item, key)' 'rem[key] *= 1.0'
mut "pending claims are emitted without the flag"           src/bodkin/bank.py     'if c.proof.status != "pending" or include_pending' 'if True'
mut "undeclared numbers are no longer rejected"             src/bodkin/bank.py     'if n not in allowed:' 'if False:'
mut "stop phrases ignored (go-getter counts as Go)"         src/bodkin/taxonomy.py 'if covered is not None and any(covered[m.start():m.end()]):' 'if False:'
mut "bullet variants always used even when the JD does not point at them" src/bodkin/select.py 'if a >= VARIANT_MIN and a > best_a:' 'if a >= 0.0 and a >= best_a:'
echo "mutations killed: $caught of $total"
[ "$caught" -eq "$total" ]
