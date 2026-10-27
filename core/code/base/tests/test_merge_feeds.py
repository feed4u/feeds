import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
CORE = BASE.parents[1]
SCRIPT = BASE / "merge_feeds.py"

sys.path.insert(0, str(BASE))
from path_utils import canonical_section, resolve_section_file, section_candidates  # noqa: E402


def opml(*groups):
    """groups: (category, [urls]) -> OPML text."""
    out = ['<?xml version="1.0"?><opml version="2.0"><head/><body>']
    for category, urls in groups:
        out.append(f'<outline title="{category}" text="{category}">')
        for url in urls:
            out.append(f'<outline type="rss" title="t" text="t" xmlUrl="{url}"/>')
        out.append("</outline>")
    out.append("</body></opml>")
    return "".join(out)


def urls_of(path):
    return [o.get("xmlUrl") for o in ET.parse(path).getroot().iter("outline") if o.get("xmlUrl")]


def shape(outline):
    return (dict(outline.attrib), [shape(c) for c in outline.findall("outline")])


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class MergeCliTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.base = Path(self._tmp.name)
        self.src = self.base / "source" / "v"
        self.src.mkdir(parents=True)
        (self.base / "data").mkdir()

    def write(self, name, *groups):
        (self.src / name).write_text(opml(*groups), encoding="utf-8")

    def run_merge(self, *extra, base=None, vertical="v"):
        env = {k: v for k, v in os.environ.items() if not k.startswith("K5_") and k != "VERTICAL"}
        cmd = [sys.executable, str(SCRIPT), "--base-dir", str(base or self.base)]
        if vertical:
            cmd += ["--vertical", vertical]
        return subprocess.run(cmd + list(extra), capture_output=True, text=True, env=env)

    @property
    def out(self):
        return self.src / "feeds.xml"

    def test_blog_xml_only_is_included(self):
        self.write("news.xml", ("News", ["http://n/1"]))
        self.write("blog.xml", ("Blogs", ["http://b/1", "http://b/2"]))
        r = self.run_merge()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(urls_of(self.out), ["http://n/1", "http://b/1", "http://b/2"])
        self.assertNotIn("blogs.xml", r.stderr)
        self.assertIn("podcasts.xml", r.stderr)  # other absent sections still warn

    def test_blogs_xml_only_is_included(self):
        self.write("blogs.xml", ("Blogs", ["http://b/1"]))
        r = self.run_merge()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(urls_of(self.out), ["http://b/1"])

    def test_both_present_blogs_wins_with_info_and_no_duplicates(self):
        self.write("blogs.xml", ("Blogs", ["http://plural/1"]))
        self.write("blog.xml", ("Blogs", ["http://singular/1"]))
        r = self.run_merge()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(urls_of(self.out), ["http://plural/1"])
        self.assertIn("Using blogs.xml; ignoring blog.xml", r.stderr)

    def test_alias_sections_requested_together_not_duplicated(self):
        self.write("blog.xml", ("Blogs", ["http://b/1"]))
        r = self.run_merge("--sections", "blog", "blogs")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(urls_of(self.out), ["http://b/1"])

    def test_explicit_sections_order_is_kept(self):
        self.write("news.xml", ("News", ["http://n/1"]))
        self.write("blog.xml", ("Blogs", ["http://b/1"]))
        self.write("videos.xml", ("Videos", ["http://v/1"]))
        r = self.run_merge("--sections", "videos", "blog", "news")
        self.assertEqual(urls_of(self.out), ["http://v/1", "http://b/1", "http://n/1"])

    def test_explicit_sections_exclude_unlisted(self):
        self.write("news.xml", ("News", ["http://n/1"]))
        self.write("blog.xml", ("Blogs", ["http://b/1"]))
        self.run_merge("--sections", "news")
        self.assertEqual(urls_of(self.out), ["http://n/1"])

    def test_missing_optional_section_warns_and_continues(self):
        self.write("news.xml", ("News", ["http://n/1"]))
        r = self.run_merge()
        self.assertEqual(r.returncode, 0)
        self.assertIn("Section missing", r.stderr)
        self.assertIn("blogs.xml", r.stderr)
        self.assertEqual(urls_of(self.out), ["http://n/1"])

    def test_all_sections_missing_exits_1_and_writes_nothing(self):
        r = self.run_merge()
        self.assertEqual(r.returncode, 1)
        self.assertIn("No feed sections found", r.stderr)
        self.assertFalse(self.out.exists())

    def test_malformed_xml_fails(self):
        (self.src / "blog.xml").write_text("<opml><body>", encoding="utf-8")
        r = self.run_merge()
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse(self.out.exists())

    def test_missing_body_fails(self):
        (self.src / "blog.xml").write_text('<opml version="2.0"><head/></opml>', encoding="utf-8")
        r = self.run_merge()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("missing a <body>", r.stderr)

    def test_unknown_slug_resolves_to_slug_xml(self):
        self.write("custom.xml", ("Custom", ["http://c/1"]))
        r = self.run_merge("--sections", "custom")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(urls_of(self.out), ["http://c/1"])
        r = self.run_merge("--sections", "nope")
        self.assertEqual(r.returncode, 1)
        self.assertIn("nope.xml", r.stderr)

    def test_opml_path_override(self):
        self.write("blog.xml", ("Blogs", ["http://b/1"]))
        target = self.base / "elsewhere.xml"
        r = self.run_merge("--opml-path", str(target))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(urls_of(target), ["http://b/1"])
        self.assertFalse(self.out.exists())

    def test_vertical_selects_its_own_source_dir(self):
        other = self.base / "source" / "w"
        other.mkdir()
        (other / "blog.xml").write_text(opml(("B", ["http://w/1"])), encoding="utf-8")
        self.write("blog.xml", ("B", ["http://v/1"]))
        self.run_merge(vertical="w")
        self.assertEqual(urls_of(other / "feeds.xml"), ["http://w/1"])
        self.assertFalse(self.out.exists())


