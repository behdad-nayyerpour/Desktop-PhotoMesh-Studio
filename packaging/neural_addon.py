"""Install only authenticated optional GPU DLLs with the shared rollback journal."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import sys

import apply_patch as updater


def addon_files(specification):
    names = set()
    result = []
    for asset in specification['assets']:
        for entry in asset['files']:
            name = entry['name']
            if (Path(name).name != name or '/' in name or '\\' in name or ':' in name
                    or not name.endswith('.dll') or name.casefold() in names):
                raise ValueError('Unsafe or duplicate optional DLL')
            names.add(name.casefold())
            result.append(dict(path='app/photomesh/resources/neural-cuda12/' + name,
                               sha256=entry['sha256']))
    data = (json.dumps(specification, indent=2) + '\n').encode('utf-8')
    result.append(dict(path='app/photomesh/resources/neural-cuda12/runtime.json',
                       sha256=hashlib.sha256(data).hexdigest()))
    return result


def make_manifest(root, payload, revision, specification):
    root, payload = root.resolve(strict=True), payload.resolve(strict=True)
    init = updater.managed(root, 'app/photomesh/__init__.py')
    values = {}
    for node in ast.parse(init.read_text(encoding='utf-8')).body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    values[target.id] = node.value.value
    if values.get('APP_NAME') != 'Lens2Mesh' or values.get('APP_VERSION') != '1.0.5':
        raise ValueError('Select the existing Lens2Mesh 1.0.5 installation folder')
    identity = updater.managed(root, 'app/runtime.id')
    runtime_id = identity.read_text(encoding='utf-8').strip()
    if len(runtime_id) != 64 or any(c not in '0123456789abcdef' for c in runtime_id):
        raise ValueError('Installed runtime identity is invalid')
    expected = addon_files(specification)
    baseline = {'app/photomesh/__init__.py': updater.digest(init),
                'app/runtime.id': updater.digest(identity)}
    files = []
    for entry in expected:
        target = updater.managed(root, entry['path'])
        source = updater.managed(payload, entry['path'])
        if not source.is_file() or updater.digest(source) != entry['sha256']:
            raise ValueError('Add-on payload checksum mismatch: ' + entry['path'])
        if target.exists():
            if not target.is_file() or updater.digest(target) != entry['sha256']:
                raise ValueError('Different GPU runtime already exists; no files replaced: ' + entry['path'])
            continue
        files.append(entry)
    return dict(schema=1, candidate=revision, runtime_id=runtime_id,
                baseline=baseline, files=files)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--payload', required=True, type=Path)
    parser.add_argument('--revision', required=True)
    parser.add_argument('--log', type=Path)
    args = parser.parse_args()
    try:
        root = args.root.resolve(strict=True)
        updater.ensure_closed(root)
        specification = json.loads((args.payload / 'packaging/neural-runtime-assets.json').read_text(encoding='utf-8'))
        manifest = make_manifest(root, args.payload, args.revision, specification)
        # The lock/journal are shared with app-only updates; no pip or driver changes.
        import msvcrt
        with open(root / '.lens2mesh-patch.lock', 'a+b') as lock:
            lock.seek(0)
            if not lock.read(1):
                lock.write(b'0')
                lock.flush()
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            updater.validate_manifest(manifest, root, args.payload)
            if manifest['files']:
                state = updater.apply(root, args.payload, manifest)
                message = 'GPU add-on installed. Backup and rollback: ' + str(state)
            else:
                message = 'The exact GPU add-on is already installed; no files were changed.'
        if args.log:
            args.log.write_text(message, encoding='utf-8')
        print(message)
    except Exception as error:
        message = 'GPU add-on stopped: ' + str(error)
        if args.log:
            args.log.write_text(message, encoding='utf-8')
        print(message, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(errors='backslashreplace')
    sys.exit(main())
