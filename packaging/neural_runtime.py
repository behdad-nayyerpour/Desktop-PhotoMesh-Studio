"""Prepare exact NVIDIA redistributable DLLs, at build/update time only.

No system installation, driver changes, pip or SDK tools. The same preparation
is used by Setup staging and the incremental updater before app mutation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from prepare_engine import acquire, digest  # noqa: E402

RESOURCE = 'app/photomesh/resources/neural-cuda12'


def specification():
    return json.loads((ROOT / 'packaging/neural-runtime-assets.json').read_text(encoding='utf-8'))


def runtime_manifest():
    return (json.dumps(specification(), indent=2) + '\n').encode('utf-8')


def runtime_files():
    names = [item['name'] for asset in specification()['assets'] for item in asset['files']]
    if any(Path(name).name != name or '\\' in name or ':' in name or not name.endswith('.dll') for name in names):
        raise ValueError('Unsafe runtime DLL name')
    if len(set(name.casefold() for name in names)) != len(names):
        raise ValueError('Duplicate runtime DLL')
    result = [{'path': RESOURCE + '/' + item['name'], 'sha256': item['sha256']}
              for asset in specification()['assets'] for item in asset['files']]
    result.append({'path': RESOURCE + '/runtime.json',
                   'sha256': hashlib.sha256(runtime_manifest()).hexdigest()})
    return result


def prepare(output, cache, offline=False, selected=None):
    output = Path(output)
    if output.exists():
        raise ValueError('Choose a fresh neural runtime stage: ' + str(output))
    # Authenticate every archive before creating the candidate runtime folder.
    names = ({Path(item['path']).name for item in runtime_files()} if selected is None else set(selected))
    allowed = {Path(item['path']).name for item in runtime_files()}
    if not names or not names <= allowed:
        raise ValueError('Unreviewed or empty neural runtime selection')
    archives = [(asset, acquire(asset, Path(cache), offline))
                for asset in specification()['assets'] if any(item['name'] in names for item in asset['files'])]
    output.mkdir(parents=True)
    for asset, path in archives:
        prefix = asset['name'][:-4] + '/'
        with zipfile.ZipFile(path) as archive:
            if hashlib.sha256(archive.read(prefix + 'LICENSE')).hexdigest() != asset['license_sha256']:
                raise ValueError('Runtime license differs from reviewed official bytes')
            for item in asset['files']:
                name = item['name']
                if name not in names:
                    continue
                if Path(name).name != name or not name.endswith('.dll'):
                    raise ValueError('Unsafe runtime DLL name')
                target = output / name
                with archive.open(prefix + 'bin/' + name) as source, target.open('xb') as destination:
                    shutil.copyfileobj(source, destination, 1024 * 1024)
                if target.stat().st_size != item['bytes'] or digest(target) != item['sha256']:
                    raise ValueError('Redistributable DLL differs: ' + name)
    if 'runtime.json' in names:
        (output / 'runtime.json').write_bytes(runtime_manifest())
    return output


def prepare_payload(payload, cache, offline=False):
    payload = Path(payload).resolve(strict=True)
    manifest = json.loads((payload / 'manifest.json').read_text(encoding='utf-8'))
    expected = {item['path']: item['sha256'] for item in runtime_files()}
    declared = {item['path']: item['sha256'] for item in manifest['files'] if item['path'].startswith(RESOURCE+'/')}
    if not declared or any(expected.get(path) != sha for path, sha in declared.items()):
        raise ValueError('Patch does not declare the exact reviewed neural runtime')
    return prepare(payload / RESOURCE, cache, offline, {Path(path).name for path in declared})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument('--output', type=Path)
    target.add_argument('--payload', type=Path)
    parser.add_argument('--cache', type=Path)
    parser.add_argument('--offline', action='store_true')
    parser.add_argument('--descriptor-only', action='store_true', help='Write only the small optional-runtime descriptor; download no DLLs')
    args = parser.parse_args()
    cache = args.cache or ((args.payload or args.output).resolve().parent / 'neural-runtime-downloads')
    if args.payload:
        if args.descriptor_only:
            parser.error('--descriptor-only requires --output')
        prepare_payload(args.payload, cache, args.offline)
    else:
        prepare(args.output, cache, args.offline, {'runtime.json'} if args.descriptor_only else None)
