from pathlib import Path
import tempfile
import unittest

from omnifiles.core import clean_results, human_size, validate_navigation
from omnifiles.search import search_local, find_es


class TestCore(unittest.TestCase):
    def test_human_size(self):
        self.assertEqual(human_size(0), "0 B")
        self.assertEqual(human_size(1024), "1.0 KiB")
        self.assertEqual(human_size(1024 ** 3), "1.0 GiB")
        self.assertEqual(human_size(None), "—")

    def test_clean_results(self):
        self.assertEqual(clean_results(["A.txt", "", "A.txt", "B.txt"], 10), ["A.txt", "B.txt"])
        self.assertEqual(clean_results(["a", "b", "c"], 2), ["a", "b"])

    def test_validate_navigation(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(validate_navigation(tmp), str(Path(tmp).resolve()))
            with self.assertRaises(ValueError):
                validate_navigation(str(Path(tmp) / "inexistente"))

    def test_local_search_nested_and_limits(self):
        with tempfile.TemporaryDirectory() as tmp:
            sub = Path(tmp, "sub")
            sub.mkdir()
            (sub / "Informe UNRC.docx").write_text("abc", encoding="utf-8")
            (sub / "otro.txt").write_text("abc", encoding="utf-8")
            out = search_local(tmp, "informe")
            self.assertEqual(out.engine, "Local")
            self.assertEqual(len(out.paths), 1)
            self.assertIn("Informe UNRC.docx", out.paths[0])
            out2 = search_local(tmp, "txt", limit=1)
            self.assertEqual(len(out2.paths), 1)

    def test_find_es_configured(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp, "es.exe")
            exe.write_bytes(b"test")
            self.assertEqual(find_es(str(exe)), str(exe))


if __name__ == "__main__":
    unittest.main()
