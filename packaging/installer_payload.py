"""Compact Setup storage without relocating or changing installed runtime files.

Only reviewed Python HTML documentation and native debug symbols are omitted.
Identical files share one Inno source entry but keep separate installed paths.
"""
import argparse
import filecmp
import hashlib
import json
from pathlib import Path


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def allowed_omission(name):
    return (name.startswith('python/Doc/') or
            (name.startswith(('tools/colmap/plugins/', 'tools/colmap-cpu/plugins/'))
             and name.endswith('.pdb')))


def quote(value):
    if any(character in str(value) for character in ('"', '\r', '\n')):
        raise ValueError('Unsupported installer path: ' + str(value))
    return '"' + str(value) + '"'


def generate(stage, output, report, plan):
    stage = Path(stage).resolve(strict=True)
    if output.resolve().is_relative_to(stage) or report.resolve().is_relative_to(stage):
        raise ValueError('Write installer metadata outside the stage')
    entries = json.loads(Path(plan).read_text(encoding='utf-8'))['files']
    omissions = {}
    for entry in entries:
        name = entry['path']
        if (not allowed_omission(name) or '..' in name.split('/') or '\\' in name
                or ':' in name or name in omissions):
            raise ValueError('Unreviewed omission: ' + name)
        omissions[name] = entry
    files = []
    directories = []
    for name in ('app', 'python', 'tools'):
        folder = stage / name
        if (not folder.is_dir() or folder.is_symlink() or folder.is_junction()
                or not folder.resolve().is_relative_to(stage)):
            raise ValueError('Missing or linked stage root: ' + name)
        for path in sorted(folder.rglob('*')):
            if path.is_symlink() or path.is_junction() or not path.resolve().is_relative_to(stage):
                raise ValueError('Linked stage entry: ' + str(path))
            relative = path.relative_to(stage).as_posix()
            if path.is_dir():
                directories.append(relative)
            elif path.is_file():
                files.append(dict(path=relative, bytes=path.stat().st_size, sha256=digest(path)))
            else:
                raise ValueError('Unsupported stage entry: ' + relative)
    present = {item['path']: item for item in files}
    for name, expected in omissions.items():
        if name in present and present[name] != expected:
            raise ValueError('Reviewed omission bytes differ: ' + name)
    # Generate everything in memory; never edit the source runtime.
    canonical = {}
    aliases = []
    kept = []
    removed = []
    lines = ['; Generated from SHA256 and exact duplicate-byte comparisons.', '[Dirs]']
    for name in directories:
        lines.append('Name: ' + quote('{app}\\' + name.replace('/', '\\')))
    lines.append('[Files]')
    for item in files:
        name = item['path']
        if name in omissions:
            removed.append(item)
            continue
        key = (item['bytes'], item['sha256'])
        source = canonical.setdefault(key, name)
        if source != name:
            if not filecmp.cmp(stage / source, stage / name, shallow=False):
                raise ValueError('Duplicate bytes differ: ' + name)
            aliases.append(dict(path=name, source=source, bytes=item['bytes'], sha256=item['sha256']))
        destination = Path(name)
        lines.append('Source: ' + quote(stage / source) + '; DestDir: ' +
                     quote('{app}\\' + destination.parent.as_posix().replace('/', '\\')) +
                     '; DestName: ' + quote(destination.name) + '; Flags: ignoreversion')
        kept.append(item)
    result = dict(schema=1, scope='installer storage only; installed duplicate files remain separate',
                  original_files=len(files), installed_files=len(kept),
                  original_bytes=sum(item['bytes'] for item in files),
                  omitted_bytes=sum(item['bytes'] for item in removed),
                  duplicate_storage_bytes=sum(item['bytes'] for item in aliases),
                  omitted=removed, aliases=aliases, installed=kept)
    output.parent.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True, exist_ok=True)
    output.write_text('\n'.join(lines) + '\n', encoding='utf-8-sig')
    report.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--plan', type=Path, default=Path(__file__).with_name('reviewed-installer-omissions.json'))
    args = parser.parse_args()
    result = generate(args.stage, args.output, args.report, args.plan)
    print(json.dumps({key: result[key] for key in ('original_files', 'installed_files', 'omitted_bytes', 'duplicate_storage_bytes')}, indent=2))
