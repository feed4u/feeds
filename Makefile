# Repository checks. `make lint` and `make test` are what the PR gate runs.
.PHONY: lint test

lint:
	python3 -m compileall -q core/code

test:
	python3 -m unittest discover -s core/code/base/tests -v
