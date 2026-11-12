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
