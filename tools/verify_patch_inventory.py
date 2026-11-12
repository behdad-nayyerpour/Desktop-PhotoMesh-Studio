"""Compare the entire remote runtime against independently collected hashes."""
import argparse
import json
from pathlib import Path


def verify(before, after, manifest):
    expected = {entry["path"]: entry["sha256"] for entry in before["files"]}
    observed = {entry["path"]: entry["sha256"] for entry in after["files"]}
    for entry in manifest["files"]:
        # Python caches are intentionally absent from distribution inventories.
        if "__pycache__" in entry["path"].split("/"):
            continue
        if entry.get("remove"):
            expected.pop(entry["path"], None)
        else:
            expected[entry["path"]] = entry["sha256"]
    differing = [p for p in set(expected) | set(observed) if expected.get(p) != observed.get(p)]
    if differing:
        raise ValueError("Unexpected runtime changes: " + ", ".join(sorted(differing)[:20]))
    print(f"Exact candidate inventory verified: {len(observed)} files; unchanged Python/engines preserved.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    verify(*(json.loads(path.read_text(encoding="utf-8")) for path in (args.before, args.after, args.manifest)))
