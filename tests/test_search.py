from unittest.mock import patch
import subprocess
import unittest

from omnifiles.search import search_everything


class TestEverythingAdapter(unittest.TestCase):
    @patch("omnifiles.search.subprocess.run")
    def test_arguments_and_results(self, runner):
        runner.return_value = subprocess.CompletedProcess([], 0, "C:\\uno.txt\nD:\\dos.txt\n", "")
        out = search_everything("C:\\Tools\\es.exe", "*.txt", limit=2)
        self.assertEqual(len(out.paths), 2)
        self.assertEqual(out.engine, "Everything")
        args, kwargs = runner.call_args
        self.assertIn("-full-path-and-name", args[0])
        self.assertEqual(args[0][-1], "*.txt")
        self.assertFalse(kwargs["shell"])

    @patch("omnifiles.search.subprocess.run")
    def test_not_running(self, runner):
        runner.return_value = subprocess.CompletedProcess([], 8, "", "")
        with self.assertRaisesRegex(RuntimeError, "no está ejecutándose"):
            search_everything("es.exe", "reporte")

    @patch("omnifiles.search.subprocess.run")
    def test_timeout(self, runner):
        runner.side_effect = subprocess.TimeoutExpired(["es"], 10)
        with self.assertRaisesRegex(RuntimeError, "10 segundos"):
            search_everything("es.exe", "reporte")


if __name__ == "__main__":
    unittest.main()
