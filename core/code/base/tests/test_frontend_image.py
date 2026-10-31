"""Frontend-image build and Caddy runtime checks, included by make test.

Builds come from tracked files only (git ls-files / git archive) plus synthetic
k5 data in a temporary tree; repository data is never copied or mounted. Tests
need Docker with a usable daemon and network access for base images and npm. A
skip is an explicit capability gap, never packaged-image proof.
"""

import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import io
import tempfile
import time
import unittest
import uuid


ROOT = Path(__file__).resolve().parents[4]
# Unchanged packaging whose Dockerfile lacks code/sync_web_data.sh.
BASELINE = "2e3b20fe80a91e9621a815a4d59b99bb4bd0343b"
SNAPSHOT_PATHS = ("core/docker", "core/web", "core/code/sync_web_data.sh")
FIXTURE = {"fixture": "original", "items": [1]}
EXCLUDED = ("news_recent.json", "feed_errors_latest.json", "promo_filtered_x.json")


def run(*args, cwd=ROOT, timeout=60):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def output(result):
    return result.stdout + result.stderr


def snapshot(destination, revision=None):
    """Only tracked inputs, so untracked files cannot leak into the image."""
    if revision:
        result = subprocess.run(
            ["git", "archive", revision, *SNAPSHOT_PATHS], cwd=ROOT,
            capture_output=True, check=True, timeout=60,
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
                shutil.copymode(ROOT / name, target)
    return destination / "core"


def write_data(core):
    """Synthetic k5 data, including files that sync_web_data.sh must exclude."""
    vertical = core / "data/k5"
    vertical.mkdir(parents=True)
    (vertical / "latest.json").write_text(json.dumps(FIXTURE))
    for name in EXCLUDED:
        (vertical / name).write_text("{}")


def compose_frontend(core):
    result = run(
        "docker", "compose", "-f", str(core / "docker/docker-compose.yml"),
        "config", "--format", "json",
    )
    if result.returncode:
        raise AssertionError(output(result))
    return json.loads(result.stdout)["services"]["frontend"]


def build(core, tag):
    return run(
        "docker", "build", "--tag", tag, "--file", "docker/Dockerfile", ".",
        cwd=core, timeout=900,
    )


def parse_json(text):
    """Reject anything that is not the JSON the fixture is supposed to be."""
    return json.loads(text)


def require_docker(case):
    if not shutil.which("docker"):
        raise unittest.SkipTest("Docker unavailable; frontend-image proof NOT RUN")
    result = run("docker", "info")
    if result.returncode:
        raise unittest.SkipTest("Frontend-image proof NOT RUN: " + output(result).strip())
    result = run("docker", "compose", "version")
    if result.returncode:
        raise unittest.SkipTest(output(result))


class FrontendBuildTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        require_docker(cls)

    def build_tree(self, revision=None):
        temp = tempfile.TemporaryDirectory(prefix="news-frontend-build-")
        self.addCleanup(temp.cleanup)
        core = snapshot(Path(temp.name), revision)
        write_data(core)
        return core

    def tag(self):
        tag = "news-frontend-build:" + uuid.uuid4().hex
        self.addCleanup(run, "docker", "image", "rm", "-f", tag)
        return tag

    def test_baseline_fails_at_prebuild_for_missing_sync_script(self):
        result = build(self.build_tree(BASELINE), self.tag())
        self.assertNotEqual(result.returncode, 0, output(result))
        self.assertIn("sync_web_data.sh", output(result))

    def test_current_tree_builds_with_real_prebuild(self):
        result = build(self.build_tree(), self.tag())
        # Layers may be cached, so the sync's effect is asserted on the
        # runtime image in test_bundled_snapshot_is_filtered, not its log.
        self.assertEqual(result.returncode, 0, output(result))

    def test_missing_data_input_fails_build(self):
        core = self.build_tree()
        shutil.rmtree(core / "data/k5")
        result = build(core, self.tag())
        self.assertNotEqual(result.returncode, 0, output(result))

    def test_missing_sync_script_fails_build(self):
        core = self.build_tree()
        (core / "code/sync_web_data.sh").unlink()
        result = build(core, self.tag())
        self.assertNotEqual(result.returncode, 0, output(result))


class FrontendRuntimeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        require_docker(cls)
        cls.temp = tempfile.TemporaryDirectory(prefix="news-frontend-image-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.core = snapshot(Path(cls.temp.name))
        write_data(cls.core)
        cls.image = "news-frontend-test:" + uuid.uuid4().hex
        cls.addClassCleanup(run, "docker", "image", "rm", "-f", cls.image)
        result = build(cls.core, cls.image)
        if result.returncode:
            raise AssertionError("Frontend image build failed:\n" + output(result))

    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="news-frontend-mount-")
        self.addCleanup(temp.cleanup)
        self.mount = Path(temp.name)
        (self.mount / "k5").mkdir()
        self.fixture = self.mount / "k5/fixture.json"
        self.fixture.write_text(json.dumps({"mounted": "one"}))
        # The mount is private and synthetic; make it readable to the container user.
        for path in (self.mount, self.mount / "k5"):
            path.chmod(0o755)
        self.fixture.chmod(0o644)

    def start(self, mount=True):
        args = [
            "docker", "run", "-d", "--read-only", "--cap-drop", "ALL",
            # The caddy binary carries a file capability for this one; without
            # it in the bounding set exec fails ("operation not permitted").
            "--cap-add", "NET_BIND_SERVICE",
            "--tmpfs", "/config", "--tmpfs", "/data", "--tmpfs", "/tmp",
        ]
        if mount:
            args += ["--mount", f"type=bind,src={self.mount},dst=/srv/data,readonly"]
        result = run(*args, self.image)
        self.assertEqual(result.returncode, 0, output(result))
        name = result.stdout.strip()
        self.addCleanup(run, "docker", "rm", "-f", name)
        for _ in range(50):
            if self.get(name, "/").returncode == 0:
                return name
            time.sleep(0.2)
        self.fail("Caddy did not start:\n" + output(run("docker", "logs", name)))

    def get(self, name, path, *flags):
        return run("docker", "exec", name, "wget", "-q", "-O", "-", *flags,
                   "http://127.0.0.1:8080" + path)

    def test_compose_frontend_mount_matches_caddy_serving_root(self):
        service = compose_frontend(self.core)
        mounts = {mount["target"]: mount for mount in service["volumes"]}
        self.assertEqual(list(mounts), ["/srv/data"])
        self.assertTrue(mounts["/srv/data"]["read_only"])
        # Caddy serves from /srv, so /data/* is /srv/data/*, as mounted above.
        caddyfile = (self.core / "docker/Caddyfile").read_text()
        self.assertIn("root * /srv", caddyfile)
        self.assertNotIn("handle_path /data", caddyfile)

    def test_spa_fallback_fixture_read_and_reload(self):
        name = self.start()
        index = self.get(name, "/")
        self.assertEqual(index.returncode, 0, output(index))
        route = self.get(name, "/archive/no-such-route", "-S")
        self.assertEqual(route.returncode, 0, output(route))
        self.assertIn("HTTP/1.1 200", route.stderr)
        self.assertEqual(route.stdout, index.stdout)
        first = self.get(name, "/data/k5/fixture.json")
        self.assertEqual(first.stdout, self.fixture.read_text())
        self.assertEqual(parse_json(first.stdout), {"mounted": "one"})
        # Bundled snapshot is replaced, not merged, by the mount.
        self.assertNotEqual(self.get(name, "/data/k5/latest.json").returncode, 0)
        self.fixture.write_text(json.dumps({"mounted": "two-changed"}))
        later = self.get(name, "/data/k5/fixture.json")
        self.assertEqual(parse_json(later.stdout), {"mounted": "two-changed"})
        headers = self.get(name, "/data/k5/fixture.json", "-S")
        self.assertIn("access-control-allow-origin: *", headers.stderr.lower())

    def test_missing_data_file_is_not_spa_fallback(self):
        name = self.start()
        missing = self.get(name, "/data/k5/absent.json")
        self.assertNotEqual(missing.returncode, 0, output(missing))
        self.assertNotIn("<html", missing.stdout.lower())

    def test_bundled_snapshot_is_filtered(self):
        name = self.start(mount=False)
        bundled = self.get(name, "/data/k5/latest.json")
        self.assertEqual(parse_json(bundled.stdout), FIXTURE)
        for excluded in EXCLUDED:
            with self.subTest(excluded=excluded):
                result = self.get(name, f"/data/k5/{excluded}")
                self.assertNotEqual(result.returncode, 0, output(result))
                listing = run("docker", "exec", name, "find", "/srv", "-name", excluded)
                self.assertEqual(listing.stdout.strip(), "")

    def test_malformed_fixture_is_rejected(self):
        self.fixture.write_text("{not json")
        name = self.start()
        served = self.get(name, "/data/k5/fixture.json")
        self.assertEqual(served.stdout, "{not json")
        with self.assertRaises(json.JSONDecodeError):
            parse_json(served.stdout)


if __name__ == "__main__":
    unittest.main()
