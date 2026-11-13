"""Optional DLL installation preserves the base and supports exact rollback."""
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'packaging'))
import neural_addon as addon  # noqa: E402


@pytest.fixture
def installation(tmp_path):
    root, payload = tmp_path / 'base فارسی', tmp_path / 'payload'
    (root / 'app/photomesh').mkdir(parents=True)
    (root / 'python').mkdir()
    (root / 'python/python.exe').write_bytes(b'unchanged Python identity fixture')
    (root / 'app/runtime.id').write_text('a' * 64)
    (root / 'app/photomesh/__init__.py').write_text('APP_NAME = "Lens2Mesh"\nAPP_VERSION = "1.0.5"\n')
    content = b'fixed optional runtime'
    spec = dict(schema=1, assets=[dict(files=[dict(name='one.dll', bytes=len(content), sha256=hashlib.sha256(content).hexdigest())])])
    folder = payload / 'app/photomesh/resources/neural-cuda12'
    folder.mkdir(parents=True)
    (folder / 'one.dll').write_bytes(content)
    (folder / 'runtime.json').write_bytes((json.dumps(spec, indent=2) + '\n').encode('utf-8'))
    return root, payload, spec


def test_apply_repeat_and_rollback_leave_base_unchanged(installation):
    root, payload, spec = installation
    before = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}
    manifest = addon.make_manifest(root, payload, 'c' * 40, spec)
    state = addon.updater.apply(root, payload, manifest)
    assert (root / 'app/photomesh/resources/neural-cuda12/one.dll').read_bytes() == b'fixed optional runtime'
    assert addon.make_manifest(root, payload, 'c' * 40, spec)['files'] == []
    addon.updater.rollback(root, state)
    after = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file() and '.lens2mesh-patches' not in p.parts}
    assert after == before


def test_different_existing_runtime_fails_without_overwrite(installation):
    root, payload, spec = installation
    target = root / 'app/photomesh/resources/neural-cuda12/one.dll'
    target.parent.mkdir(parents=True)
    target.write_bytes(b'other version')
    with pytest.raises(ValueError, match='Different GPU runtime'):
        addon.make_manifest(root, payload, 'c' * 40, spec)
    assert target.read_bytes() == b'other version'


def test_wrong_app_or_payload_is_rejected(installation):
    root, payload, spec = installation
    (payload / 'app/photomesh/resources/neural-cuda12/one.dll').write_bytes(b'corrupt')
    with pytest.raises(ValueError, match='checksum mismatch'):
        addon.make_manifest(root, payload, 'c' * 40, spec)
    (root / 'app/photomesh/__init__.py').write_text('APP_NAME="Other"\nAPP_VERSION="1.0.5"\n')
    with pytest.raises(ValueError, match='existing Lens2Mesh'):
        addon.make_manifest(root, payload, 'c' * 40, spec)


@pytest.mark.parametrize('name', ['../escape.dll', 'sub/one.dll', 'C:one.dll', 'one.exe'])
def test_addon_does_not_accept_arbitrary_managed_targets(name):
    spec = dict(assets=[dict(files=[dict(name=name, sha256='0' * 64)])])
    with pytest.raises(ValueError, match='Unsafe'):
        addon.addon_files(spec)


@pytest.mark.parametrize('reported_exe,app_argument,blocked', [(None, False, False), ('', False, False), ('owned', False, True), (None, True, True)])
def test_app_close_missing_executable_is_not_the_working_directory(tmp_path, monkeypatch, reported_exe, app_argument, blocked):
    import psutil
    root = tmp_path / 'install'
    (root / 'python').mkdir(parents=True)
    monkeypatch.chdir(root / 'python')
    executable = str(root / 'python/python.exe') if reported_exe == 'owned' else reported_exe
    args = [str(root / 'app/main.py')] if app_argument else []
    monkeypatch.setattr(addon.updater.os, 'getpid', lambda: 102)
    processes = [SimpleNamespace(pid=101, info=dict(exe=executable, cmdline=args))]
    monkeypatch.setattr(psutil, 'process_iter', lambda *_: processes)
    if blocked:
        with pytest.raises(RuntimeError, match='Close this application'):
            addon.updater.ensure_closed(root)
    else:
        addon.updater.ensure_closed(root)
