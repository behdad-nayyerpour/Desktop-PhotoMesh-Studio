"""Authenticate every compact installed byte against the published baseline."""
import argparse
import hashlib
import json
from pathlib import Path


def inventory(root):
    result = {}
    for name in ('app', 'python', 'tools'):
        for path in (root / name).rglob('*'):
            if path.is_symlink() or path.is_junction():
                raise ValueError('Linked installed entry: ' + str(path))
            if path.is_file():
                with path.open('rb') as stream:
                    digest = hashlib.file_digest(stream, 'sha256').hexdigest()
                result[path.relative_to(root).as_posix()] = dict(bytes=path.stat().st_size, sha256=digest)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--installed', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source', type=Path, help='Allow only the separately approved documentation updates')
    args = parser.parse_args()
    before = inventory(args.baseline)
    after = inventory(args.installed)
    report = json.loads(args.report.read_text(encoding='utf-8'))
    omissions = {entry['path']: dict(bytes=entry['bytes'], sha256=entry['sha256']) for entry in report['omitted']}
    assert {name: before[name] for name in omissions} == omissions
    expected = {name: item for name, item in before.items() if name not in omissions}
    updated_documentation = []
    if args.source:
        for name in ('README.md', 'UPDATING.md', 'docs/installation.md',
                     'photomesh/resources/manual/Lens2Mesh_1.0.5_Complete_User_Manual.pdf'):
            path = args.source / name
            with path.open('rb') as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            expected['app/' + name] = dict(bytes=path.stat().st_size, sha256=digest)
            updated_documentation.append('app/' + name)
    assert expected == after, dict(missing=sorted(expected.keys() - after.keys()),
                                   unexpected=sorted(after.keys() - expected.keys()),
                                   changed=[name for name in expected.keys() & after.keys() if expected[name] != after[name]])
    for name in omissions:
        assert not (args.installed / name).exists()
    assert len(after) == report['installed_files']
    result = dict(baseline_files=len(before), identical_retained_files=len(after),
                  reviewed_omissions=len(omissions), removed_bytes=report['omitted_bytes'],
                  neural_profile=report.get('neural_profile', 'full'),
                  updated_documentation=updated_documentation, no_retained_runtime_content_changes=True)
    args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))
