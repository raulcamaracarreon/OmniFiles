"""Índice local SQLite de OmniFiles: solo lee archivos, nunca los modifica.

La reconstrucción de una carpeta es transaccional: si se cancela o falla,
se conserva íntegramente el índice anterior de esa carpeta.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3
import threading
from typing import Callable


class IndexCancelled(Exception):
    """El usuario canceló el escaneo; se revierte la transacción."""


@dataclass(frozen=True)
class IndexSummary:
    root: str
    count: int
    skipped: int


def database_path() -> Path:
    """Ruta privada del índice; no se crea dentro del repositorio."""
    base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / ".config")))
    return base / "OmniFiles" / "index.sqlite3"


def _key(path: str) -> str:
    return os.path.normcase(os.path.normpath(path)).casefold()


def _connect(db_path: str | Path) -> sqlite3.Connection:
    target = Path(db_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(target), timeout=15)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA busy_timeout=15000")
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS roots (
            id INTEGER PRIMARY KEY,
            path TEXT NOT NULL,
            path_key TEXT NOT NULL UNIQUE,
            last_indexed TEXT,
            entry_count INTEGER NOT NULL DEFAULT 0,
            skipped_count INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS entries (
            root_id INTEGER NOT NULL REFERENCES roots(id) ON DELETE CASCADE,
            path TEXT NOT NULL,
            path_key TEXT NOT NULL,
            name TEXT NOT NULL,
            name_key TEXT NOT NULL,
            extension TEXT NOT NULL,
            size INTEGER NOT NULL,
            modified REAL,
            is_dir INTEGER NOT NULL,
            UNIQUE(root_id, path_key)
        );
        CREATE INDEX IF NOT EXISTS entries_name_key_idx ON entries(name_key);
        CREATE INDEX IF NOT EXISTS entries_root_idx ON entries(root_id);
    """)
    db.commit()
    return db


def _is_link_or_junction(path: str) -> bool:
    """No descendemos por enlaces ni puntos de unión NTFS."""
    return os.path.islink(path) or (hasattr(os.path, "isjunction") and os.path.isjunction(path))


def index_folder(
    db_path: str | Path,
    folder: str,
    *,
    cancel: threading.Event | None = None,
    progress: Callable[[int], None] | None = None,
    max_entries: int = 1_500_000,
) -> IndexSummary:
    """Indexa de forma recursiva y atómica una carpeta elegida explícitamente.

    Solo enumera nombres y metadatos. No abre ni analiza contenido de archivos.
    No sigue symlinks ni junctions. Si una subcarpeta es inaccesible se
    contabiliza, sin presentar el resultado como índice perfecto.
    """
    original = str(Path(folder).expanduser())
    if _is_link_or_junction(original):
        raise ValueError("Por seguridad, no se indexan carpetas que sean enlaces o junctions.")
    root = str(Path(original).resolve())
    if not os.path.isdir(root):
        raise ValueError(f"La carpeta no existe: {root}")
    if _is_link_or_junction(root):
        raise ValueError("Por seguridad, no se indexan carpetas que sean enlaces o junctions.")
    if max_entries < 1:
        raise ValueError("max_entries debe ser positivo.")

    db = _connect(db_path)
    total = 0
    skipped = 0
    try:
        db.execute("BEGIN IMMEDIATE")
        root_key = _key(root)
        db.execute(
            "INSERT INTO roots(path, path_key) VALUES (?, ?) "
            "ON CONFLICT(path_key) DO UPDATE SET path=excluded.path",
            (root, root_key),
        )
        root_id = db.execute("SELECT id FROM roots WHERE path_key=?", (root_key,)).fetchone()[0]
        db.execute("DELETE FROM entries WHERE root_id=?", (root_id,))
        stack = [root]
        while stack:
            if cancel is not None and cancel.is_set():
                raise IndexCancelled("Indexación cancelada: se conservó el índice anterior.")
            current = stack.pop()
            try:
                with os.scandir(current) as listing:
                    for item in listing:
                        if cancel is not None and cancel.is_set():
                            raise IndexCancelled("Indexación cancelada: se conservó el índice anterior.")
                        try:
                            if item.is_symlink() or _is_link_or_junction(item.path):
                                skipped += 1
                                continue
                            is_dir = item.is_dir(follow_symlinks=False)
                            metadata = item.stat(follow_symlinks=False)
                        except OSError:
                            skipped += 1
                            continue
                        if total >= max_entries:
                            raise RuntimeError(
                                f"Se alcanzó el límite de {max_entries:,} elementos. "
                                "No se reemplazó el índice anterior."
                            )
                        name = item.name
                        db.execute(
                            "INSERT INTO entries(root_id,path,path_key,name,name_key,extension,size,modified,is_dir) "
                            "VALUES (?,?,?,?,?,?,?,?,?)",
                            (
                                root_id, item.path, _key(item.path), name, name.casefold(),
                                Path(name).suffix.casefold() if not is_dir else "",
                                0 if is_dir else metadata.st_size, metadata.st_mtime, int(is_dir),
                            ),
                        )
                        total += 1
                        if is_dir:
                            stack.append(item.path)
                        if progress is not None and total % 250 == 0:
                            progress(total)
            except IndexCancelled:
                raise
            except OSError as ex:
                if current == root:
                    raise RuntimeError(f"No se puede leer la carpeta seleccionada: {ex}") from ex
                skipped += 1
        db.execute(
            "UPDATE roots SET last_indexed=?,entry_count=?,skipped_count=? WHERE id=?",
            (datetime.now(timezone.utc).isoformat(), total, skipped, root_id),
        )
        db.commit()
        if progress is not None:
            progress(total)
        return IndexSummary(root, total, skipped)
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


def indexed_roots(db_path: str | Path) -> list[dict]:
    """Devuelve índice y fechas; no comprueba automáticamente vigencia."""
    db = _connect(db_path)
    try:
        rows = db.execute(
            "SELECT path, last_indexed, entry_count, skipped_count FROM roots ORDER BY path_key"
        ).fetchall()
        return [
            {"path": r[0], "last_indexed": r[1], "count": r[2], "skipped": r[3]}
            for r in rows
        ]
    finally:
        db.close()


def search_index(db_path: str | Path, query: str, *, limit: int = 400) -> list[str]:
    """Busca texto literal (incluidos %, _ y tildes) en nombres indexados."""
    needle = query.strip().casefold()
    if not needle or limit <= 0:
        return []
    db = _connect(db_path)
    try:
        # instr, en lugar de LIKE, evita comodines implícitos y respeta casefold Unicode.
        rows = db.execute(
            "SELECT path FROM entries WHERE instr(name_key, ?) > 0 ORDER BY name_key, path_key LIMIT ?",
            (needle, min(limit * 3, 5000)),
        ).fetchall()
        seen: set[str] = set()
        result: list[str] = []
        for (path,) in rows:
            key = _key(path)
            if key in seen:
                continue
            seen.add(key)
            result.append(path)
            if len(result) >= limit:
                break
        return result
    finally:
        db.close()
