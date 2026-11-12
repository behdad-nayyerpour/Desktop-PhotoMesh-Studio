"""Inventory an exact extracted runtime without importing/executing its packages.

Run on a disposable remote runner. This collects evidence, not legal clearance.
"""
import argparse
import hashlib
from importlib import metadata
import json
from pathlib import Path
import zipfile


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(4 << 20), b""):
            h.update(block)
    return h.hexdigest()


def inventory(root, output):
    output.mkdir(parents=True, exist_ok=True)
    files = []
    packages = []
    evidence = []
    site = root / "python/Lib/site-packages"
    for dist in metadata.distributions(path=[str(site)]):
        meta = dist.metadata
        packages.append({
            "name": meta.get("Name"), "version": dist.version,
            "license": meta.get("License"), "license_expression": meta.get("License-Expression"),
            "classifiers": meta.get_all("Classifier", []),
            "homepage": meta.get("Home-page"), "project_urls": meta.get_all("Project-URL", []),
            "requires": meta.get_all("Requires-Dist", []),
        })
    for path in sorted(root.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        relative = path.relative_to(root).as_posix()
        files.append({"path": relative, "bytes": path.stat().st_size, "sha256": sha256(path)})
        name = path.name.casefold()
        if any(token in name for token in ("license", "licence", "notice", "copyright", "copying")):
            evidence.append(path)
        elif name in ("metadata", "direct_url.json", "photomesh-engine.json", "runtime.lock"):
            evidence.append(path)
    with zipfile.ZipFile(output / "license-evidence.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for path in evidence:
            archive.write(path, path.relative_to(root).as_posix())
    report = {"scope": "Exact extracted installer runtime; no package imports",
              "legal_clearance": False, "files": files,
              "packages": sorted(packages, key=lambda p: (p["name"] or "").casefold()),
              "remaining_review": [
                  "Review native engine/DLL provenance and corresponding source obligations",
                  "Verify Qt LGPL replacement/relinking and version-specific notices",
                  "Verify NVIDIA CUDA redistribution list and neural weight permissions",
                  "Inspect GPL-only packages and transitive imports before removal",
                  "Audit corrected candidate separately; metadata alone is not clearance",
              ]}
    (output / "inventory.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = inventory(args.root.resolve(strict=True), args.output.resolve())
    print(f"Inventoried {len(report['files'])} files and {len(report['packages'])} distributions; review required.")