class TrackedSourcesTest(unittest.TestCase):
    """Run the real merge against copies of the committed section files."""

    def check_vertical(self, vertical):
        real = CORE / "source" / vertical
        blog_name = "blog.xml" if (real / "blog.xml").exists() else "blogs.xml"
        originals = {p.name: sha(p) for p in real.glob("*.xml")}
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            dest = base / "source" / vertical
            dest.mkdir(parents=True)
            for name in ("news.xml", "blog.xml", "blogs.xml", "podcasts.xml", "videos.xml"):
                if (real / name).exists():
                    shutil.copy2(real / name, dest / name)
            env = {k: v for k, v in os.environ.items() if not k.startswith("K5_") and k != "VERTICAL"}
            r = subprocess.run(
                [sys.executable, str(SCRIPT), "--base-dir", str(base), "--vertical", vertical],
                capture_output=True, text=True, env=env,
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertNotIn("Section missing: " + str(dest / "blogs.xml"), r.stderr)
            merged = ET.parse(dest / "feeds.xml").getroot().find("body")
            merged_shapes = [shape(o) for o in merged.findall("outline")]
            blog_body = ET.parse(real / blog_name).getroot().find("body")
            blog_outlines = blog_body.findall("outline")
            self.assertTrue(blog_outlines)
            for o in blog_outlines:
                # exact taxonomy/source attributes survive, children in order
                self.assertIn(shape(o), merged_shapes)
            blog_urls = {u for o in blog_outlines for u in (x.get("xmlUrl") for x in o.iter("outline")) if u}
            self.assertTrue(blog_urls <= set(urls_of(dest / "feeds.xml")))
        self.assertEqual(originals, {p.name: sha(p) for p in real.glob("*.xml")})

    def test_k5(self):
        self.check_vertical("k5")

    def test_4u(self):
        self.check_vertical("4u")


class ResolverTest(unittest.TestCase):
    def test_aliases(self):
        self.assertEqual(canonical_section("blog"), "blogs")
        self.assertEqual(canonical_section("blogs"), "blogs")
        self.assertEqual(canonical_section("news"), "news")
        self.assertEqual(section_candidates("blog"), ["blogs.xml", "blog.xml"])
        self.assertEqual(section_candidates("podcasts"), ["podcasts.xml"])
        self.assertEqual(section_candidates("zzz"), ["zzz.xml"])

    def test_resolve_none_existing_returns_first_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            chosen, ignored = resolve_section_file(Path(tmp), "blog")
            self.assertEqual(chosen.name, "blogs.xml")
            self.assertEqual(ignored, [])


if __name__ == "__main__":
    unittest.main()
