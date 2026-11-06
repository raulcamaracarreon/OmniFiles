"""Adaptador independiente de Everything ES y búsqueda local acotada."""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess
import threading
import time

from .core import clean_results


@dataclass(frozen=True)
class SearchOutput:
    paths: list[str]
    engine: str
    note: str


def find_es(configured: str = "") -> str | None:
    """No incluye ni distribuye es.exe: lo detecta en el sistema."""
    if configured and Path(configured).is_file():
        return str(Path(configured))
    return shutil.which("es.exe") or shutil.which("es")


def search_everything(executable: str, query: str, limit: int = 400) -> SearchOutput:
    """Consulta ES con shell=False (no interpreta comandos de consola)."""
    if not query.strip():
        return SearchOutput([], "Everything", "Escribe un término para buscar.")
    command = [
        executable, "-n", str(limit), "-timeout", "3000", "-txt", "-full-path-and-name",
        query,
    ]
    try:
        proc = subprocess.run(
            command, capture_output=True, text=True, encoding="utf-8-sig",
            errors="replace", timeout=10, shell=False, check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired as ex:
        raise RuntimeError("Everything no respondió dentro del límite de 10 segundos.") from ex
    except OSError as ex:
        raise RuntimeError(f"No se pudo iniciar es.exe: {ex}") from ex

    if proc.returncode != 0:
        meaning = {
            7: "Falló la consulta IPC a Everything.",
            8: "Everything no está ejecutándose o su IPC no está disponible (versión Lite no sirve).",
            9: "No se encontraron resultados.",
        }.get(proc.returncode, f"es.exe devolvió el código {proc.returncode}.")
        if proc.returncode == 9:
            return SearchOutput([], "Everything", meaning)
        raise RuntimeError(meaning + (f" Detalle: {proc.stderr.strip()[:400]}" if proc.stderr else ""))

    results = clean_results(proc.stdout.splitlines(), limit)
    return SearchOutput(results, "Everything", f"{len(results)} resultados; máximo {limit}.")


def search_local(
    root: str,
    query: str,
    limit: int = 400,
    max_seconds: float = 8.0,
    max_directories: int = 10000,
    cancel: threading.Event | None = None,
) -> SearchOutput:
    """Plan B: busca por nombre en carpeta elegida, sin indexación ni contenido."""
    if not Path(root).is_dir():
        raise ValueError("La carpeta de búsqueda no existe.")
    if not query.strip():
        return SearchOutput([], "Local", "Escribe un término para buscar.")
    needle = query.casefold().strip()
    deadline = time.monotonic() + max_seconds
    found: list[str] = []
    seen_dirs = 0
    reason = "Búsqueda completada."

    def skip_error(_exc: OSError) -> None:
        # Directorios inaccesibles no cancelan el escaneo completo.
        return None

    for current, directories, files in os.walk(root, topdown=True, followlinks=False, onerror=skip_error):
        if cancel and cancel.is_set():
            reason = "Búsqueda cancelada; resultados parciales."
            break
        if time.monotonic() > deadline:
            reason = "Límite de tiempo alcanzado; resultados parciales."
            break
        seen_dirs += 1
        if seen_dirs > max_directories:
            reason = "Límite de directorios alcanzado; resultados parciales."
            break
        directories[:] = [d for d in directories if not os.path.islink(os.path.join(current, d))]
        for name in directories + files:
            if needle in name.casefold():
                found.append(os.path.join(current, name))
                if len(found) >= limit:
                    reason = "Límite de resultados alcanzado."
                    break
        if len(found) >= limit:
            break
    return SearchOutput(found, "Local", f"{len(found)} resultados. {reason}")
