from pathlib import Path
import hashlib
from PySide6.QtGui import QDesktopServices
from photomesh import documentation


def test_manual_is_exact_render_reviewed_updated_pdf():
    path = documentation.RESOURCES/'manual/Lens2Mesh_1.0.5_Complete_User_Manual.pdf'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == '83bcd31c0ddea7277227045311f5f74117164d7bf96b8dac933296cae02f9faf'


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


def test_third_party_notice_index_opens_offline_with_local_license_texts(window, monkeypatch):
    import json
    opened = []
    monkeypatch.setattr(QDesktopServices, 'openUrl', lambda url: opened.append(url.toLocalFile()) or True)
    window.actions['Third-party Notices...'].trigger()
    path = Path(opened[0]); text = path.read_text(encoding='utf-8')
    assert path.is_file() and path.name == 'index.html'
    assert 'LGPL' in text and 'LightGlue' in text and 'numpy' in text
    assert '<script' not in text and '<iframe' not in text and '<img' not in text
    record = json.loads((path.parent/'review.json').read_text(encoding='utf-8'))
    assert record['redistribution_clearance'] is False and record['release_blockers']
    for name in ('GPL-3.0.txt', 'LGPL-3.0.txt', 'COLMAP-4.2.1.txt', 'GCC-exception-3.1.txt'):
        assert (path.parent/name).is_file()


def test_primary_provenance_records_retain_exact_evidence_bytes():
    import json
    root = documentation.RESOURCES/'third-party'
    record = json.loads((root/'review.json').read_text(encoding='utf-8'))
    proof = record['primary_identity']
    assert proof['qt_mismatches'] == 0 and proof['qt_compared'] == 1564
    assert sum(group['matched'] for group in proof['native_groups']) == 145
    for item in proof['proof_records']:
        assert hashlib.sha256((root/item['path']).read_bytes()).hexdigest() == item['sha256']
    for version in ('11.8','13.2'):
        text = (root/f'NVIDIA-CUDA-{version}-EULA.txt').read_text(encoding='utf-8')
        assert 'NVIDIA' in text and 'Distribution' in text and '<script' not in text
