from pathlib import Path
import hashlib
from PySide6.QtGui import QDesktopServices
from photomesh import documentation


def test_manual_is_exact_approved_unmodified_pdf():
    path = documentation.RESOURCES/'manual/PhotoMeshStudio_1.0.4_Complete_User_Manual.pdf'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == '632dde8b0392787d735610dcf805ade49f10068f6086d4e01137f5a5e31610a4'


def test_help_manual_resolves_installed_resources_offline(window, monkeypatch):
    opened = []
    monkeypatch.setattr(QDesktopServices, 'openUrl', lambda url: opened.append(url.toLocalFile()) or True)
    window.actions['User Manual (PDF)'].trigger()
    assert Path(opened[0]).is_file() and opened[0].endswith('.pdf')
    assert 'Contents' in window.actions  # Preserve the existing Documentation command.


def test_missing_or_unopenable_manual_reports_actionable_error(window, monkeypatch, tmp_path):
    errors = []
    monkeypatch.setattr(documentation.QMessageBox, 'warning', lambda *args: errors.append(args[2]))
    monkeypatch.setattr(QDesktopServices, 'openUrl', lambda *_: False)
    assert not documentation.open_manual(window)
    assert 'PDF viewer' in errors[-1]
    monkeypatch.setattr(documentation, 'RESOURCES', tmp_path)
    assert not documentation.open_manual(window)
    assert 'Reapply' in errors[-1]
