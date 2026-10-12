PYTHON ?= python3

.PHONY: patch-solver build-solver freeze-manifests test

patch-solver:
	git -C vendor/Kangaroo apply ../../patches/kangaroo/lab-instrumentation.patch

build-solver:
	./scripts/build_solver.sh

freeze-manifests:
	$(PYTHON) scripts/freeze_manifest.py modes/smoke.json configs/smoke.manifest.json
	$(PYTHON) scripts/freeze_manifest.py modes/research.json configs/research.manifest.json
	$(PYTHON) scripts/freeze_manifest.py modes/miracle.json configs/miracle.manifest.json

test:
	$(PYTHON) -m unittest discover -s tests -v
