"""Compact storage preserves installed bytes and rejects unsafe exclusions."""
import importlib.util
import json
from pathlib import Path
import re
import shutil

import pytest

spec = importlib.util.spec_from_file_location('installer_payload', Path(__file__).resolve().parents[1] / 'packaging/installer_payload.py')
payload = importlib.util.module_from_spec(spec)
spec.loader.exec_module(payload)


def fixture(tmp_path):
    stage = tmp_path / 'stage فارسی'
    data = {'app/main.py': b'print("Lens2Mesh")\n',
            'app/LICENSE': b'license stays',
            'python/Lib/module.py': b'runtime stays',
            'python/Doc/html/index.html': b'optional offline Python reference',
            'tools/colmap/bin/shared.dll': b'exact common binary',
            'tools/colmap-cpu/bin/shared.dll': b'exact common binary',
            'tools/colmap/plugins/platforms/qwindows.pdb': b'debug symbols only'}
    for name, content in data.items():
        path = stage / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    plan = tmp_path / 'plan.json'
    omitted = [dict(path=name, bytes=len(content), sha256=payload.digest(stage / name))
               for name, content in data.items() if payload.allowed_omission(name)]
    plan.write_text(json.dumps(dict(files=omitted)))
    return stage, plan, data


def test_compact_include_reconstructs_original_runtime_with_reviewed_omissions(tmp_path):
    stage, plan, data = fixture(tmp_path)
    include, report = tmp_path / 'files.iss', tmp_path / 'report.json'
    result = payload.generate(stage, include, report, plan)
    installed = tmp_path / 'installed'
    rows = re.findall(r'^Source: "([^"]+)"; DestDir: "\{app\}\\([^"]+)"; DestName: "([^"]+)";', include.read_text(encoding='utf-8-sig'), re.M)
    assert len(rows) == result['installed_files']
    for source, directory, name in rows:
        destination = installed / directory.replace('\\', '/') / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    actual = {p.relative_to(installed).as_posix(): p.read_bytes() for p in installed.rglob('*') if p.is_file()}
    assert actual == {name: content for name, content in data.items() if not payload.allowed_omission(name)}
    assert {p.relative_to(stage).as_posix(): p.read_bytes() for p in stage.rglob('*') if p.is_file()} == data
    assert len(result['aliases']) == 1
    assert result['duplicate_storage_bytes'] == len(b'exact common binary')


def test_changed_reviewed_file_fails_before_writing_include(tmp_path):
    stage, plan, _ = fixture(tmp_path)
    (stage / 'python/Doc/html/index.html').write_text('different bytes')
    output = tmp_path / 'files.iss'
    with pytest.raises(ValueError, match='bytes differ'):
        payload.generate(stage, output, tmp_path / 'report.json', plan)
    assert not output.exists()


@pytest.mark.parametrize('name', ['python/Lib/module.py', 'app/LICENSE', 'tools/colmap/bin/shared.dll', '../outside', 'python/Doc/../../app/main.py'])
def test_unreviewed_runtime_or_traversal_omission_is_rejected(tmp_path, name):
    stage, plan, _ = fixture(tmp_path)
    plan.write_text(json.dumps(dict(files=[dict(path=name, bytes=1, sha256='0' * 64)])))
    with pytest.raises(ValueError, match='Unreviewed omission'):
        payload.generate(stage, tmp_path / 'files.iss', tmp_path / 'report.json', plan)


def test_generated_files_cannot_be_placed_in_stage(tmp_path):
    stage, plan, _ = fixture(tmp_path)
    with pytest.raises(ValueError, match='outside the stage'):
        payload.generate(stage, stage / 'files.iss', tmp_path / 'report.json', plan)
