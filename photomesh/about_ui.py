"""Offline About and full application license dialogs."""
from html import escape
from pathlib import Path
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton,
                               QDialogButtonBox, QPlainTextEdit, QMessageBox)
from . import APP_NAME, APP_VERSION

LICENSE_PATH = Path(__file__).resolve().parent.parent / "LICENSE"


def show_license(parent):
    try:
        text = LICENSE_PATH.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        QMessageBox.warning(parent, "License", f"Cannot read the bundled license:\n{error}")
        return
    dialog = QDialog(parent)
    dialog.setWindowTitle(f"{APP_NAME} — License")
    dialog.resize(720, 560)
    layout = QVBoxLayout(dialog)
    viewer = QPlainTextEdit()
    viewer.setReadOnly(True)
    viewer.setPlainText(text)
    layout.addWidget(viewer)
    buttons = QDialogButtonBox(QDialogButtonBox.Close)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    dialog.exec()


def show_about(parent):
    dialog = QDialog(parent)
    dialog.setWindowTitle(f"About {APP_NAME}")
    dialog.resize(600, 450)
    layout = QVBoxLayout(dialog)
    text = QLabel(
        f"<b>{escape(APP_NAME)} — {escape(APP_VERSION)}</b>"
        "<p>Desktop photogrammetry application.<br>"
        "Runs fully offline; no network connection is required for processing.</p>"
        "<p>Reconstruction: COLMAP (BSD), with optional GLOMAP (BSD) for compatible legacy workflows.<br>"
        "Processing pipeline: fastpipe.<br>User interface: PySide6 / pyqtgraph.</p>"
        "<p><b>License</b></p>"
        "<p>Free for personal and educational, non-commercial use. Commercial use, including evaluation "
        "for company workflows, requires prior written permission from Behdad Nayyerpour.</p>"
        "<p>Third-party components retain their respective licenses.</p>")
    text.setWordWrap(True)
    layout.addWidget(text)
    license_button = QPushButton("View full license")
    license_button.clicked.connect(lambda: show_license(dialog))
    layout.addWidget(license_button)
    layout.addWidget(QLabel("© 2026 Behdad Nayyerpour."))
    buttons = QDialogButtonBox(QDialogButtonBox.Close)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    dialog.exec()
