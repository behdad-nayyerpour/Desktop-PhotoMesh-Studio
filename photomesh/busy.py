"""Counted activity; interactive dialogs keep the normal pointer."""
from contextlib import contextmanager
from weakref import WeakSet

from PySide6.QtCore import QObject, Qt, QEvent, Signal, Slot
from PySide6.QtWidgets import QApplication, QLabel, QDialog
from shiboken6 import isValid


class _DialogCursorFilter(QObject):
    """One application-owned filter, independent of individual window lifetimes.

    Queue notifications: changing a cursor/status widget from inside Qt's
    style/show/hide event delivery can re-enter widget destruction.
    """
    changed = Signal()

    def __init__(self, app):
        super().__init__(app)
        self.interactive = WeakSet()
        self.listeners = WeakSet()
        self.pending = False
        self.changed.connect(self._notify, Qt.QueuedConnection)
        app.installEventFilter(self)

    def eventFilter(self, watched, event):
        if isinstance(watched, QDialog) and not watched.property("task_progress"):
            if event.type() == QEvent.Show:
                self.interactive.add(watched)
                self._schedule()
            elif event.type() == QEvent.Hide:
                self.interactive.discard(watched)
                self._schedule()
        return False

    def _schedule(self):
        if not self.pending:
            self.pending = True
            self.changed.emit()

    @Slot()
    def _notify(self):
        self.pending = False
        for listener in list(self.listeners):
            if isValid(listener) and isValid(listener.label):
                listener._show()
            else:
                self.listeners.discard(listener)


def _dialog_filter():
    app = QApplication.instance()
    registry = getattr(app, "_photomesh_dialog_cursor_filter", None)
    if registry is None:
        registry = _DialogCursorFilter(app)
        app._photomesh_dialog_cursor_filter = registry
    return registry


class BusyIndicator(QObject):
    def __init__(self, statusbar=None):
        super().__init__(statusbar)
        self.statusbar = statusbar
        self.titles = []
        self.tasks = {}
        self.label = QLabel(statusbar)
        self.label.hide()
        self._cursor = False
        self._dialogs = _dialog_filter()
        self._dialogs.listeners.add(self)

    @property
    def active(self):
        return bool(self.titles or self.tasks)

    @Slot()
    def _show(self):
        active = self.active
        self.label.setText("Busy" if active else "Ready")
        if self.statusbar is not None and isValid(self.statusbar) and hasattr(self.statusbar, "set_busy"):
            self.statusbar.set_busy(active)
        interactive = any(isValid(dialog) and dialog.isVisible()
                          for dialog in self._dialogs.interactive)
        wait_cursor = active and not interactive
        if wait_cursor and not self._cursor:
            QApplication.setOverrideCursor(Qt.BusyCursor)
            self._cursor = True
        elif not wait_cursor and self._cursor:
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
