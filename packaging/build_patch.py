"""Build a delta against an exact disposable installed baseline (no full Setup)."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

from runtime_dependencies import plyfile_files


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(source, installed, output, revision):
    output.mkdir(parents=True, exist_ok=True)
    baseline = {}
    for path in (installed / "app").rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            baseline[path.relative_to(installed).as_posix()] = digest(path)
    # Application sources and reviewed resources only. Never include arbitrary
    # untracked files, personal projects or the reusable Python/engine runtime.
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=source).decode().split("\0")
    files = []
    # Never blindly delete a copied environment's packages. Only this exact
    # distribution's installed RECORD files are considered, and declared
    # transitive requirements block removal for manual review.
    ply = plyfile_files(installed)
    for path in ply:
        target = path.relative_to(installed.resolve()).as_posix()
        baseline[target] = digest(path)
        files.append({"path": target, "sha256": None, "remove": True})
    for relative in tracked:
        path = source / relative
        allowed = (relative.startswith("photomesh/")
                   or relative in ("main.py", "requirements.txt", "packaging/fix_shortcut_icon.ps1"))
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
    generated = {}
    if ply:
        # Keep the runtime identity honest after dependency removal, while
        # downloading no unchanged Python or native engine components.
        old_id = (installed / "app/runtime.id").read_text().strip()
        runtime_id = hashlib.sha256((old_id + "\nremoved:plyfile\n" + revision).encode()).hexdigest()
        generated["app/runtime.id"] = (runtime_id + "\n").encode("ascii")
        generated["app/release_manifest.txt"] = (
            f"Lens2Mesh test candidate\nSource: {revision}\nRuntime ID: {runtime_id}\n"
            "Runtime change: removed plyfile; no Python/engine replacement\n").encode("utf-8")
        for target, data in generated.items():
            files.append({"path": target, "sha256": hashlib.sha256(data).hexdigest()})
    if not files:
        raise ValueError("Candidate has no changed installed components")
    manifest = {"schema": 1, "candidate": revision,
                "baseline_installer_sha256": "059c81c30479f6c839fcb643f7527a73af94232505aac33840804834fce25b3f",
                "runtime_id": (installed / "app/runtime.id").read_text().strip(),
                "baseline": baseline, "files": files}
    filename = f"Lens2Mesh_TestPatch_{revision[:12]}.zip"
    archive_path = output / filename
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, indent=2))
        archive.write(source / "packaging/apply_patch.py", "apply_patch.py")
        for entry in files:
            if entry.get("remove"):
                continue
            if entry["path"] in generated:
                archive.writestr(entry["path"], generated[entry["path"]])
            else:
                archive.write(source / entry["path"][4:], entry["path"])
    sha = digest(archive_path)
    (output / (filename + ".sha256")).write_text(f"{sha} *{filename}\n", encoding="ascii")
    (output / "patch-summary.json").write_text(json.dumps({
        "candidate": revision, "archive": filename, "sha256": sha,
        "bytes": archive_path.stat().st_size, "files": files,
        "unchanged_python_and_engines": True, "removed_dependency": bool(ply), "setup_built": False,
    }, indent=2), encoding="utf-8")
    return archive_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=args.source).decode().strip()
    if args.revision != actual:
        raise ValueError("Candidate revision differs from checkout")
    if subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], cwd=args.source):
        raise ValueError("Candidate must use committed sources")
    print(build(args.source, args.baseline, args.output, args.revision))
