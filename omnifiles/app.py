"""Interfaz de escritorio del MVP. Intencionalmente no modifica archivos."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import threading

from PySide6.QtCore import QDir, QObject, Qt, QThread, QUrl, Signal, QStorageInfo
from PySide6.QtGui import QAction, QDesktopServices, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QFileSystemModel, QFrame, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMainWindow, QMenu, QMessageBox, QProgressBar, QPushButton,
    QSplitter, QStackedWidget, QTableView, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget, QAbstractItemView,
)

from .core import human_size, validate_navigation
from .search import SearchOutput
from .indexer import database_path, indexed_roots, index_folder, search_index, IndexCancelled


def config_path() -> Path:
    home = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / ".config")))
    return home / "OmniFiles" / "settings.json"


class SearchWorker(QObject):
    done = Signal(object)
    error = Signal(str)
    finished = Signal()

    def __init__(self, query: str, db_path: Path):
        super().__init__()
        self.query = query
        self.db_path = db_path

    def run(self) -> None:
        try:
            paths = search_index(self.db_path, self.query)
            self.done.emit(SearchOutput(paths, "SQLite", f"{len(paths)} resultados del índice local; máximo 400. Los cambios posteriores a la indexación pueden no aparecer."))
        except Exception as ex:
            self.error.emit(str(ex))
        finally:
            self.finished.emit()


class IndexWorker(QObject):
    done = Signal(object)
    progress = Signal(int)
    error = Signal(str)
    finished = Signal()

    def __init__(self, folder: str, db_path: Path):
        super().__init__()
        self.folder = folder
        self.db_path = db_path
        self.cancel = threading.Event()

    def run(self) -> None:
        try:
            summary = index_folder(self.db_path, self.folder, cancel=self.cancel, progress=self.progress.emit)
            self.done.emit(summary)
        except IndexCancelled as ex:
            self.error.emit(str(ex))
        except Exception as ex:
            self.error.emit(f"Error de indexación: {ex}")
        finally:
            self.finished.emit()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OmniFiles — explorador de archivos (prototipo 0.2)")
        self.resize(1180, 720)
        self.setMinimumSize(850, 480)
        self.history: list[str] = []
        self.position = -1
        self.active_search = False
        self.search_thread: QThread | None = None
        self.search_worker: SearchWorker | None = None
        self.active_index = False
        self.index_thread: QThread | None = None
        self.index_worker: IndexWorker | None = None
        self.db_path = database_path()

        self.settings = self._load_settings()
        self.bookmarks: list[str] = [p for p in self.settings.get("favorites", []) if isinstance(p, str)]

        main = QWidget(self)
        self.setCentralWidget(main)
        vbox = QVBoxLayout(main)
        vbox.setContentsMargins(12, 12, 12, 9)
        vbox.setSpacing(9)

        header = QHBoxLayout()
        self.btn_back = QPushButton("◀")
        self.btn_back.setToolTip("Atrás (Alt+Izquierda)")
        self.btn_next = QPushButton("▶")
        self.btn_next.setToolTip("Adelante")
        self.btn_up = QPushButton("↑")
        self.btn_up.setToolTip("Carpeta superior")
        self.btn_home = QPushButton("Inicio")
        self.btn_reload = QPushButton("Actualizar")
        self.btn_fav = QPushButton("☆ Favorito")
        for btn in (self.btn_back, self.btn_next, self.btn_up, self.btn_home, self.btn_reload, self.btn_fav):
            header.addWidget(btn)
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Ruta de carpeta...")
        header.addWidget(self.path_edit, stretch=1)
        vbox.addLayout(header)

        disks = QFrame()
        disks.setObjectName("diskBox")
        self.disk_layout = QHBoxLayout(disks)
        self.disk_layout.setContentsMargins(8, 8, 8, 8)
        self.disk_layout.setSpacing(8)
        vbox.addWidget(disks)

        search_bar = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Buscar por nombre en todas las carpetas indexadas (SQLite)...")
        self.btn_search = QPushButton("Buscar")
        self.btn_explorer = QPushButton("Ver carpeta")
        self.btn_index = QPushButton("Indexar carpeta")
        self.btn_index_cancel = QPushButton("Cancelar índice")
        self.btn_index_cancel.setEnabled(False)
        search_bar.addWidget(self.search_edit, stretch=1)
        for btn in (self.btn_search, self.btn_explorer, self.btn_index, self.btn_index_cancel):
            search_bar.addWidget(btn)
        vbox.addLayout(search_bar)

        split = QSplitter(Qt.Orientation.Horizontal)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 4, 0)
        left_layout.addWidget(QLabel("UNIDADES"))
        self.drives_list = QListWidget()
        self.drives_list.setMaximumHeight(180)
        left_layout.addWidget(self.drives_list)
        left_layout.addWidget(QLabel("FAVORITOS"))
        self.favs_list = QListWidget()
        left_layout.addWidget(self.favs_list)
        split.addWidget(left)

        self.pages = QStackedWidget()
        self.fs_model = QFileSystemModel(self)
        self.fs_model.setReadOnly(True)
        self.fs_model.setFilter(QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot)
        self.fs_model.setRootPath(str(Path.home()))
        self.explorer = QTableView()
        self.explorer.setModel(self.fs_model)
        self.explorer.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.explorer.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.explorer.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.explorer.setAlternatingRowColors(True)
        self.explorer.setSortingEnabled(True)
        self.explorer.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.explorer.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.explorer.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.explorer.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.pages.addWidget(self.explorer)

        self.results = QTableWidget(0, 2)
        self.results.setHorizontalHeaderLabels(["Archivo o carpeta", "Ruta completa"])
        self.results.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.results.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.results.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.results.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.results.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.results.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.pages.addWidget(self.results)
        split.addWidget(self.pages)
        split.setSizes([210, 890])
        vbox.addWidget(split, stretch=1)

        self.engine_label = QLabel()
        vbox.addWidget(self.engine_label)
        self.statusBar().showMessage("Listo. OmniFiles 0.2 no modifica los archivos originales.")

        self.btn_back.clicked.connect(self.go_back)
        self.btn_next.clicked.connect(self.go_next)
        self.btn_up.clicked.connect(self.go_up)
        self.btn_home.clicked.connect(lambda: self.navigate(str(Path.home())))
        self.btn_reload.clicked.connect(self.refresh)
        self.btn_fav.clicked.connect(self.toggle_favorite)
        self.path_edit.returnPressed.connect(self.navigate_address)
        self.btn_search.clicked.connect(self.start_search)
        self.btn_explorer.clicked.connect(lambda: self.pages.setCurrentIndex(0))
        self.btn_index.clicked.connect(self.start_indexing)
        self.btn_index_cancel.clicked.connect(self.cancel_indexing)
        self.search_edit.returnPressed.connect(self.start_search)
        self.drives_list.itemActivated.connect(lambda item: self.navigate(item.data(Qt.ItemDataRole.UserRole)))
        self.drives_list.itemClicked.connect(lambda item: self.navigate(item.data(Qt.ItemDataRole.UserRole)))
        self.favs_list.itemActivated.connect(lambda item: self.navigate(item.data(Qt.ItemDataRole.UserRole)))
        self.favs_list.itemClicked.connect(lambda item: self.navigate(item.data(Qt.ItemDataRole.UserRole)))
        self.explorer.doubleClicked.connect(self.open_file_index)
        self.results.cellDoubleClicked.connect(self.open_result)
        self.explorer.customContextMenuRequested.connect(self.context_explorer)
        self.results.customContextMenuRequested.connect(self.context_results)

        action_back = QAction("Atrás", self)
        action_back.setShortcut(QKeySequence("Alt+Left"))
        action_back.triggered.connect(self.go_back)
        self.addAction(action_back)
        action_search = QAction("Buscar", self)
        action_search.setShortcut(QKeySequence("Ctrl+F"))
        action_search.triggered.connect(self.search_edit.setFocus)
        self.addAction(action_search)
        self._refresh_volumes()
        self._refresh_favorites()
        self._refresh_search_status()
        self.navigate(str(Path.home()))

    def _load_settings(self) -> dict:
        try:
            return json.loads(config_path().read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return {}

    def _save_settings(self) -> None:
        try:
            dest = config_path()
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp = dest.with_suffix(".tmp")
            tmp.write_text(json.dumps({"favorites": self.bookmarks, "es_path": self.settings.get("es_path", "")}, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(dest)
        except OSError as ex:
            self.statusBar().showMessage(f"No se pudo guardar configuración: {ex}", 7000)

    def _refresh_volumes(self) -> None:
        self.drives_list.clear()
        while self.disk_layout.count():
            item = self.disk_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        volumes = sorted(QStorageInfo.mountedVolumes(), key=lambda v: v.rootPath().lower())
        count = 0
        for vol in volumes:
            if not vol.isValid() or not vol.isReady() or vol.bytesTotal() <= 0:
                continue
            root = vol.rootPath()
            total = vol.bytesTotal()
            free = vol.bytesAvailable()
            if not root:
                continue
            title = root.rstrip("/\\") or root
            item = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, root)
            self.drives_list.addItem(item)
            tile = QFrame()
            tile.setObjectName("tile")
            t_layout = QVBoxLayout(tile)
            t_layout.setContentsMargins(10, 8, 10, 7)
            b = QPushButton(f"{title} · {human_size(free)} libres")
            b.setFlat(True)
            b.clicked.connect(lambda _=False, p=root: self.navigate(p))
            progress = QProgressBar()
            progress.setRange(0, 100)
            progress.setValue(round((total - free) * 100 / total))
            progress.setFormat(f"{human_size(total)} · %p% ocupado")
            if free / total < 0.10:
                progress.setStyleSheet("QProgressBar::chunk {background: #d84d50;}")
            t_layout.addWidget(b)
            t_layout.addWidget(progress)
            self.disk_layout.addWidget(tile, stretch=1)
            count += 1
        if not count:
            self.disk_layout.addWidget(QLabel("No se encontraron volúmenes disponibles."))

    def _refresh_favorites(self) -> None:
        self.favs_list.clear()
        for folder in self.bookmarks:
            if not Path(folder).is_dir():
                continue
            item = QListWidgetItem(folder)
            item.setData(Qt.ItemDataRole.UserRole, folder)
            self.favs_list.addItem(item)

    def _refresh_search_status(self) -> None:
        try:
            roots = indexed_roots(self.db_path)
        except Exception as ex:
            self.engine_label.setText(f"No se puede leer el índice SQLite: {ex}")
            return
        total = sum(item["count"] for item in roots)
        if roots:
            locations = ", ".join(item["path"] for item in roots[:3])
            if len(roots) > 3:
                locations += f" ... (+{len(roots) - 3})"
            self.engine_label.setText(
                f"Motor propio SQLite · {len(roots)} carpetas · {total:,} elementos · {locations}. "
                "Los cambios posteriores a la indexación requieren reindexar."
            )
        else:
            self.engine_label.setText(
                "Motor propio SQLite: aún no hay carpetas indexadas. "
                "Pulsa «Indexar carpeta»; no necesitas Everything."
            )

    def start_indexing(self) -> None:
        if self.active_index:
            return
        current = self.path_edit.text()
        start_folder = current if Path(current).is_dir() else str(Path.home())
        folder = QFileDialog.getExistingDirectory(self, "Elegir una carpeta para indexar", start_folder)
        if not folder:
            return
        answer = QMessageBox.question(
            self, "Confirmar indexación",
            f"¿Indexar nombres y metadatos dentro de esta carpeta y sus subcarpetas?\n\n{folder}\n\n"
            "Solo lectura. El primer recorrido puede tardar; puedes cancelarlo. "
            "Una nueva indexación de esta misma carpeta actualizará los resultados.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.active_index = True
        self.btn_index.setEnabled(False)
        self.btn_index_cancel.setEnabled(True)
        self.index_thread = QThread(self)
        self.index_worker = IndexWorker(folder, self.db_path)
        self.index_worker.moveToThread(self.index_thread)
        self.index_thread.started.connect(self.index_worker.run)
        self.index_worker.progress.connect(self.index_progress)
        self.index_worker.done.connect(self.index_done)
        self.index_worker.error.connect(self.index_error)
        self.index_worker.finished.connect(self.index_thread.quit)
        self.index_worker.finished.connect(self.index_worker.deleteLater)
        self.index_thread.finished.connect(self.index_thread.deleteLater)
        self.index_thread.finished.connect(self.index_cleanup)
        self.index_thread.start()
        self.statusBar().showMessage(f"Indexando en segundo plano: {folder}")

    def index_progress(self, count: int) -> None:
        self.statusBar().showMessage(f"Indexando en segundo plano: {count:,} elementos examinados...")

    def index_done(self, summary) -> None:
        self.statusBar().showMessage(
            f"Índice actualizado: {summary.count:,} elementos; {summary.skipped} omitidos. "
            "Los archivos originales no se modificaron."
        )
        self._refresh_search_status()

    def index_error(self, detail: str) -> None:
        self.statusBar().showMessage(detail, 12000)
        if not detail.startswith("Indexación cancelada"):
            QMessageBox.warning(self, "Indexación", detail)

    def index_cleanup(self) -> None:
        self.active_index = False
        self.index_thread = None
        self.index_worker = None
        self.btn_index.setEnabled(True)
        self.btn_index_cancel.setEnabled(False)
        self._refresh_search_status()

    def cancel_indexing(self) -> None:
        if self.index_worker:
            self.index_worker.cancel.set()
            self.btn_index_cancel.setEnabled(False)
            self.statusBar().showMessage("Cancelando indexación. Se conserva el índice anterior...")

    def navigate(self, path: str, record: bool = True) -> None:
        try:
            target = validate_navigation(path)
        except (OSError, ValueError) as ex:
            QMessageBox.warning(self, "Carpeta no disponible", str(ex))
            return
        if record:
            if self.position < 0 or self.history[self.position] != target:
                self.history = self.history[:self.position + 1]
                self.history.append(target)
                self.position = len(self.history) - 1
        self.path_edit.setText(target)
        self.explorer.setRootIndex(self.fs_model.index(target))
        self.pages.setCurrentIndex(0)
        self.btn_back.setEnabled(self.position > 0)
        self.btn_next.setEnabled(self.position < len(self.history) - 1)
        self.statusBar().showMessage(target)
        self.btn_fav.setText("★ Favorito" if target in self.bookmarks else "☆ Favorito")

    def navigate_address(self) -> None:
        self.navigate(self.path_edit.text())

    def go_back(self) -> None:
        if self.position > 0:
            self.position -= 1
            self.navigate(self.history[self.position], record=False)

    def go_next(self) -> None:
        if self.position < len(self.history) - 1:
            self.position += 1
            self.navigate(self.history[self.position], record=False)

    def go_up(self) -> None:
        path = Path(self.path_edit.text())
        if path.parent != path:
            self.navigate(str(path.parent))

    def refresh(self) -> None:
        self._refresh_volumes()
        self._refresh_search_status()
        self.navigate(self.path_edit.text(), record=False)

    def toggle_favorite(self) -> None:
        folder = self.path_edit.text()
        if folder in self.bookmarks:
            self.bookmarks.remove(folder)
        elif Path(folder).is_dir():
            self.bookmarks.append(folder)
        self._save_settings()
        self._refresh_favorites()
        self.btn_fav.setText("★ Favorito" if folder in self.bookmarks else "☆ Favorito")

    def open_path(self, path: str) -> None:
        if os.path.isdir(path):
            self.navigate(path)
        elif os.path.isfile(path):
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(path)):
                QMessageBox.warning(self, "No se pudo abrir", f"No hay aplicación asociada para:\n{path}")
        else:
            QMessageBox.information(self, "Ruta no disponible", f"El elemento ya no existe:\n{path}")

    def open_file_index(self, index) -> None:
        path = self.fs_model.filePath(index)
        if path:
            self.open_path(path)

    def selected_explorer_path(self) -> str:
        selected = self.explorer.selectionModel().selectedRows(0)
        return self.fs_model.filePath(selected[0]) if selected else ""

    def selected_result_path(self) -> str:
        row = self.results.currentRow()
        item = self.results.item(row, 1) if row >= 0 else None
        return item.text() if item else ""

    def context_explorer(self, pos) -> None:
        index = self.explorer.indexAt(pos)
        if index.isValid():
            self.show_context(self.fs_model.filePath(index), self.explorer.mapToGlobal(pos))

    def context_results(self, pos) -> None:
        row = self.results.rowAt(pos.y())
        if row >= 0:
            item = self.results.item(row, 1)
            if item:
                self.show_context(item.text(), self.results.mapToGlobal(pos))

    def show_context(self, path: str, global_pos) -> None:
        menu = QMenu(self)
        open_act = menu.addAction("Abrir")
        copy_act = menu.addAction("Copiar ruta al portapapeles")
        choice = menu.exec(global_pos)
        if choice == open_act:
            self.open_path(path)
        elif choice == copy_act:
            QApplication.clipboard().setText(path)
            self.statusBar().showMessage("Ruta copiada.", 3000)

    def start_search(self) -> None:
        if self.active_search:
            return
        query = self.search_edit.text().strip()
        if not query:
            self.search_edit.setFocus()
            return
        try:
            if not indexed_roots(self.db_path):
                QMessageBox.information(
                    self, "Sin índice",
                    "No hay carpetas indexadas. Pulsa «Indexar carpeta», elige una carpeta "
                    "y vuelve a realizar la búsqueda. No necesitas Everything.",
                )
                return
        except Exception as ex:
            QMessageBox.warning(self, "Índice no disponible", str(ex))
            return
        self.active_search = True
        self.btn_search.setEnabled(False)
        self.search_thread = QThread(self)
        self.search_worker = SearchWorker(query, self.db_path)
        self.search_worker.moveToThread(self.search_thread)
        self.search_thread.started.connect(self.search_worker.run)
        self.search_worker.done.connect(self.search_done)
        self.search_worker.error.connect(self.search_error)
        self.search_worker.finished.connect(self.search_thread.quit)
        self.search_worker.finished.connect(self.search_worker.deleteLater)
        self.search_thread.finished.connect(self.search_cleanup)
        self.search_thread.start()
        self.statusBar().showMessage("Buscando en el índice SQLite...")

    def search_done(self, output) -> None:
        self.results.setRowCount(len(output.paths))
        for row, p in enumerate(output.paths):
            self.results.setItem(row, 0, QTableWidgetItem(Path(p).name or p))
            self.results.setItem(row, 1, QTableWidgetItem(p))
        self.pages.setCurrentIndex(1)
        self.statusBar().showMessage(f"{output.engine}: {output.note}")

    def search_error(self, error: str) -> None:
        QMessageBox.warning(self, "Error de búsqueda", error)
        self.statusBar().showMessage("La búsqueda no pudo completarse.")

    def search_cleanup(self) -> None:
        self.active_search = False
        self.search_thread = None
        self.search_worker = None
        self.btn_search.setEnabled(True)

    def open_result(self, row: int, _column: int) -> None:
        item = self.results.item(row, 1)
        if item:
            self.open_path(item.text())

    def closeEvent(self, event) -> None:
        if self.active_index:
            self.cancel_indexing()
        if self.active_search or self.active_index:
            QMessageBox.information(
                self, "Trabajo en curso",
                "Se solicitó cancelar la indexación, si estaba activa. "
                "Cierra la ventana cuando terminen las tareas de fondo.",
            )
            event.ignore()
        else:
            event.accept()


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet("""
        QMainWindow, QWidget { background: #171b24; color: #eef0f5; font-size: 12px; }
        QLineEdit, QListWidget, QTableView, QTableWidget {
            background: #222937; color: #f0f3fa; border: 1px solid #394459;
            border-radius: 5px; padding: 4px; selection-background-color: #356eb4;
            alternate-background-color: #273042;
        }
        QPushButton { background: #2d374a; border: 1px solid #46536b; border-radius: 5px; padding: 7px 9px; }
        QPushButton:hover { background: #3a4962; }
        QPushButton:disabled { color: #8490a2; }
        QHeaderView::section { background: #303a4d; color: white; padding: 6px; border: 0px; }
        QFrame#diskBox, QFrame#tile { border: 1px solid #354052; border-radius: 7px; }
        QProgressBar { background: #30394c; border: 0; border-radius: 4px; text-align: center; min-height: 17px; }
        QProgressBar::chunk { background: #3986c5; border-radius: 4px; }
        QMenu { background: #222937; color: white; }
        QMenu::item:selected { background: #355a8b; }
    """)
    window = MainWindow()
    window.show()
    return app.exec()
