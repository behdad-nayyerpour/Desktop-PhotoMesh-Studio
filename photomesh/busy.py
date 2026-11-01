"""Counted task activity and wait cursors; percentages belong in task windows."""
from contextlib import contextmanager
from PySide6.QtCore import QObject, Qt
from PySide6.QtWidgets import QApplication, QLabel


class BusyIndicator(QObject):
    def __init__(self, statusbar=None):
        super().__init__(statusbar)
        self.statusbar = statusbar
        self.titles = []
        self.tasks = {}
        self.label = QLabel(statusbar)
        self.label.hide()
        self._cursor = False

    @property
    def active(self):
        return bool(self.titles or self.tasks)

    def _show(self):
        active = self.active
        self.label.setText("Busy" if active else "Ready")
        if self.statusbar is not None and hasattr(self.statusbar, "set_busy"):
            self.statusbar.set_busy(active)
        if active and not self._cursor:
            QApplication.setOverrideCursor(Qt.BusyCursor)
            self._cursor = True
        elif not active and self._cursor:
            QApplication.restoreOverrideCursor()
            self._cursor = False

    def begin(self, title):
        self.titles.append(str(title))
        self._show()

    def end(self):
        if self.titles:
            self.titles.pop()
        self._show()

    def end_all(self):
        self.titles.clear()
        self.tasks.clear()
        self._show()

    def background(self, key, title=None, done=None, total=None, text=""):
        if title is None:
            self.tasks.pop(str(key), None)
        else:
            self.tasks[str(key)] = str(title)
        self._show()

    @contextmanager
    def __call__(self, title):
        self.begin(title)
        try:
            yield self
        finally:
            self.end()
