"""Safety contracts using disposable fixtures, never a personal installation."""
import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "candidate_updater", Path(__file__).resolve().parents[1] / "packaging/apply_patch.py")
updater = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(updater)


@pytest.fixture
def fixture(tmp_path):
    root, payload = tmp_path / "install فارسی", tmp_path / "payload"
    for base in (root, payload):
        (base / "app/photomesh").mkdir(parents=True)
    (root / "python").mkdir()
    (root / "python/python.exe").write_bytes(b"unchanged runtime")
    (root / "app/runtime.id").write_text("a" * 64)
    (root / "app/main.py").write_bytes(b"previous")
    (root / "project.pmsx").write_bytes(b"user data")
    (payload / "app/main.py").write_bytes(b"candidate")
    (payload / "app/photomesh/new.py").write_bytes(b"new module")
    manifest = {"schema": 1, "candidate": "c" * 40, "runtime_id": "a" * 64,
                "baseline": {"app/main.py": updater.digest(root / "app/main.py")},
                "files": [{"path": p, "sha256": updater.digest(payload / p)}
                          for p in ("app/main.py", "app/photomesh/new.py")]}
    return root, payload, manifest


def test_apply_and_rollback_preserve_runtime_and_user_data(fixture):
    root, payload, manifest = fixture
    state = updater.apply(root, payload, manifest)
    assert (root / "app/main.py").read_bytes() == b"candidate"
    assert (root / "app/photomesh/new.py").is_file()
    assert json.loads((state / "state.json").read_text())["status"] == "applied"
    updater.rollback(root, state)
    assert (root / "app/main.py").read_bytes() == b"previous"
    assert not (root / "app/photomesh/new.py").exists()
    assert (root / "python/python.exe").read_bytes() == b"unchanged runtime"
    assert (root / "project.pmsx").read_bytes() == b"user data"


def test_reviewed_qt_removal_and_recovery_keep_core_and_plan(fixture):
    root, payload, manifest = fixture
    relative = 'python/Lib/site-packages/PySide6/Qt6Charts.dll'
    assert relative in updater._QT_REMOVALS
    addon = root/relative; addon.parent.mkdir(parents=True); addon.write_bytes(b'reviewed fixture addon')
    core = addon.with_name('Qt6Core.dll'); core.write_bytes(b'required core')
    manifest['baseline'][relative] = updater.digest(addon)
    manifest['files'].append(dict(path=relative, sha256=None, remove=True))
    state = updater.apply(root, payload, manifest)
    assert not addon.exists() and core.read_bytes() == b'required core'
    assert (state/'reviewed-qt-removals.json').is_file()
    updater.rollback(root, state)
    assert addon.read_bytes() == b'reviewed fixture addon'
    assert core.read_bytes() == b'required core'
    with pytest.raises(ValueError, match='allowed runtime'):
        updater.managed(root, 'python/Lib/site-packages/PySide6/Qt6Core.dll')


def test_reviewed_qt_scope_cannot_replace_a_runtime_binary(fixture):
    root, payload, manifest = fixture
    relative = 'python/Lib/site-packages/PySide6/Qt6Charts.dll'
    target = root/relative; target.parent.mkdir(parents=True); target.write_bytes(b'old')
    manifest['baseline'][relative] = updater.digest(target)
    manifest['files'].append(dict(path=relative, sha256='b'*64))
    with pytest.raises(ValueError, match='cannot replace Python'):
        updater.apply(root, payload, manifest)
    assert target.read_bytes() == b'old'


@pytest.mark.parametrize("target", ["app/../project.pmsx", "app/../../file", "python/python.exe",
                                    "app\\main.py", "C:/app/main.py", "/app/main.py", "app//main.py"])
def test_reject_paths_outside_managed_application(fixture, target):
    root, _, _ = fixture
    with pytest.raises(ValueError):
        updater.managed(root, target)


