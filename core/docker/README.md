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

## Frontend image

```sh
cd core
docker build -f docker/Dockerfile -t news-frontend-local .
```

The build context needs `web/`, `code/sync_web_data.sh` and `data/k5/`. The
image installs `bash` (alpine has none) because `npm run build` runs
`prebuild` → `bash ../code/sync_web_data.sh`, installs with `npm ci` against
the committed lock, and serves the filtered `dist/data` snapshot (no
`news_recent.json`, `feed_errors_*`, `promo_filtered_*`). Caddy serves `/srv`;
`/data/*` is handled without stripping the prefix, so it maps to `/srv/data`,
where Compose mounts `../data` read-only. A mount replaces the bundled
snapshot. The baseline `2e3b20fe80a91e9621a815a4d59b99bb4bd0343b` fails its
build because `code/sync_web_data.sh` is not copied into the image.

```sh
python3 -m unittest discover -s core/code/base/tests -p test_frontend_image.py -v
```

The tests build from `git ls-files`/`git archive` trees with synthetic data,
reproduce the baseline failure, check missing data and missing script fail the
build, and run the image with a private read-only synthetic mount, a read-only
root filesystem, dropped capabilities and no published port. They check SPA
fallback, a fixture read, a changed fixture re-read, CORS, the absence of
excluded files, and rejection of a malformed fixture. Without a Docker daemon
they skip, which is not proof.

Result of that command on the branch built from origin/main
`2e3b20fe80a91e9621a815a4d59b99bb4bd0343b` plus this change (tests build from
tracked files only): `Ran 9 tests ... OK`. The caddy binary carries a file
capability, so the test container drops all capabilities but adds back
`NET_BIND_SERVICE`; with none, `exec /usr/bin/caddy` fails.

## Scope

This covers the packaging of the data and frontend images for k5. It does not
deploy either service or alter schedules.
