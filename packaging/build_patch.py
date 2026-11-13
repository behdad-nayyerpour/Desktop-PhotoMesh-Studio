"""Build a delta against an exact disposable installed baseline (no full Setup)."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import shutil
import zipfile

from runtime_dependencies import plyfile_files, reviewed_qt_files
from neural_runtime import runtime_files, RESOURCE


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(source, installed, output, revision, with_neural_runtime=False, with_engine_utf8=False, engine_only=False):
    output.mkdir(parents=True, exist_ok=True)
    baseline = {}
    for path in ([] if engine_only else (installed / "app").rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            baseline[path.relative_to(installed).as_posix()] = digest(path)
    # Application sources and reviewed resources only. Never include arbitrary
    # untracked files, personal projects or the reusable Python/engine runtime.
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=source).decode().split("\0")
    files = []
    # Never blindly delete a copied environment's packages. Only this exact
    # distribution's installed RECORD files are considered, and declared
    # transitive requirements block removal for manual review.
    ply = [] if engine_only else plyfile_files(installed)
    qt = [] if engine_only else reviewed_qt_files(installed)
    removed = ply + qt
    for path in removed:
        target = path.relative_to(installed.resolve()).as_posix()
        baseline[target] = digest(path)
        files.append({"path": target, "sha256": None, "remove": True})
    for relative in ([] if engine_only else tracked):
        path = source / relative
        allowed = (relative.startswith("photomesh/")
                   or relative in ("main.py", "requirements.txt", "packaging/fix_shortcut_icon.ps1",
                                   "packaging/migrate_shortcuts.ps1", "packaging/requirements-runtime-win313.lock",
                                   "README.md", "CHANGES.md", "UPDATING.md", "SCREENSHOT-LICENSE.txt",
                                   "screenshot.png", "screenshot-light.png", "docs/README.md",
                                   "docs/user-guide.md", "docs/candidate-105.md", "docs/installation.md",
                                   "packaging/README.md", "packaging/RELEASE.md"))
        if not allowed or not path.is_file():
            continue
        target = "app/" + relative
        sha = digest(path)
        previous = installed / target
        if (path.suffix in (".py", ".ps1") and previous.is_file()
                and path.read_bytes().replace(b"\r\n", b"\n")
                == previous.read_bytes().replace(b"\r\n", b"\n")):
            continue
        if baseline.get(target) != sha:
            files.append({"path": target, "sha256": sha})
    external = []
    for entry in (runtime_files() if with_neural_runtime else []):
        previous = installed / entry['path']
        if previous.is_file():
            baseline[entry['path']] = digest(previous)
        if baseline.get(entry['path']) == entry['sha256']:
            continue
        external.append(entry)
        files.append(entry)
    native = {}
    if with_engine_utf8:
        from utf8_engine import patch
        for entry in json.loads((source/'packaging/reviewed-engine-patches.json').read_text())['files']:
            original = installed/entry['path']
            if digest(original) == entry['after']:
                continue
            if digest(original) != entry['before']:
                raise ValueError('Unreviewed native engine; not replacing it')
            target = output/entry['path']; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(original, target)
            proof = patch(target, entry['before'])
            if proof['after'] != entry['after']:
                raise ValueError('Engine manifest output differs from reviewed bytes')
            baseline[entry['path']] = entry['before']
            files.append(dict(path=entry['path'], sha256=entry['after']))
            native[entry['path']] = target
    generated = {}
    if removed or external or native:
        # Keep the runtime identity honest after dependency removal, while
        # downloading no unchanged Python or native engine components.
        old_id = (installed / "app/runtime.id").read_text().strip()
        runtime_id = hashlib.sha256((old_id + '\nremoved:' + '\n'.join(sorted(
            path.relative_to(installed.resolve()).as_posix() for path in removed)) +
            '\nadded:' + json.dumps(external, sort_keys=True) + '\n' + revision).encode()).hexdigest()
        generated["app/runtime.id"] = (runtime_id + "\n").encode("ascii")
        generated["app/release_manifest.txt"] = (
            f"Lens2Mesh test candidate\nSource: {revision}\nRuntime ID: {runtime_id}\n"
            "Runtime change: explicit reviewed removals/additional neural DLLs; no Python/engine replacement\n").encode("utf-8")
        for target, data in generated.items():
            files.append({"path": target, "sha256": hashlib.sha256(data).hexdigest()})
    if not files:
        raise ValueError("Candidate has no changed installed components")
    # Keep candidate provenance current for app-only iterations too. Native
    # runtime identity stays stable when only application resources are changed.
    runtime_id = (generated.get('app/runtime.id') or
                  (installed / 'app/runtime.id').read_bytes()).decode('ascii').strip()
    generated['app/release_manifest.txt'] = (
        f'Lens2Mesh test candidate\nSource: {revision}\nRuntime ID: {runtime_id}\n'
        'Application components bound to the incremental patch manifest.\n'
        'Native UTF-8 resource-only changes and dependency changes are explicit in the manifest.\n').encode('utf-8')
    target = 'app/release_manifest.txt'
    if engine_only:
        baseline[target] = digest(installed/target)
    files = [entry for entry in files if entry['path'] != target]
    files.append({'path': target, 'sha256': hashlib.sha256(generated[target]).hexdigest()})
    manifest = {"schema": 1, "candidate": revision,
                "baseline_installer_sha256": "059c81c30479f6c839fcb643f7527a73af94232505aac33840804834fce25b3f",
                "runtime_id": (installed / "app/runtime.id").read_text().strip(),
                "baseline": baseline, "files": files}
    filename = f"Lens2Mesh_TestPatch_{revision[:12]}.zip"
    archive_path = output / filename
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, indent=2))
        archive.write(source / "packaging/apply_patch.py", "apply_patch.py")
        archive.write(source / 'packaging/reviewed-qt-removals.json', 'reviewed-qt-removals.json')
        archive.write(source / 'packaging/reviewed-engine-patches.json', 'reviewed-engine-patches.json')
        if external:
            for helper in ('packaging/neural_runtime.py', 'packaging/neural-runtime-assets.json', 'tools/prepare_engine.py'):
                archive.write(source / helper, helper)
        for entry in files:
            if entry.get("remove"):
                continue
            if entry in external:
                continue  # Official pinned archives are fetched by the update bootstrap.
            if entry['path'] in native:
                archive.write(native[entry['path']], entry['path'])
            elif entry["path"] in generated:
                archive.writestr(entry["path"], generated[entry["path"]])
            else:
                archive.write(source / entry["path"][4:], entry["path"])
    sha = digest(archive_path)
    (output / (filename + ".sha256")).write_text(f"{sha} *{filename}\n", encoding="ascii")
    (output / "patch-summary.json").write_text(json.dumps({
        "candidate": revision, "archive": filename, "sha256": sha,
        "bytes": archive_path.stat().st_size, "files": files,
        "unchanged_python_and_engines": not bool(qt), "removed_dependency": bool(removed),
        "python_engine_replacement": False, "removed_qt_files": len(qt), "setup_built": False,
        "added_neural_runtime": bool(external), "neural_runtime_path": RESOURCE if external else None,
    }, indent=2), encoding="utf-8")
    return archive_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--with-neural-runtime", action='store_true')
    parser.add_argument("--with-engine-utf8", action='store_true')
    parser.add_argument("--engine-only", action='store_true')
    args = parser.parse_args()
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=args.source).decode().strip()
    if args.revision != actual:
        raise ValueError("Candidate revision differs from checkout")
    if subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], cwd=args.source):
        raise ValueError("Candidate must use committed sources")
    print(build(args.source, args.baseline, args.output, args.revision, args.with_neural_runtime, args.with_engine_utf8, args.engine_only))
