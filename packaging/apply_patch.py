"""Apply a hash-bound test candidate to an installed app; never run pip/Setup.

The bootstrap authenticates the entire candidate archive before launching this
script with the installed Python. All managed destinations are explicit app
files. The runtime, projects, photos and settings are outside this allowlist.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import uuid

_QT_PLAN = Path(__file__).with_name('reviewed-qt-removals.json')
_QT_REMOVALS = ({entry['path'] for entry in json.loads(_QT_PLAN.read_text(encoding='utf-8'))['files']}
                if _QT_PLAN.is_file() else set())
_ENGINE_PLAN = Path(__file__).with_name('reviewed-engine-patches.json')
_ENGINE_PATCHES = ({entry['path']: entry for entry in json.loads(_ENGINE_PLAN.read_text(encoding='utf-8'))['files']
                   if entry['path'] in ('tools/colmap/bin/colmap.exe', 'tools/colmap-cpu/bin/colmap.exe')}
                  if _ENGINE_PLAN.is_file() else {})


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(4 << 20), b""):
            h.update(block)
    return h.hexdigest()


def managed(root, relative):
    """Resolve a canonical manifest path without following symlink destinations."""
    p = PurePosixPath(relative)
    if (not relative or "\\" in relative or ":" in relative or p.is_absolute()
            or any(x in (".", "..", "") for x in relative.split("/"))
            or len(p.parts) < 2):
        raise ValueError(f"Not a managed application path: {relative!r}")
    # Exact reviewed Qt addon removals also permit restoration of their backups.
    # Arbitrary Python/engine replacement remains forbidden.
    dependency = re.fullmatch(
        r"python/Lib/site-packages/(?:plyfile\.py|plyfile/[^:]+|"
        r"plyfile-[0-9][^/]*\.dist-info/[^:]+|__pycache__/plyfile\.[^/]+\.pyc)", relative)
    qt_dependency = relative in _QT_REMOVALS and relative.startswith('python/Lib/site-packages/PySide6/')
    if p.parts[0] != "app" and not dependency and not qt_dependency and relative not in _ENGINE_PATCHES:
        raise ValueError(f"Not an allowed runtime dependency path: {relative!r}")
    target = root.joinpath(*p.parts)
    for part in (target, *target.parents):
        if part == root:
            break
        if part.is_symlink() or part.is_junction():
            raise ValueError(f"Linked patch destination is not allowed: {relative}")
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Path escapes installation: {relative}")
    return target


def ensure_closed(root):
    import psutil
    me = os.getpid()
    for process in psutil.process_iter(["pid", "exe", "cmdline"]):
        if process.pid == me:
            continue
        try:
            # Protected/system processes may have no executable path. Resolving
            # an empty path would falsely identify the current working directory
            # as their executable (notably when Setup starts us in root/python).
            name = process.info['exe']
            executable = Path(name).resolve() if name else None
            args = process.info["cmdline"] or []
            if ((executable is not None and executable.is_relative_to(root / "python"))
                    or any(str(root / "app").casefold() in arg.casefold() for arg in args)):
                raise RuntimeError("Close this application's windows and processing jobs before updating.")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue


def write_json(path, value):
    temp = path.with_suffix(".tmp")
    with open(temp, "w", encoding="utf-8") as fh:
        json.dump(value, fh, indent=2)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(temp, path)


def replace_from(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = destination.with_name(destination.name + ".lens2mesh-patch-tmp")
    if temp.exists():
        raise RuntimeError(f"Interrupted update file exists: {temp}; use rollback first")
    created = False
    try:
        with open(source, "rb") as src, open(temp, "xb") as dst:
            created = True
            shutil.copyfileobj(src, dst, 4 << 20)
            dst.flush()
            os.fsync(dst.fileno())
        os.replace(temp, destination)
    finally:
        if created and temp.exists():
            temp.unlink()


def validate_manifest(manifest, root, payload):
    if manifest.get("schema") != 1:
        raise ValueError("Unsupported patch manifest")
    candidate = manifest.get("candidate", "")
    if len(candidate) != 40 or any(c not in "0123456789abcdef" for c in candidate):
        raise ValueError("Candidate must be an exact Git commit")
    identity = root / "app/runtime.id"
    if not identity.is_file() or identity.read_text().strip() != manifest["runtime_id"]:
        raise ValueError("Installed runtime does not match the verified 1.0.4 baseline")
    if not (root / "python/python.exe").is_file():
        raise ValueError("Choose the installation root containing app and python")
    # Validate the complete baseline code/resources, not just a version string.
    for relative, expected in manifest["baseline"].items():
        path = managed(root, relative)
        if not path.is_file() or digest(path) != expected:
            raise ValueError(f"Baseline differs at {relative}; no files were replaced")
    seen = set()
    for entry in manifest["files"]:
        relative = entry["path"]
        if relative.casefold() in seen:
            raise ValueError("Duplicate patch target")
        seen.add(relative.casefold())
        target = managed(root, relative)
        if relative in _ENGINE_PATCHES:
            review = _ENGINE_PATCHES[relative]
            if (entry.get('remove') or entry['sha256'] != review['after']
                    or manifest['baseline'].get(relative) != review['before']):
                raise ValueError('Engine replacement is not the exact reviewed UTF-8 manifest change')
        if relative not in manifest["baseline"] and target.exists():
            raise ValueError(f"New target already exists: {relative}")
        if entry.get("remove"):
            if relative not in manifest["baseline"]:
                raise ValueError("Removal has no verified baseline file")
        else:
            if relative.startswith("python/"):
                raise ValueError("This candidate can remove reviewed dependencies but cannot replace Python dependencies")
            source = managed(payload, relative)
            if not source.is_file() or digest(source) != entry["sha256"]:
                raise ValueError(f"Candidate payload checksum mismatch: {relative}")


def rollback(root, state_dir):
    if not state_dir.resolve().is_relative_to(root / ".lens2mesh-patches"):
        raise ValueError("Recovery state must belong to this installation's patch directory")
    state_path = state_dir / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if Path(state["root"]).resolve() != root:
        raise ValueError("Backup belongs to another installation")
    # Inspect all destinations first: never overwrite subsequent user changes.
    for entry in state["files"]:
        target = managed(root, entry["path"])
        if target.exists() and digest(target) not in (entry["sha256"], entry["before"]):
            raise ValueError(f"File changed after patch: {entry['path']}; restore manually")
        if entry["before"] is not None:
            backup = managed(state_dir / "backup", entry["path"])
            if not backup.is_file() or digest(backup) != entry["before"]:
                raise ValueError(f"Backup checksum mismatch: {entry['path']}")
    for entry in reversed(state["files"]):
        target = managed(root, entry["path"])
        # Only this candidate's journal-owned temporary destinations are removed.
        # They may remain if the process or machine stopped during a replacement.
        temp = target.with_name(target.name + ".lens2mesh-patch-tmp")
        if temp.is_symlink() or temp.is_junction():
            raise ValueError("Linked recovery temporary file is not allowed")
        temp.unlink(missing_ok=True)
        if entry["before"] is None:
            target.unlink(missing_ok=True)
        else:
            replace_from(managed(state_dir / "backup", entry["path"]), target)
    state["status"] = "rolled_back"
    write_json(state_path, state)


def apply(root, payload, manifest):
    validate_manifest(manifest, root, payload)
    parent = root / ".lens2mesh-patches"
    if parent.is_symlink() or parent.is_junction():
        raise ValueError("Patch backup directory must not be a link")
    parent.mkdir(exist_ok=True)
    # Preserve every recovery attempt. A verified baseline may be updated again
    # after rollback without deleting or overwriting the previous backup journal.
    state_dir = parent / manifest["candidate"]
    while True:
        try:
            state_dir.mkdir()
            break
        except FileExistsError:
            state_dir = parent / (manifest["candidate"] + "-" + uuid.uuid4().hex[:12])
    entries = []
    for entry in manifest["files"]:
        target = managed(root, entry["path"])
        before = digest(target) if target.exists() else None
        if before is not None:
            backup = managed(state_dir / "backup", entry["path"])
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, backup)
            if digest(backup) != before:
                raise RuntimeError("Backup verification failed; no files were replaced")
        entries.append({**entry, "before": before})
    state = {"root": str(root), "status": "applying", "files": entries}
    shutil.copy2(__file__, state_dir / "apply_patch.py")
    if _QT_PLAN.is_file():
        shutil.copy2(_QT_PLAN, state_dir / _QT_PLAN.name)
    if _ENGINE_PLAN.is_file():
        shutil.copy2(_ENGINE_PLAN, state_dir / _ENGINE_PLAN.name)
    write_json(state_dir / "state.json", state)
    # ASCII-only batch source with Unicode paths obtained from cmd's %~dp0.
    # Embedding UTF-8 path literals breaks under legacy console code pages.
    recovery = ('@echo off\r\nfor %%I in ("%~dp0..\\..") do set "LM_RESTORE_ROOT=%%~fI"\r\n'
                '"%LM_RESTORE_ROOT%\\python\\python.exe" "%~dp0apply_patch.py" '
                '--root "%LM_RESTORE_ROOT%" --rollback "%~dp0."\r\n'
                'set "LM_RESTORE_EXIT=%ERRORLEVEL%"\r\npause\r\nexit /b %LM_RESTORE_EXIT%\r\n')
    (state_dir / "ROLLBACK.bat").write_bytes(recovery.encode("ascii"))
    try:
        for entry in entries:
            if entry.get("remove"):
                managed(root, entry["path"]).unlink()
            else:
                replace_from(managed(payload, entry["path"]), managed(root, entry["path"]))
        state["status"] = "applied"
        write_json(state_dir / "state.json", state)
    except BaseException:
        rollback(root, state_dir)
        raise
    return state_dir


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--payload", type=Path)
    parser.add_argument("--rollback", type=Path)
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    ensure_closed(root)
    # An OS lock is released on crash; the state journal supports recovery.
    import msvcrt
    with open(root / ".lens2mesh-patch.lock", "a+b") as lock:
        lock.seek(0)
        if lock.read(1) == b"":
            lock.write(b"0"); lock.flush()
        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        if args.rollback:
            rollback(root, args.rollback.resolve(strict=True))
            print("Previous application files restored.")
        else:
            payload = args.payload.resolve(strict=True)
            manifest = json.loads((payload / "manifest.json").read_text(encoding="utf-8"))
            state_dir = apply(root, payload, manifest)
            print(f"Candidate applied. Backup and rollback: {state_dir}")


if __name__ == "__main__":
    # An unsupported console glyph must never turn a successful update into a
    # reported failure, especially with Persian/custom installation paths.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="backslashreplace")
    try:
        main()
    except Exception as exc:
        print(f"Update stopped: {exc}", file=sys.stderr)
        sys.exit(1)
