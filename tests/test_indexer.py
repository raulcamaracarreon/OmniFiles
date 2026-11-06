"""Pruebas con archivos temporales; jamás indexan unidades del equipo."""
from pathlib import Path
import tempfile
import threading
import unittest

from omnifiles.indexer import (
    IndexCancelled, database_path, index_folder, indexed_roots, search_index,
)


class IndexerTests(unittest.TestCase):
    def setUp(self):
        self.sandbox = tempfile.TemporaryDirectory()
        self.addCleanup(self.sandbox.cleanup)
        self.base = Path(self.sandbox.name)
        self.db = self.base / "config" / "index.sqlite3"
        self.one = self.base / "fuenteA"
        self.two = self.base / "fuenteB"
        self.one.mkdir()
        self.two.mkdir()

    def test_multiple_roots_and_persistent_search(self):
        (self.one / "Informe UNRC.txt").write_text("hola", encoding="utf-8")
        (self.two / "informe resumen.pdf").write_bytes(b"PDF")
        first = index_folder(self.db, str(self.one))
        second = index_folder(self.db, str(self.two))
        self.assertEqual((first.count, second.count), (1, 1))
        self.assertEqual(len(search_index(self.db, "INFORME")), 2)
        self.assertEqual(len(indexed_roots(self.db)), 2)
        # Cada consulta abre una conexión nueva: índice persistente entre ejecuciones.
        self.assertTrue(search_index(self.db, "resumen")[0].endswith(".pdf"))

    def test_reindex_replaces_stale_entries(self):
        old = self.one / "anterior.txt"
        old.write_text("v1", encoding="utf-8")
        index_folder(self.db, str(self.one))
        old.unlink()
        (self.one / "nuevo.txt").write_text("v2", encoding="utf-8")
        # La indexación no es instantánea ni un watcher: todavía aparece el nombre anterior.
        self.assertEqual(len(search_index(self.db, "anterior")), 1)
        index_folder(self.db, str(self.one))
        self.assertEqual(search_index(self.db, "anterior"), [])
        self.assertEqual(len(search_index(self.db, "nuevo")), 1)

    def test_unicode_casefold_and_literal_special_characters(self):
        for name in ("Café.txt", "straße %_ final.txt", "otro.txt"):
            (self.one / name).write_text("x", encoding="utf-8")
        index_folder(self.db, str(self.one))
        self.assertEqual(len(search_index(self.db, "CAFÉ")), 1)
        self.assertEqual(len(search_index(self.db, "STRASSE")), 1)
        self.assertEqual(len(search_index(self.db, "%_")), 1)

    def test_cancel_rolls_back_without_overwriting_existing_index(self):
        (self.one / "estable.txt").write_text("v1", encoding="utf-8")
        index_folder(self.db, str(self.one))
        for i in range(290):
            (self.one / f"temporal{i:04}.txt").write_text("x", encoding="utf-8")
        cancel = threading.Event()

        def stop_after_250(_count):
            cancel.set()

        with self.assertRaises(IndexCancelled):
            index_folder(self.db, str(self.one), cancel=cancel, progress=stop_after_250)
        self.assertEqual(len(search_index(self.db, "estable")), 1)
        self.assertEqual(search_index(self.db, "temporal"), [])
        self.assertEqual(indexed_roots(self.db)[0]["count"], 1)

    def test_capacity_limit_rolls_back(self):
        (self.one / "estable.txt").write_text("x", encoding="utf-8")
        index_folder(self.db, str(self.one))
        (self.one / "nuevo.txt").write_text("x", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "límite"):
            index_folder(self.db, str(self.one), max_entries=1)
        self.assertEqual(indexed_roots(self.db)[0]["count"], 1)
        self.assertEqual(search_index(self.db, "nuevo"), [])

    def test_unreadable_or_missing_root_keeps_index(self):
        (self.one / "informe.txt").write_text("x", encoding="utf-8")
        index_folder(self.db, str(self.one))
        with self.assertRaises(ValueError):
            index_folder(self.db, str(self.base / "nunca-existió"))
        self.assertEqual(len(search_index(self.db, "informe")), 1)

    def test_nested_folders_and_limits(self):
        deep = self.one / "SubCarpeta"
        deep.mkdir()
        (deep / "nota.txt").write_text("x", encoding="utf-8")
        index_folder(self.db, str(self.one))
        self.assertEqual(len(search_index(self.db, "subcarpeta")), 1)
        self.assertEqual(len(search_index(self.db, ".txt", limit=1)), 1)
        self.assertEqual(search_index(self.db, "", limit=30), [])

    def test_no_follow_symlinks(self):
        outer = self.base / "privado"
        outer.mkdir()
        (outer / "privado.txt").write_text("x", encoding="utf-8")
        link = self.one / "enlace"
        try:
            link.symlink_to(outer, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Permisos para crear symlinks no disponibles")
        summary = index_folder(self.db, str(self.one))
        self.assertGreaterEqual(summary.skipped, 1)
        self.assertEqual(search_index(self.db, "privado.txt"), [])


if __name__ == "__main__":
    unittest.main()
