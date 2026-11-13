"""Exact, reviewed removal of the replaced PLY dependency from staged runtimes."""
from importlib import metadata
import hashlib
import json
from pathlib import Path
import re


def reviewed_qt_files(root):
    """Only exact, PE-reviewed unused addon bytes; never infer from filenames."""
    root = Path(root).resolve(strict=True)
    plan = json.loads(Path(__file__).with_name('reviewed-qt-removals.json').read_text(encoding='utf-8'))
    result = []
    for record in plan['files']:
        relative = record['path']
        if not relative.startswith('python/Lib/site-packages/PySide6/') or '..' in Path(relative).parts:
            raise ValueError('Qt removal plan escapes reviewed scope')
        path = root/relative
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError('Linked Qt removal target')
        if path.is_file():
            if hashlib.sha256(path.read_bytes()).hexdigest() != record['sha256']:
                raise ValueError('Qt dependency bytes differ from reviewed baseline: '+relative)
            result.append(path)
    return result


def plyfile_files(root):
    root = Path(root).resolve(strict=True)
    site = root / "python/Lib/site-packages"
    distributions = list(metadata.distributions(path=[str(site)]))
    for dist in distributions:
        if any(re.split(r"[\s<>=!~;\[()]", requirement, 1)[0].casefold() == "plyfile"
               for requirement in (dist.requires or [])):
            raise ValueError(f"Review transitive plyfile requirement before removal: {dist.metadata['Name']}")
    paths = []
    for dist in distributions:
        if dist.metadata.get("Name", "").casefold() != "plyfile":
            continue
        if dist.files is None:
            raise ValueError("Cannot remove plyfile without its exact installed RECORD")
        for record in dist.files:
            path = Path(dist.locate_file(record))
            if path.is_symlink() or not path.resolve().is_relative_to(site.resolve()):
                raise ValueError("plyfile RECORD escapes site-packages or contains links")
            if path.is_file():
                relative = path.relative_to(root).as_posix()
                if not re.fullmatch(r"python/Lib/site-packages/(?:plyfile\.py|plyfile/[^:]+|"
                                    r"plyfile-[0-9][^/]*\.dist-info/[^:]+|__pycache__/plyfile\.[^/]+\.pyc)", relative):
                    raise ValueError(f"Unexpected file in plyfile RECORD: {relative}")
                paths.append(path)
    return paths


def clean_staged_runtime(root):
    """Only used on a newly created build stage, before any Setup is compiled."""
    paths = plyfile_files(root) + reviewed_qt_files(root)
    # All declarations are checked before the first managed file is removed.
    for path in paths:
        path.unlink()
    return len(paths)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, required=True)
    args = parser.parse_args()
    print(f"Removed {clean_staged_runtime(args.stage)} replaced dependency files from stage")
