import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import mdlinkcheck


class FindLinksTest(unittest.TestCase):
    def test_finds_inline_links(self):
        text = "Смотрите [доки](docs/a.md) и [сайт](https://example.com)."
        self.assertEqual(
            mdlinkcheck.find_links(text),
            [(1, "docs/a.md"), (1, "https://example.com")],
        )

    def test_skips_fenced_code(self):
        text = "```\n[x](broken.md)\n```\n[y](ok.md)"
        self.assertEqual(mdlinkcheck.find_links(text), [(4, "ok.md")])

    def test_skips_inline_code(self):
        text = "Формат `[текст](адрес)` и [рабочая](ok.md)."
        self.assertEqual(mdlinkcheck.find_links(text), [(1, "ok.md")])


class MainTest(unittest.TestCase):
    def test_reports_broken_local_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc = Path(tmp) / "index.md"
            doc.write_text("[нет](missing.md)", encoding="utf-8")
            self.assertEqual(mdlinkcheck.main([str(doc), "--offline"]), 1)

    def test_ok_when_all_links_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "b.md").write_text("текст", encoding="utf-8")
            doc = Path(tmp) / "index.md"
            doc.write_text("[b](b.md#раздел)", encoding="utf-8")
            self.assertEqual(mdlinkcheck.main([str(doc), "--offline"]), 0)

    def test_no_files_returns_2(self):
        self.assertEqual(mdlinkcheck.main(["/nonexistent/path"]), 2)


if __name__ == "__main__":
    unittest.main()
