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
from .search import find_es, search_everything, search_local


def config_path() -> Path:
    home = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / ".config")))
    return home / "OmniFiles" / "settings.json"


class SearchWorker(QObject):
    done = Signal(object)
    error = Signal(str)
    finished = Signal()

    def __init__(self, query: str, folder: str, es_path: str | None):
        super().__init__()
        self.query = query
        self.folder = folder
        self.es_path = es_path
        self.cancel = threading.Event()

    def run(self) -> None:
        try:
            if self.es_path:
                output = search_everything(self.es_path, self.query)
            else:
                output = search_local(self.folder, self.query, cancel=self.cancel)
            self.done.emit(output)
        except Exception as ex:
            self.error.emit(str(ex))
        finally:
            self.finished.emit()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OmniFiles — explorador de archivos (prototipo 0.1)")
        self.resize(1180, 720)
        self.setMinimumSize(850, 480)
        self.history: list[str] = []
        self.position = -1
        self.active_search = False
        self.search_thread: QThread | None = None
        self.search_worker: SearchWorker | None = None

        self.settings = self._load_settings()
        self.bookmarks: list[str] = [p for p in self.settings.get("favorites", []) if isinstance(p, str)]
        self.es_path = str(self.settings.get("es_path", ""))

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
        self.search_edit.setPlaceholderText("Buscar archivos y carpetas en todas las unidades con Everything...")
        self.btn_search = QPushButton("Buscar")
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.setEnabled(False)
        self.btn_explorer = QPushButton("Ver carpeta")
        self.btn_es = QPushButton("Configurar ES")
        search_bar.addWidget(self.search_edit, stretch=1)
        for btn in (self.btn_search, self.btn_cancel, self.btn_explorer, self.btn_es):
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
        self.statusBar().showMessage("Listo. La versión 0.1 no modifica archivos.")

        self.btn_back.clicked.connect(self.go_back)
        self.btn_next.clicked.connect(self.go_next)
        self.btn_up.clicked.connect(self.go_up)
        self.btn_home.clicked.connect(lambda: self.navigate(str(Path.home())))
        self.btn_reload.clicked.connect(self.refresh)
        self.btn_fav.clicked.connect(self.toggle_favorite)
        self.path_edit.returnPressed.connect(self.navigate_address)
        self.btn_search.clicked.connect(self.start_search)
        self.btn_cancel.clicked.connect(self.cancel_search)
        self.btn_explorer.clicked.connect(lambda: self.pages.setCurrentIndex(0))
        self.btn_es.clicked.connect(self.configure_es)
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
            tmp.write_text(json.dumps({"favorites": self.bookmarks, "es_path": self.es_path}, indent=2, ensure_ascii=False), encoding="utf-8")
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
        candidate = find_es(self.es_path)
        if candidate:
            self.engine_label.setText("Motor disponible: Everything ES (se necesita Everything estándar ejecutándose).")
        else:
            self.engine_label.setText("Motor: búsqueda local acotada a la carpeta actual. Configura es.exe para búsqueda global.")

    def configure_es(self) -> None:
        chosen, _ = QFileDialog.getOpenFileName(self, "Seleccionar es.exe", str(Path.home()), "Ejecutable ES (es.exe);;Todos (*.*)")
        if chosen:
            self.es_path = chosen
            self._save_settings()
            self._refresh_search_status()

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
        es = find_es(self.es_path)
        if not es:
            answer = QMessageBox.question(
                self, "Búsqueda local limitada",
                "No encontramos es.exe. ¿Buscar solo por nombre dentro de la carpeta actual?\n"
                "La búsqueda tendrá límites de tiempo, resultados y directorios.\n"
                "Los filtros de Everything no se interpretarán en este modo.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        folder = self.path_edit.text()
        self.active_search = True
        self.btn_search.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.search_thread = QThread(self)
        self.search_worker = SearchWorker(query, folder, es)
        self.search_worker.moveToThread(self.search_thread)
        self.search_thread.started.connect(self.search_worker.run)
        self.search_worker.done.connect(self.search_done)
        self.search_worker.error.connect(self.search_error)
        self.search_worker.finished.connect(self.search_thread.quit)
        self.search_worker.finished.connect(self.search_worker.deleteLater)
        self.search_thread.finished.connect(self.search_thread.deleteLater)
        self.search_thread.finished.connect(self.search_cleanup)
        self.search_thread.start()
        self.statusBar().showMessage("Buscando...")

    def cancel_search(self) -> None:
        if self.search_worker:
            self.search_worker.cancel.set()
            self.btn_cancel.setEnabled(False)
            self.statusBar().showMessage("Cancelación solicitada; finalizando operación...")

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
        self.btn_cancel.setEnabled(False)

    def open_result(self, row: int, _column: int) -> None:
        item = self.results.item(row, 1)
        if item:
            self.open_path(item.text())

    def closeEvent(self, event) -> None:
        if self.active_search:
            self.cancel_search()
            QMessageBox.information(self, "Búsqueda en curso", "Se solicitó cancelar la búsqueda. Cierra la ventana cuando termine.")
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
