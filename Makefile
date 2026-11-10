.PHONY: test validate eval mutants batch serve clean

test:
	python3 -m unittest discover -s tests -t .

validate:
	./bodkin validate && ./bodkin claims --check

eval:
	./bodkin eval

# Injects 6 deliberate bugs into a scratch copy; the suite must catch every one.
mutants:
	./scripts/mutation_check.sh

# Analyse every JD in jds/fixtures and jds/private (if present) and summarise portfolio gaps.
batch:
	mkdir -p out
	./bodkin batch jds/fixtures jds/private --out out/batch.md

serve:
	./bodkin serve

# Generated files only: the output folder and Python bytecode caches.
clean:
	rm -rf out
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
