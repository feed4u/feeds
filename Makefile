# Repository checks: `make lint` and `make test` from the repository root.
# Web dependencies are installed from core/web/package-lock.json (npm ci) the
# first time and again whenever the lock file changes. The Python suite uses
# only the standard library.

PYTHON ?= python3
WEB := core/web
WEB_DEPS := $(WEB)/node_modules/.package-lock.json

.PHONY: setup lint lint-python lint-web test test-python test-web

setup: $(WEB_DEPS)

$(WEB_DEPS): $(WEB)/package-lock.json $(WEB)/package.json
	cd $(WEB) && npm ci --no-audit --no-fund
	touch $@

lint: lint-python lint-web

lint-python:
	$(PYTHON) -m compileall -q core/code core/scripts

lint-web: $(WEB_DEPS)
	cd $(WEB) && npm run lint

test: test-python test-web

test-python:
	$(PYTHON) -m unittest discover -s core/code/base/tests -v

test-web: $(WEB_DEPS)
	cd $(WEB) && npm test
