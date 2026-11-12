"""Consistent task progress in the relevant pane and a minimal status bar."""
from PySide6.QtCore import Signal, QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QStatusBar, QPushButton
from .progress import WorkProgress


class ActivityStatusBar(QStatusBar):
    """Transient details go to logs/tooltips, never replace Ready/Busy."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.details = ""
        self.state = "Ready"
        super().showMessage(self.state)

    def showMessage(self, text, timeout=0):
        self.details = str(text)
        self.setToolTip(self.details)
        host = self.parentWidget()
        if self.details not in ("Ready", "Busy", "") and hasattr(host, "console"):
            host.log(self.details)
        super().showMessage(self.state)

    def clearMessage(self):
        super().showMessage(self.state)

    def set_busy(self, active):
        self.state = "Busy" if active else "Ready"
        super().showMessage(self.state)


class ProgressPanel(QWidget):
    """One measured counter; inner-file progress is not separately reported."""
    cancelled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        self.detail = QLabel(); self.detail.setWordWrap(True)
        self.overall = QProgressBar(); self.overall.setFormat("Overall: %p%")
        self.subtask = QProgressBar(); self.subtask.setFormat("Current task: %p%")
        self.subtask.hide()
        self.timing = QLabel()
        self.meter = WorkProgress()
        self.timer = QTimer(self); self.timer.setInterval(1000)
        self.timer.timeout.connect(self._refresh_timing)
        for w in (self.detail, self.overall, self.subtask, self.timing):
            layout.addWidget(w)
        button = QPushButton("Cancel", self)
        button.clicked.connect(self.cancelled)
        layout.addWidget(button)
        self.hide()

    def _refresh_timing(self):
        self.timing.setText(self.meter.text())

    def showEvent(self, event):
        self.timer.start()
        super().showEvent(event)

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def update_progress(self, done=0, total=0, text=""):
        self.detail.setText(text)
        self.meter.update(done, total)
        self.overall.setRange(0, total if total > 0 else 0)
        if total > 0:
            self.overall.setValue(min(max(0, done), total))
        # Reports count completed files/items, not the fraction of the current file.
        # Show that inner work as indeterminate until it has actually completed.
        self.subtask.setRange(0, 100 if total > 0 and done >= total else 0)
        if self.subtask.maximum():
            self.subtask.setValue(100)
        self.timing.setText(self.meter.text())
        self.show()

    def reset(self):
        self.meter.reset()
        self.hide()
