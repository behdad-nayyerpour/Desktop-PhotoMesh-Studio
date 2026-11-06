"""Validate the actual upgraded 1.0.3 installation on a disposable CI runner."""
from pathlib import Path
import hashlib
import json
import os
import sys

app_root = Path(sys.argv[1]).resolve()
output = Path(sys.argv[2]).resolve()
repository = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(app_root))

from PySide6.QtCore import QCoreApplication, Qt
QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
from PySide6.QtWidgets import QApplication, QMessageBox, QStyle, QStyleOptionToolButton
from PySide6.QtGui import QFont, QFontDatabase, QRawFont
import photomesh
assert photomesh.APP_VERSION == "1.0.3"
assert "PhotoMesh Studio 1.0.3" in (app_root / "release_manifest.txt").read_text(encoding="ascii")
assert Path(photomesh.__file__).resolve().is_relative_to(app_root)
assert (app_root / "photomesh" / "resources" / "photomesh.ico").is_file()
assert (app_root / "packaging" / "fix_shortcut_icon.ps1").is_file()
expected = {p.relative_to(repository / "photomesh"): p for p in (repository / "photomesh").rglob("*.py")}
installed = {p.relative_to(app_root / "photomesh"): p for p in (app_root / "photomesh").rglob("*.py")}
assert set(expected) == set(installed), "Missing or obsolete application source files after upgrade"
for name, path in expected.items():
    assert hashlib.sha256(path.read_bytes()).digest() == hashlib.sha256(installed[name].read_bytes()).digest(), name

from photomesh.memguard import require_available_bytes
available = require_available_bytes()
app = QApplication([])
assert QFontDatabase.addApplicationFont(str(Path(os.environ["WINDIR"]) / "Fonts" / "segoeui.ttf")) >= 0
app.setFont(QFont("Segoe UI", 9))
assert QRawFont.fromFont(app.font()).supportsCharacter(ord("T"))
app.setOrganizationName("PhotoMeshReleaseAcceptance")
app.setApplicationName("PhotoMesh103")
from photomesh.mainwindow import MainWindow
from photomesh.theme import apply_theme
window = MainWindow()
window.resize(1600, 900)
window.show()
about = []
QMessageBox.about = staticmethod(lambda parent, title, text: about.append(text))
window.actions["About PhotoMesh Studio..."].trigger()
assert len(about) == 1 and "1.0.3" in about[0]
assert "1.0.3" in window.windowTitle()
assert not hasattr(window, "toggle_full_screen") and not hasattr(window, "measure_shape")
measurements = []
for theme in ("Dark", "Light"):
    apply_theme(app, theme)
    for checked in (False, True):
        for button in window.mode_buttons:
            button.visibility.setChecked(checked)
        for _ in range(10): app.processEvents()
        for button in window.mode_buttons:
            option = QStyleOptionToolButton()
            button.initStyleOption(option)
            body = button.style().subControlRect(QStyle.CC_ToolButton, option, QStyle.SC_ToolButton, button)
            arrow = button.style().subControlRect(QStyle.CC_ToolButton, option, QStyle.SC_ToolButtonMenu, button)
            room = body.width() - body.intersected(arrow).width()
            text = button.fontMetrics().horizontalAdvance(button.title)
            assert room >= text + 8, (theme, checked, button.title, room, text)
            assert button.text() == button.title and button.isChecked() == checked
            assert button.iconSize().width() == 21
            changes = []
            on_change = changes.append
            button.visibility.toggled.connect(on_change)
            button.click()
            assert changes == [not checked]
            button.visibility.toggled.disconnect(on_change)
            button.visibility.setChecked(checked)
            measurements.append({"theme": theme, "checked": checked, "title": button.title,
                                 "caption_room": room, "text_width": text})
output.mkdir(parents=True, exist_ok=True)
image_path = output / "installed-layers.png"
assert window.display_toolbar.grab().save(str(image_path))
import base64
print("CAPTURE_IMAGE preview/installed-layers.png " + base64.b64encode(image_path.read_bytes()).decode("ascii"), flush=True)
payload = {"installed_version": photomesh.APP_VERSION, "application_root": str(app_root),
           "source_modules_match": len(expected), "about_version_verified": True,
           "available_ram": available, "captions": measurements}
(output / "installed-validation.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
print(json.dumps(payload, indent=2), flush=True)
window.project.modified = False
window.close()
app.processEvents()
os._exit(0)
