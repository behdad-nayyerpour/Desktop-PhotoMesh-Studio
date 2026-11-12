"""Update delivery tooling while preserving every verified application byte."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile


def repack(archive, expected_sha, updater, revision, output):
    if hashlib.sha256(archive.read_bytes()).hexdigest() != expected_sha:
        raise ValueError("Original accepted archive checksum mismatch")
    if len(revision) != 40 or any(c not in "0123456789abcdef" for c in revision):
        raise ValueError("Updater must be bound to an exact source commit")
    if output.exists():
        raise ValueError("Choose a new output archive; accepted evidence must remain intact")
    with zipfile.ZipFile(archive) as source:
        manifest = json.loads(source.read("manifest.json"))
        manifest["updater_revision"] = revision
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as target:
            for info in source.infolist():
                data = source.read(info.filename)
                if info.filename == "apply_patch.py":
                    data = updater.read_bytes()
                elif info.filename == "manifest.json":
                    data = json.dumps(manifest, indent=2).encode("utf-8")
                target.writestr(info, data)
        with zipfile.ZipFile(output) as target:
            for info in source.infolist():
                if info.filename not in ("manifest.json", "apply_patch.py"):
                    if source.read(info.filename) != target.read(info.filename):
                        raise AssertionError("Accepted application bytes changed during tooling repack")
            updated = json.loads(target.read("manifest.json"))
            original = json.loads(source.read("manifest.json"))
            updated.pop("updater_revision")
            if updated != original:
                raise AssertionError("Application manifest changed during tooling repack")
    return {"candidate": manifest["candidate"], "updater_revision": revision,
            "archive": output.name, "bytes": output.stat().st_size,
            "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            "application_bytes_unchanged": True, "setup_built": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root).decode().strip()
    if subprocess.check_output(["git", "status", "--porcelain", "--", "packaging/apply_patch.py"], cwd=root):
        raise ValueError("Commit the updater before repacking")
    result = repack(args.archive, args.expected_sha, root / "packaging/apply_patch.py", revision, args.output)
    args.output.with_suffix(".summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    args.output.with_suffix(".zip.sha256").write_text(result["sha256"] + " *" + args.output.name + "\n", encoding="ascii")
    print(json.dumps(result))
