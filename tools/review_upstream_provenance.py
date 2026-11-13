"""Resolve exact public wheel origins and native versions on a disposable runner."""
import argparse
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import subprocess
import urllib.request
import zipfile


def get_json(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'Lens2Mesh-provenance-review'})
    with urllib.request.urlopen(request, timeout=90) as response:
        return json.load(response)


def review(root, output):
    from packaging.tags import sys_tags
    from packaging.utils import canonicalize_name, parse_wheel_filename
    import pefile
    output.mkdir(parents=True, exist_ok=True)
    supported = {tag: i for i, tag in enumerate(sys_tags())}
    site = root/'python/Lib/site-packages'
    versions = {canonicalize_name(d.metadata['Name']): d.version for d in metadata.distributions(path=[str(site)])
                if d.metadata.get('Name') and canonicalize_name(d.metadata['Name']) != 'plyfile'}
    versions.update(laspy='2.6.1', lazrs='0.7.0')
    packages, wheel_hashes, wheel_owners = [], {}, {}
    for name, version in sorted(versions.items()):
        print('Resolving '+name+'=='+version, flush=True)
        info = get_json(f'https://pypi.org/pypi/{name}/{version}/json')
        choices = []
        for file in info['urls']:
            if file['packagetype'] != 'bdist_wheel' or file.get('yanked'):
                continue
            try:
                tags = parse_wheel_filename(file['filename'])[3]
            except ValueError:
                continue
            ranks = [supported[t] for t in tags if t in supported]
            if ranks:
                choices.append((min(ranks), file['filename'], file))
        if not choices:
            raise ValueError('No exact supported binary wheel for '+name+'=='+version)
        file = min(choices, key=lambda row: row[:2])[2]
        packages.append(dict(name=name, version=version, wheel=file['filename'], url=file['url'],
            sha256=file['digests']['sha256'], bytes=file['size'],
            license=info['info'].get('license_expression') or info['info'].get('license'),
            sources=info['info'].get('project_urls'), requires=info['info'].get('requires_dist')))
        if name.startswith('pyside6') or name == 'shiboken6':
            path = output/file['filename']
            urllib.request.urlretrieve(file['url'], path)
            if hashlib.file_digest(path.open('rb'), 'sha256').hexdigest() != file['digests']['sha256']:
                raise ValueError('Wheel hash mismatch')
            with zipfile.ZipFile(path) as archive:
                for member in archive.namelist():
                    if member.endswith('/') or not member.startswith(('PySide6/', 'shiboken6/')):
                        continue
                    # Binary and resource byte identity, not a package-name inference.
                    if Path(member).suffix.lower() not in ('.dll', '.pyd', '.exe', '.qml', '.rcc', '.pak', '.dat'):
                        continue
                    digest = hashlib.sha256(archive.read(member)).hexdigest()
                    wheel_hashes.setdefault(member, set()).add(digest)
                    wheel_owners.setdefault(member, []).append(name+'=='+version)
            path.unlink()  # Only the disposable downloaded wheel; evidence kept below.
    (output/'python-origins.json').write_text(json.dumps(packages, indent=2), encoding='utf-8')
    lock = ['# Windows x64 CPython3.13 exact published runtime plus audited app-vendor dependencies.',
            '# Generated from official PyPI version metadata; binary-only, no dependency resolution.',
            '--only-binary=:all:']
    for item in packages:
        lock.append(f"{item['name']}=={item['version']} --hash=sha256:{item['sha256']}")
    (output/'requirements-runtime-win313.lock').write_text('\n'.join(lock)+'\n', encoding='utf-8')
    qt = []
    for path in site.rglob('*'):
        if not path.is_file():
            continue
        relative = path.relative_to(site).as_posix()
        if relative not in wheel_hashes:
            continue
        digest = hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()
        qt.append(dict(path=relative, sha256=digest, official_match=digest in wheel_hashes[relative],
                       owners=wheel_owners[relative]))
    (output/'qt-official-byte-comparison.json').write_text(json.dumps(qt, indent=2), encoding='utf-8')
    native = []
    for path in (root/'tools').rglob('*'):
        if not path.is_file() or path.suffix.lower() not in ('.exe', '.dll') or path.name.endswith('_test.exe'):
            continue
        record = dict(path=path.relative_to(root).as_posix(), version={}, sha256=hashlib.file_digest(path.open('rb'), 'sha256').hexdigest())
        try:
            pe = pefile.PE(str(path), fast_load=True); pe.parse_data_directories(directories=[2])
            for group in getattr(pe, 'FileInfo', []):
                for entry in group:
                    for table in getattr(entry, 'StringTable', []):
                        for key, value in table.entries.items():
                            record['version'][key.decode('utf-8', 'replace')] = value.decode('utf-8', 'replace')
            pe.close()
        except pefile.PEFormatError as error:
            record['error'] = str(error)
        if path.name.lower() in ('colmap.exe', 'glomap.exe'):
            try:
                environment = dict(os.environ)
                environment['PATH'] = os.pathsep.join([str(path.parent), str(path.parent.parent/'lib'), environment.get('PATH', '')])
                result = subprocess.run([str(path), '-h'], capture_output=True, timeout=30, env=environment)
                record['help'] = (result.stdout+result.stderr).decode('utf-8', 'replace')[:6000]
                record['help_exit_code'] = result.returncode
            except subprocess.TimeoutExpired:
                record['help_error'] = 'timed out'
        native.append(record)
    (output/'native-version-origins.json').write_text(json.dumps(native, indent=2), encoding='utf-8')
    summary = dict(python_packages=len(packages), qt_compared=len(qt), qt_mismatches=[r for r in qt if not r['official_match']],
                   native_files=len(native))
    (output/'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2))


def native_release_comparison(root, output):
    """Record byte identity against primary native archives, not a version guess."""
    output.mkdir(parents=True, exist_ok=True)
    releases = [
        ('colmap-legacy', 'https://github.com/colmap/colmap/releases/download/3.8/COLMAP-3.8-windows-cuda.zip'),
        ('glomap', 'https://github.com/colmap/glomap/releases/download/1.2.0/glomap-x64-windows-nocuda.zip'),
        ('colmap-cpu', 'https://github.com/colmap/colmap/releases/download/4.2.1/colmap-x64-windows-cpu.zip'),
        ('colmap', 'https://github.com/colmap/colmap/releases/download/4.2.1/colmap-x64-windows-cuda.zip'),
    ]
    result = []
    for group, url in releases:
        # Modern assets have fixed primary hashes in engine-assets.json. Preserve
        # the original URLs there; do not guess a release's asset spelling.
        if group in ('colmap-cpu', 'colmap'):
            print('Modern engine provenance is retained by the pinned engine manifest: '+group, flush=True)
            continue
        print('Comparing native primary archive: '+url, flush=True)
        archive_path = output/(group+'-official.zip')
        urllib.request.urlretrieve(url, archive_path)
        digest = hashlib.file_digest(archive_path.open('rb'), 'sha256').hexdigest()
        with zipfile.ZipFile(archive_path) as archive:
            origins = {}
            notices = []
            for member in archive.infolist():
                if member.is_dir():
                    continue
                if Path(member.filename).suffix.lower() in ('.dll', '.exe'):
                    sha = hashlib.sha256(archive.read(member)).hexdigest()
                    origins.setdefault(sha, []).append(member.filename)
                elif any(name in Path(member.filename).name.lower() for name in ('license', 'copying', 'notice', 'copyright')):
                    if member.file_size < 2_000_000:
                        destination = output/'native-notices'/group/member.filename
                        if not destination.resolve().is_relative_to((output/'native-notices'/group).resolve()):
                            raise ValueError('Unsafe upstream notice path')
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        destination.write_bytes(archive.read(member)); notices.append(member.filename)
            rows = []
            for path in sorted((root/'tools'/group).rglob('*')):
                if not path.is_file() or path.suffix.lower() not in ('.dll', '.exe'):
                    continue
                sha = hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()
                rows.append(dict(path=path.relative_to(root).as_posix(), sha256=sha, official_members=origins.get(sha, [])))
            result.append(dict(group=group, url=url, sha256=digest, bytes=archive_path.stat().st_size,
                               files=rows, matched=sum(bool(r['official_members']) for r in rows), notices=notices))
        archive_path.unlink()  # Disposable download; exact hash and member mapping retained.
    (output/'native-official-byte-comparison.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps([{k:v for k,v in r.items() if k != 'files'} for r in result], indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    review(args.root.resolve(strict=True), args.output)
    native_release_comparison(args.root.resolve(strict=True), args.output)
