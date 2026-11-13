"""Check staged package versions against the exact audited Windows wheel lock.

This verifies metadata, not a replacement for byte inventories or pip's wheel
hash verification. It neither installs packages nor imports native extensions.
"""
import argparse
from importlib import metadata
import json
from pathlib import Path
import re
import sys


def normalized(name):
    return re.sub(r'[-_.]+', '-', name).lower()


def verify(root, lock):
    expected = {}
    for line in lock.read_text(encoding='utf-8').splitlines():
        if not line or line.startswith(('#', '--')):
            continue
        match = re.fullmatch(r'([A-Za-z0-9_.-]+)==([^ ]+) --hash=sha256:([0-9a-f]{64})', line)
        if not match:
            raise ValueError('Invalid hashed runtime pin: '+line)
        name, version, _hash = match.groups()
        key = normalized(name)
        if key in expected:
            raise ValueError('Duplicate runtime pin: '+key)
        expected[key] = version
    paths = [root/'python/Lib/site-packages', root/'app/photomesh/_vendor']
    found = {}
    for dist in metadata.distributions(path=list(map(str, paths))):
        name = normalized(dist.metadata['Name'])
        if name in found:
            raise ValueError('Duplicate installed distribution: '+name)
        found[name] = dist.version
    missing = sorted(set(expected)-set(found))
    changed = {key: [expected[key], found[key]] for key in expected.keys() & found.keys() if expected[key] != found[key]}
    unexpected = sorted(set(found)-set(expected))
    if missing or changed or unexpected:
        raise ValueError(json.dumps(dict(missing=missing, changed=changed, unexpected=unexpected)))
    return dict(packages=len(found), versions_match=True, wheel_hashes_enforced_by='pip --require-hashes --no-deps',
                byte_identity='separate installed inventory and primary upstream comparison')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--lock', type=Path, default=Path(__file__).with_name('requirements-runtime-win313.lock'))
    args = parser.parse_args()
    if sys.platform != 'win32' or sys.version_info[:2] != (3, 13) or sys.maxsize <= 2**32:
        raise RuntimeError('This binary lock requires Windows x64 CPython3.13')
    print(json.dumps(verify(args.root, args.lock), indent=2))
