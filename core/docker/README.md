# Data image

The existing data service packages `code/base` and `code/k5` and installs
`code/base/requirements.txt`. From a clean checkout, its build route is:

```sh
cd core
docker build -f docker/Dockerfile.data -t news-data-local .
```

The standalone image command fetches **k5** news. Compose's data command runs
category metadata → fetch → archive → k5 trends, stopping at the first nonzero
exit. Each command explicitly uses `--base-dir /app --vertical k5`. Source
definitions belong under `/app/source/k5`, mounted read-only; outputs belong
under `/app/data/k5`, on the writable data mount. Existing path CLI options
remain available when overriding an image command. The data service does not
merge or modify source definitions.

## Isolated verification

From the repository root:

```sh
python3 -m unittest discover -s core/code/base/tests -p test_data_image.py -v
```

These tests also run in the existing `make test` Python suite. They reproduce
the missing entrypoints in baseline `6306fdc3fbaa6e189718c832b4f45251580cf601`
using `git archive`; keep that commit available for the historical reproduction.
The baseline's COPY inputs exist, so this is a runtime packaging defect rather
than an absent-build-input claim. The same entrypoint resolution assertion
rejects the baseline and accepts the corrected packaging.

Image tests require Docker, Compose, a usable daemon, and access to the base
image and Python/build dependencies. They build with the declared Compose data
build context and Dockerfile, using only tracked input files in a fresh temporary
tree. They run the image's default command and Compose's parsed data command
directly in disposable containers; they never start the Compose stack. All
runtime containers have networking disabled, no published ports or fixed names,
a read-only root filesystem, an isolated read-only RSS/OPML source fixture and
an isolated writable data root. They run as the fixture owner's UID/GID with
capabilities dropped. No repository data volume, live feed, LLM or credentials
are passed to them.

Assertions re-read metadata, recent news, daily/monthly/yearly archives, latest,
the chunk manifest and trends, then repeat the sequence to verify persistence
and deduplication. Fixture and repository source hashes must remain unchanged.
Negative cases cover invalid CLI options, missing OPML and archive input,
malformed trends JSON, tolerated individual-feed errors, and failures in the
four-stage sequence reaching the container status without running later stages.
Missing Docker/Compose capability is reported as a test skip, **not** evidence
that the packaged image works. Build or runtime failures on an available daemon
fail the suite.

## Scope

This verifies only the data image for k5. The separate frontend image still
lacks the code needed by its prebuild data-sync step, and Compose mounts its
data at an nginx path although the runtime uses Caddy. Neither is repaired or
verified here. This change does not deploy either service or alter schedules.
