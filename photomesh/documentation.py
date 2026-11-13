"""Offline access to bundled documentation and upstream notices."""
from pathlib import Path
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox

RESOURCES = Path(__file__).resolve().parent / 'resources'


def open_bundled(parent, relative, title):
    path = RESOURCES / relative
    if not path.is_file():
        QMessageBox.warning(parent, title, 'This document is missing. Reapply the latest application update and try again.')
        return False
    if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):
        QMessageBox.warning(parent, title, 'The document could not be opened. Install a PDF viewer or web browser and try again.')
        return False
    return True


def open_manual(parent):
    return open_bundled(parent, 'manual/Lens2Mesh_1.0.5_Complete_User_Manual.pdf', 'User Manual (PDF)')


def open_notices(parent):
    return open_bundled(parent, 'third-party/index.html', 'Third-party Notices')
