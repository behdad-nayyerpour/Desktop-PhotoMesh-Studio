"""Disposable CI visual evidence for the 1.0.4 layout and offline dialogs."""
import base64
import os
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PySide6.QtCore import QCoreApplication, Qt, QBuffer, QIODevice, QSettings
QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
from PySide6.QtWidgets import QApplication, QDialog, QLabel
app = QApplication([])
app.setOrganizationName("PhotoMesh104VisualReview")
app.setApplicationName("PhotoMesh104VisualReview")
QSettings.setDefaultFormat(QSettings.IniFormat)
QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, tempfile.mkdtemp())
from photomesh.mainwindow import MainWindow
from photomesh.theme import apply_theme
from photomesh.about_ui import show_license
window = MainWindow()
window.resize(1500, 920)
window.show()

def capture(widget, label):
    widget.show()
    for _ in range(8):
        app.processEvents()
    buffer = QBuffer()
    buffer.open(QIODevice.WriteOnly)
    widget.grab().save(buffer, "PNG")
    print(label + "_IMAGE=" + base64.b64encode(bytes(buffer.data())).decode(), flush=True)

original = QDialog.exec
for theme in ("Dark", "Light"):
    apply_theme(app, theme)
    capture(window, "LAYOUT_" + theme.upper())
    def dialog_capture(dialog):
        capture(dialog, "DIALOG_" + theme.upper() + "_" + dialog.windowTitle().replace(" ", "_"))
        for label in dialog.findChildren(QLabel):
            if label.wordWrap() and label.isVisible():
                assert label.height() >= label.heightForWidth(label.width()), label.text()
        dialog.hide()
        return 0
    QDialog.exec = dialog_capture
    window.about()
    show_license(window)
QDialog.exec = original
print("UI_REVIEW_OK scale=" + os.environ.get("QT_SCALE_FACTOR", "1"), flush=True)
os._exit(0)