@pytest.mark.parametrize("tamper", ["baseline", "payload", "runtime"])
def test_checksum_failures_replace_nothing(fixture, tamper):
    root, payload, manifest = fixture
    if tamper == "baseline":
        (root / "app/main.py").write_bytes(b"local customization")
    elif tamper == "payload":
        (payload / "app/main.py").write_bytes(b"corrupted download")
    else:
        (root / "app/runtime.id").write_text("b" * 64)
    before = (root / "app/main.py").read_bytes()
    with pytest.raises(ValueError):
        updater.apply(root, payload, manifest)
    assert (root / "app/main.py").read_bytes() == before
    assert not (root / "app/photomesh/new.py").exists()


def test_failed_replace_restores_already_replaced_files(fixture, monkeypatch):
    root, payload, manifest = fixture
    real = updater.replace_from
    calls = []
    def fail_second(source, target):
        calls.append(target)
        if len(calls) == 2:
            raise OSError("simulated interrupted copy")
        return real(source, target)
    monkeypatch.setattr(updater, "replace_from", fail_second)
    with pytest.raises(OSError):
        updater.apply(root, payload, manifest)
    assert (root / "app/main.py").read_bytes() == b"previous"
    assert not (root / "app/photomesh/new.py").exists()


def test_rollback_does_not_overwrite_later_edits(fixture):
    root, payload, manifest = fixture
    state = updater.apply(root, payload, manifest)
    (root / "app/main.py").write_bytes(b"later edit")
    with pytest.raises(ValueError, match="changed after patch"):
        updater.rollback(root, state)
    assert (root / "app/main.py").read_bytes() == b"later edit"
    assert (root / "app/photomesh/new.py").is_file()


def test_running_application_blocks_update(fixture, monkeypatch):
    import psutil
    root, _, _ = fixture
    class Process:
        pid = 99999999
        info = {"exe": str(root / "python/pythonw.exe"), "cmdline": []}
    monkeypatch.setattr(psutil, "process_iter", lambda *args: [Process()])
    with pytest.raises(RuntimeError, match="Close"):
        updater.ensure_closed(root)


def test_power_loss_temporary_file_can_be_recovered(fixture):
    root, payload, manifest = fixture
    state = updater.apply(root, payload, manifest)
    interrupted = root / "app/main.py.lens2mesh-patch-tmp"
    interrupted.write_bytes(b"incomplete copy")
    updater.rollback(root, state)
    assert (root / "app/main.py").read_bytes() == b"previous"
    assert not interrupted.exists()


def test_exact_dependency_removal_is_reversible(fixture):
    root, payload, manifest = fixture
    relative = "python/Lib/site-packages/plyfile.py"
    dependency = root / relative
    dependency.parent.mkdir(parents=True)
    dependency.write_bytes(b"previous dependency")
    manifest["baseline"][relative] = updater.digest(dependency)
    manifest["files"].append({"path": relative, "sha256": None, "remove": True})
    state = updater.apply(root, payload, manifest)
    assert not dependency.exists()
    updater.rollback(root, state)
    assert dependency.read_bytes() == b"previous dependency"


def test_runtime_replacement_is_not_allowed(fixture):
    root, payload, manifest = fixture
    relative = "python/Lib/site-packages/plyfile.py"
    target = payload / relative
    target.parent.mkdir(parents=True)
    target.write_bytes(b"unexpected runtime replacement")
    manifest["files"].append({"path": relative, "sha256": updater.digest(target)})
    with pytest.raises(ValueError, match="cannot replace"):
        updater.apply(root, payload, manifest)


def test_same_candidate_can_be_applied_after_rollback_without_losing_history(fixture):
    root, payload, manifest = fixture
    first = updater.apply(root, payload, manifest)
    updater.rollback(root, first)
    second = updater.apply(root, payload, manifest)
    assert first != second and first.exists()
    assert json.loads((first / "state.json").read_text())["status"] == "rolled_back"
    assert (first / "backup/app/main.py").read_bytes() == b"previous"
    assert (root / "app/main.py").read_bytes() == b"candidate"
    updater.rollback(root, second)
    assert (root / "app/main.py").read_bytes() == b"previous"
