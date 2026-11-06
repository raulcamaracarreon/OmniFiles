"""Lógica independiente de la interfaz: rutas, unidades y formato."""
from __future__ import annotations

from pathlib import Path
import os


def human_size(number: int | float | None) -> str:
    """Convierte bytes a unidades binarias legibles."""
    if number is None or number < 0:
        return "—"
    value = float(number)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB", "PiB"):
        if value < 1024 or unit == "PiB":
            return f"{int(value)} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return "—"


def is_directory(path: str) -> bool:
    return bool(path) and os.path.isdir(path)


def validate_navigation(path: str) -> str:
    """Valida una carpeta existente; no crea ni modifica archivos."""
    p = Path(path).expanduser()
    if not p.is_dir():
        raise ValueError(f"No existe o no es una carpeta: {p}")
    return str(p.resolve())


def clean_results(lines: list[str], limit: int) -> list[str]:
    """Filtra líneas vacías y duplicados sin alterar la ruta original."""
    if limit < 1:
        return []
    seen: set[str] = set()
    result: list[str] = []
    for raw in lines:
        path = raw.strip("\r\n\ufeff")
        if not path:
            continue
        key = os.path.normcase(os.path.normpath(path))
        if key in seen:
            continue
        seen.add(key)
        result.append(path)
        if len(result) >= limit:
            break
    return result
