"""Verify a disposable installed candidate against its source checkout, offline."""
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import tempfile

app_root, source_root, output = map(lambda value: Path(value).resolve(), sys.argv[1:4])
output.mkdir(parents=True, exist_ok=True)
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
expected = {path.relative_to(source_root).as_posix(): digest(path)
            for path in (source_root / "photomesh").rglob("*") if path.is_file() and
            "__pycache__" not in path.parts and path.suffix != ".pyc"}
actual = {path.relative_to(app_root).as_posix(): digest(path)
          for path in (app_root / "photomesh").rglob("*") if path.is_file() and
          "__pycache__" not in path.parts and path.suffix != ".pyc"}
assert actual == expected, "Installed application files differ from source"
assert digest(app_root / "LICENSE") == digest(source_root / "LICENSE")
assert digest(app_root / "main.py") == digest(source_root / "main.py")
sys.path.insert(0, str(app_root))
import photomesh
assert photomesh.APP_NAME == 'Lens2Mesh' and photomesh.APP_VERSION == "1.0.5"
assert Path(photomesh.__file__).resolve().is_relative_to(app_root)
def deny(*args, **kwargs):
    raise AssertionError("Installed validation attempted network access")
socket.create_connection = socket.getaddrinfo = socket.socket.connect = deny
from PySide6.QtCore import QCoreApplication, QSettings, Qt
QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
from PySide6.QtWidgets import QApplication, QDialog, QLabel, QPlainTextEdit, QPushButton
app = QApplication([])
app.setOrganizationName("Lens2Mesh105InstalledAcceptance")
app.setApplicationName("Lens2Mesh105InstalledAcceptance")
QSettings.setDefaultFormat(QSettings.IniFormat)
QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, tempfile.mkdtemp())
from photomesh.mainwindow import MainWindow
from photomesh.theme import apply_theme
from photomesh.about_ui import show_license
from photomesh import documentation
from PySide6.QtGui import QDesktopServices
opened = []
QDesktopServices.openUrl = lambda url: opened.append(url.toLocalFile()) or True
assert documentation.open_manual(None)
assert digest(Path(opened[-1])) == '716a33f587cd3cd3303629b33d6096d7a120bed4c753808f3b0e21bf58f04706'
window = MainWindow()
window.resize(1500, 920)
window.show()
assert [window.tabs.tabText(i) for i in range(window.tabs.count())] == ["3D View", "Plan View"]
assert not window.unhandled_actions
assert window.dockWidgetArea(window.docks["Photos"]) == Qt.RightDockWidgetArea
assert all(window.docks[name].isHidden() for name in ("Console", "Jobs"))
seen = []
for theme in ("Dark", "Light"):
    apply_theme(app, theme)
    for _ in range(5): app.processEvents()
    window.grab().save(str(output / ("installed-" + theme.lower() + ".png")))
    def verify(dialog):
        dialog.show()
        for _ in range(5): app.processEvents()
        labels = " ".join(label.text() for label in dialog.findChildren(QLabel))
        if "About" in dialog.windowTitle():
            assert "1.0.5" in labels and "evaluation for company workflows" in labels
            assert any(button.text() == "View full license" for button in dialog.findChildren(QPushButton))
            for label in dialog.findChildren(QLabel):
                if label.wordWrap():
                    assert label.height() >= label.heightForWidth(label.width())
            kind = "about"
        else:
            text = dialog.findChild(QPlainTextEdit)
            assert text and text.isReadOnly()
            assert text.toPlainText() == (app_root / "LICENSE").read_text(encoding="utf-8")
            kind = "license"
        dialog.grab().save(str(output / (kind + "-" + theme.lower() + ".png")))
        seen.append((theme, kind))
        dialog.hide()
        return 0
    QDialog.exec = verify
    window.about()
    show_license(window)
assert len(seen) == 4
(output / "installed-acceptance.json").write_text(json.dumps({
    "version": photomesh.APP_VERSION, "matched_app_files": len(expected),
    "offline_about_license_themes": seen, "license_sha256": digest(app_root / "LICENSE")
}, indent=2), encoding="utf-8")
print("INSTALLED_105_ACCEPTANCE_OK", flush=True)
os._exit(0)
