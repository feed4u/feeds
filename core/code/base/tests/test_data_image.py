"""Data-image regression and isolated runtime checks, included by make test.

The input tests need only Python and the Compose client (no daemon). Image
tests additionally need a usable Docker daemon and build dependencies. A skip
is an explicit capability gap, never packaged-image proof.
"""

from datetime import datetime, timezone
from email.utils import format_datetime
import hashlib
import io
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
import uuid


ROOT = Path(__file__).resolve().parents[4]
BASELINE = "6306fdc3fbaa6e189718c832b4f45251580cf601"
SNAPSHOT_PATHS = ("core/docker", "core/code", "core/source", "core/scripts")


def run(*args, cwd=ROOT, timeout=60):
    return subprocess.run(
        args, cwd=cwd, capture_output=True, text=True, timeout=timeout,
    )


def output(result):
    return result.stdout + result.stderr


def compose_data(core):
    result = run(
        "docker", "compose", "-f", str(core / "docker/docker-compose.yml"),
        "config", "--format", "json",
    )
    if result.returncode:
        raise AssertionError(output(result))
    return json.loads(result.stdout)["services"]["data"]


def snapshot(destination, revision=None):
    """Only tracked inputs: exclude local caches, datasets and credentials."""
    if revision:
        result = subprocess.run(
            ["git", "archive", revision, *SNAPSHOT_PATHS], cwd=ROOT,
            capture_output=True, check=True, timeout=30,
        )
        with tarfile.open(fileobj=io.BytesIO(result.stdout)) as archive:
            archive.extractall(destination, filter="data")
    else:
        result = run("git", "ls-files", "-z", "--", *SNAPSHOT_PATHS)
        if result.returncode:
            raise AssertionError(output(result))
        for name in result.stdout.split("\0"):
            if name:
                target = destination / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, target)
    return destination / "core"


def copied_inputs(core, app):
    """Materialize this Dockerfile's simple COPY inputs, without claiming a build."""
    for line in (core / "docker/Dockerfile.data").read_text().splitlines():
        if not line.startswith("COPY "):
            continue
        _, source, target = shlex.split(line)
        source = core / source
        target = app / Path(target).relative_to("/app")
        if source.is_dir():
            shutil.copytree(source, target, dirs_exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)


def default_command(core):
    lines = (core / "docker/Dockerfile.data").read_text().splitlines()
    return json.loads(next(line[4:] for line in lines if line.startswith("CMD ")))


def stages(service):
    command = service["command"]
    if command[:2] != ["/bin/sh", "-c"]:
        raise AssertionError(f"Unexpected data command: {command}")
    return [shlex.split(stage) for stage in command[2].split("&&")]


def require_entrypoints(app, commands):
    for command in commands:
        script = app / Path(command[1]).relative_to("/app")
        if not script.is_file():
            raise AssertionError(f"Packaged entrypoint missing: {command[1]}")


def hashes(directory):
    return {
        str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in directory.rglob("*") if path.is_file()
    }


def write_fixture(source):
    vertical = source / "k5"
    vertical.mkdir(parents=True)
    now = datetime.now(timezone.utc)
    (vertical / "feed.rss").write_text(f"""<?xml version="1.0"?>
<rss version="2.0"><channel><title>Offline security fixture</title>
<link>https://fixture.invalid/</link><description>Local test only</description>
<item><title>Offline ransomware vulnerability report</title>
<link>https://fixture.invalid/report</link><guid>offline-image-fixture</guid>
<pubDate>{format_datetime(now)}</pubDate>
<description>Researchers describe a ransomware vulnerability and patch.</description>
</item></channel></rss>""")
    opml = """<?xml version="1.0"?>
<opml version="2.0"><body><outline text="Security fixture">
<outline text="Offline feed" xmlUrl="file:///app/source/k5/feed.rss"/>
</outline></body></opml>"""
    (vertical / "feeds.xml").write_text(opml)
    (vertical / "news.xml").write_text(opml)
    return now


class DataBuildInputsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("docker"):
            raise unittest.SkipTest("Docker/Compose client unavailable; input regression not run")
        result = run("docker", "compose", "version")
        if result.returncode:
            raise unittest.SkipTest(output(result))

    def test_clean_baseline_copies_exist_but_entrypoints_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            core = snapshot(Path(temp), BASELINE)
            app = Path(temp) / "app"
            # The old COPY inputs exist: do not assert the disproven premise.
            copied_inputs(core, app)
            commands = [default_command(core), *stages(compose_data(core))]
            self.assertEqual(len(commands), 5)
            # The same regression assertion must reject the old packaging.
            with self.assertRaisesRegex(AssertionError, "Packaged entrypoint missing"):
                require_entrypoints(app, commands)
            for command in commands:
                with self.subTest(command=command):
                    script = app / Path(command[1]).relative_to("/app")
                    result = run(sys.executable, str(script), "--help")
                    self.assertEqual(result.returncode, 2, output(result))
                    self.assertIn("No such file or directory", result.stderr)

    def test_current_copies_resolve_default_and_all_compose_entrypoints(self):
        with tempfile.TemporaryDirectory() as temp:
            core = snapshot(Path(temp))
            app = Path(temp) / "app"
            copied_inputs(core, app)
            service = compose_data(core)
            commands = [default_command(core), *stages(service)]
            self.assertEqual(len(commands), 5)
            require_entrypoints(app, commands)
            self.assertEqual(service["build"]["dockerfile"], "docker/Dockerfile.data")
            self.assertEqual(Path(service["build"]["context"]), core)
            mounts = {mount["target"]: mount for mount in service["volumes"]}
            self.assertTrue(mounts["/app/source"]["read_only"])
            self.assertFalse(mounts["/app/data"].get("read_only", False))
            for command in commands:
                with self.subTest(command=command):
                    self.assertTrue((app / Path(command[1]).relative_to("/app")).is_file())
                    self.assertEqual(command[command.index("--vertical") + 1], "k5")
                    self.assertEqual(command[command.index("--base-dir") + 1], "/app")
            # Execute a real copied entrypoint with a non-default root, not a text search.
            metadata = app / Path(commands[1][1]).relative_to("/app")
            fixture = Path(temp) / "isolated"
            write_fixture(fixture / "source")
            before = hashes(fixture / "source")
            args = [sys.executable, str(metadata), "--base-dir", str(fixture), "--vertical", "k5"]
            result = run(*args)
            self.assertEqual(result.returncode, 0, output(result))
            saved = json.loads((fixture / "data/k5/category_metadata.json").read_text())
            self.assertEqual(saved["slug_to_label"], {"security-fixture": "Security fixture"})
            self.assertEqual(hashes(fixture / "source"), before)
            invalid = run(*args, "--not-an-option")
            self.assertEqual(invalid.returncode, 2, output(invalid))
            missing = run(sys.executable, str(metadata), "--base-dir", str(fixture / "absent"), "--vertical", "k5")
            self.assertEqual(missing.returncode, 1, output(missing))


class DataImageRuntimeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("docker"):
            raise unittest.SkipTest("Docker unavailable; packaged-image proof NOT RUN")
        result = run("docker", "info")
        if result.returncode:
            raise unittest.SkipTest("Packaged-image proof NOT RUN: " + output(result).strip())
        cls.temp = tempfile.TemporaryDirectory(prefix="news-data-image-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.core = snapshot(Path(cls.temp.name))
        cls.service = compose_data(cls.core)
        cls.image = "news-data-test:" + uuid.uuid4().hex
        cls.addClassCleanup(run, "docker", "image", "rm", cls.image)
        result = run(
            "docker", "build", "--tag", cls.image,
            "--file", cls.service["build"]["dockerfile"], ".",
            cwd=cls.service["build"]["context"], timeout=600,
        )
        if result.returncode:
            raise AssertionError("Data image build failed:\n" + output(result))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="news-data-fixture-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.data = self.root / "data"
        self.data.mkdir()
        self.now = write_fixture(self.source)
        self.before = hashes(self.source)
        self.original_sources = hashes(ROOT / "core/source")

    def tearDown(self):
        self.assertEqual(hashes(self.source), self.before)
        self.assertEqual(hashes(ROOT / "core/source"), self.original_sources)

    def container(self, *command):
        return run(
            "docker", "run", "--rm", "--network", "none", "--read-only",
            "--tmpfs", "/tmp", "--cap-drop", "ALL",
            "--user", f"{os.getuid()}:{os.getgid()}",
            "--mount", f"type=bind,src={self.source},dst=/app/source,readonly",
            "--mount", f"type=bind,src={self.data},dst=/app/data",
            self.image, *command, timeout=60,
        )

    def read_json(self, relative):
        return json.loads((self.data / "k5" / relative).read_text())

    def assert_item(self, items):
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["link"], "https://fixture.invalid/report")

    def test_packaged_cli_imports_arguments_and_invalid_option(self):
        for command in stages(self.service):
            with self.subTest(script=command[1]):
                args = [
                    *command, "--data-dir", "/app/data", "--opml-path", "/app/source/k5/feeds.xml",
                    "--output-path", "/app/data/override.json", "--archive-dir", "/app/data/archive",
                ]
                result = self.container(*args, "--help")
                self.assertEqual(result.returncode, 0, output(result))
                self.assertIn("--vertical", result.stdout)
                invalid = self.container(*args, "--not-an-option")
                self.assertEqual(invalid.returncode, 2, output(invalid))

    def test_default_fetch_command_and_supported_path_overrides(self):
        result = self.container()
        self.assertEqual(result.returncode, 0, output(result))
        self.assert_item(self.read_json("news_recent.json")["items"])
        # Use actual path overrides, rather than help alone accepting the spellings.
        for index, command in enumerate(stages(self.service)):
            with self.subTest(script=command[1]):
                primary = "custom/k5/custom-metadata.json" if index == 0 else "custom-items.json"
                extra = ["--trends-path", "/app/data/custom-trends.json"] if index == 3 else []
                result = self.container(
                    *command, "--data-dir", "/app/data/custom",
                    "--opml-path", "/app/source/k5/feeds.xml",
                    "--output-path", f"/app/data/{primary}",
                    "--archive-dir", "/app/data/custom-archive", *extra,
                )
                self.assertEqual(result.returncode, 0, output(result))
        self.assert_item(json.loads((self.data / "custom-items.json").read_text())["items"])
        metadata = json.loads((self.data / "custom/k5/custom-metadata.json").read_text())
        self.assertEqual(metadata["slug_to_label"], {"security-fixture": "Security fixture"})
        latest = json.loads((self.data / "custom/k5/latest.json").read_text())
        self.assert_item(latest["items"])
        date = self.now.strftime("%Y-%m-%d")
        daily = json.loads((self.data / f"custom-archive/news/daily/{date}.json").read_text())
        self.assert_item(daily["items"])
        trends = json.loads((self.data / "custom-trends.json").read_text())
        self.assertEqual(trends["summary"]["total_articles"], 1)

    def test_real_compose_sequence_persists_archive_manifest_and_trends(self):
        result = self.container(*self.service["command"])
        self.assertEqual(result.returncode, 0, output(result))
        metadata = self.read_json("category_metadata.json")
        self.assertEqual(metadata["slug_to_label"], {"security-fixture": "Security fixture"})
        self.assert_item(self.read_json("news_recent.json")["items"])
        self.assert_item(self.read_json("latest.json")["items"])
        date = self.now.strftime("%Y-%m-%d")
        month = self.now.strftime("%Y-%m")
        year = self.now.strftime("%Y")
        self.assert_item(self.read_json(f"archive/news/daily/{date}.json")["items"])
        self.assert_item(self.read_json(f"archive/news/monthly/{year}/{month}.json"))
        self.assert_item(self.read_json(f"archive/news/yearly/{year}.json"))
        manifest = self.read_json("index.json")
        self.assertEqual(manifest["latest"]["item_count"], 1)
        self.assertEqual(manifest["daily"][0]["file"], f"archive/news/daily/{date}.json")
        self.assertEqual(self.read_json("trends.json")["summary"]["total_articles"], 1)
        # A second container must read the saved artifacts and keep one item.
        result = self.container(*self.service["command"])
        self.assertEqual(result.returncode, 0, output(result))
        self.assert_item(self.read_json(f"archive/news/daily/{date}.json")["items"])
        self.assertFalse((self.data / "category_metadata.json").exists())
        self.assertFalse((self.data / "news_recent.json").exists())

    def test_missing_opml_fails_and_stops_real_compose_sequence(self):
        shutil.rmtree(self.source / "k5")
        self.before = hashes(self.source)
        result = self.container(*self.service["command"])
        self.assertEqual(result.returncode, 1, output(result))
        self.assertIn("No OPML sources found", output(result))
        self.assertEqual(list(self.data.rglob("*.json")), [])
        result = self.container(*stages(self.service)[1])
        self.assertNotEqual(result.returncode, 0, output(result))
        self.assertIn("No feed sources found", output(result))

    def test_fetch_failure_stops_archive_and_trends(self):
        # Metadata succeeds on valid OPML; fetching fails because it has no feeds.
        (self.source / "k5/news.xml").unlink()
        (self.source / "k5/feeds.xml").write_text("<opml><body/></opml>")
        self.before = hashes(self.source)
        result = self.container(*self.service["command"])
        self.assertNotEqual(result.returncode, 0, output(result))
        self.assertTrue((self.data / "k5/category_metadata.json").exists())
        self.assertFalse((self.data / "k5/news_recent.json").exists())
        self.assertFalse((self.data / "k5/index.json").exists())
        self.assertFalse((self.data / "k5/trends.json").exists())

    def test_missing_archive_input_and_malformed_trends_are_nonzero(self):
        commands = stages(self.service)
        result = self.container(*commands[2])
        self.assertNotEqual(result.returncode, 0, output(result))
        self.assertIn("Recent file not found", output(result))
        (self.data / "k5").mkdir(exist_ok=True)
        (self.data / "k5/news_recent.json").write_text("{not json")
        result = self.container(*commands[3])
        self.assertEqual(result.returncode, 1, output(result))
        self.assertIn("Invalid data", output(result))
        self.assertFalse((self.data / "k5/trends.json").exists())

    def test_archive_failure_stops_trends_and_reaches_container_status(self):
        # Fetch can save recent items, but latest.json cannot be written.
        (self.data / "k5/latest.json").mkdir(parents=True)
        result = self.container(*self.service["command"])
        self.assertNotEqual(result.returncode, 0, output(result))
        self.assertIn("Is a directory", output(result))
        self.assert_item(self.read_json("news_recent.json")["items"])
        self.assertFalse((self.data / "k5/trends.json").exists())

    def test_bad_individual_feed_remains_tolerated_but_empty_trends_fails(self):
        (self.source / "k5/feed.rss").write_text("not an RSS document")
        self.before = hashes(self.source)
        # Fetch reports individual bad feeds rather than failing the whole run.
        result = self.container(*stages(self.service)[1])
        self.assertEqual(result.returncode, 0, output(result))
        self.assertEqual(self.read_json("news_recent.json")["items"], [])
        # The unchanged trends CLI refuses an empty report at the last stage.
        result = self.container(*self.service["command"])
        self.assertEqual(result.returncode, 1, output(result))
        self.assertIn("No news items found", output(result))
        self.assertFalse((self.data / "k5/trends.json").exists())


if __name__ == "__main__":
    unittest.main()
