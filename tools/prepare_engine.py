"""Prepare pinned offline engines at build time; never imported by the app."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def acquire(asset, cache, offline=False):
    cache.mkdir(parents=True, exist_ok=True)
    target = cache / (asset["sha256"][:16] + "-" + asset["name"])
    if target.is_file() and digest(target) == asset["sha256"]:
        return target
    if offline:
        raise ValueError("Verified offline build asset missing: " + asset["name"])
    temp = target.with_suffix(target.suffix + ".part")
    print("Downloading verified build asset: " + asset["name"], flush=True)
    try:
        request = urllib.request.Request(asset["url"], headers={"User-Agent":"PhotoMesh-Studio-Builder"})
        with urllib.request.urlopen(request, timeout=120) as src, temp.open("wb") as dst:
            shutil.copyfileobj(src, dst, 1024*1024)
        if digest(temp) != asset["sha256"]:
            raise ValueError("SHA256 mismatch: " + asset["name"])
        os.replace(temp, target)
    finally:
        temp.unlink(missing_ok=True)
    return target


def safe_extract(archive, target):
    target.mkdir(parents=True, exist_ok=False)
    root = target.resolve()
    with zipfile.ZipFile(archive) as zipfile_:
        if sum(entry.file_size for entry in zipfile_.infolist()) > 4*1024**3:
            raise ValueError("Unexpectedly large engine archive")
        for entry in zipfile_.infolist():
            name = entry.filename.replace("\\","/")
            destination = (root / name).resolve()
            if ":" in name or not destination.is_relative_to(root) or stat.S_ISLNK(entry.external_attr >> 16):
                raise ValueError("Unsafe engine archive entry")
        zipfile_.extractall(root)
    if not (target/"bin"/"colmap.exe").is_file():
        raise ValueError("Engine archive does not contain bin/colmap.exe")


def prepare(output, cache, cpu_only=False, offline=False):
    assets=json.loads((ROOT/"packaging"/"engine-assets.json").read_text(encoding="utf-8"))
    output=Path(output).resolve()
    output.mkdir(parents=True,exist_ok=True)
    weights={item["name"]:acquire(item,cache,offline) for item in assets["models"]}
    result=[]
    for key in (["cpu"] if cpu_only else ["cuda","cpu"]):
        folder=output/("colmap" if key=="cuda" else "colmap-cpu")
        if folder.exists():
            raise ValueError("Engine destination already exists; choose a fresh build stage: "+str(folder))
        safe_extract(acquire(assets["windows"][key],cache,offline),folder)
        models=folder/"models"; models.mkdir()
        for name,source in weights.items():
            shutil.copyfile(source,models/name)
        manifest={"version":assets["version"],"cuda":key=="cuda","ceres_cuda":False,
                  "minimum_driver":13020 if key=="cuda" else 0,
                  "minimum_cc":75 if key=="cuda" else 0,
                  "models":{item["name"]:item["sha256"] for item in assets["models"]}}
        (folder/"photomesh-engine.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
        result.append(str(folder))
    print("Offline engines prepared: "+", ".join(result),flush=True)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",required=True)
    parser.add_argument("--cache",default=str(ROOT/".engine-download-cache"))
    parser.add_argument("--cpu-only",action="store_true")
    parser.add_argument("--offline",action="store_true")
    args=parser.parse_args()
    prepare(args.output,Path(args.cache),args.cpu_only,args.offline)


if __name__=="__main__":
    main()
