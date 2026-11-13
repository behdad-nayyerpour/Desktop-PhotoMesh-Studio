"""Private DLL lookup and authenticated, minimal redistributable staging."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import zipfile

import pytest
from photomesh import engine

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'packaging'))
import neural_runtime as runtime  # noqa: E402


def test_private_runtime_does_not_change_host_or_legacy_lookup(tmp_path, monkeypatch):
    module = tmp_path/'app/photomesh/engine.py'
    private = module.parent/'resources/neural-cuda12'
    private.mkdir(parents=True)
    monkeypatch.setattr(engine, '__file__', str(module))
    monkeypatch.setenv('PATH', 'host-path')
    monkeypatch.setattr(engine, 'bundle_manifest', lambda exe: {'version': '4.2.1'} if 'modern' in exe else {})
    modern = engine.child_env(str(tmp_path/'modern/bin/colmap.exe'))['PATH'].split(os.pathsep)
    legacy = engine.child_env(str(tmp_path/'legacy/bin/colmap.exe'))['PATH'].split(os.pathsep)
    assert modern[:3] == [str(tmp_path/'modern/bin'), str(tmp_path/'modern/lib'), str(private)]
    assert str(private) not in legacy
    assert os.environ['PATH'] == 'host-path'


@pytest.fixture
def tiny_archive(tmp_path, monkeypatch):
    archive = tmp_path/'runtime.zip'
    data, license_text = b'redistributable fixture', b'exact license'
    with zipfile.ZipFile(archive, 'w') as output:
        output.writestr('runtime/LICENSE', license_text)
        output.writestr('runtime/bin/test.dll', data)
        output.writestr('runtime/bin/unreviewed.exe', b'do not stage')
    asset = dict(name='runtime.zip', license_sha256=hashlib.sha256(license_text).hexdigest(),
                 files=[dict(name='test.dll', bytes=len(data), sha256=hashlib.sha256(data).hexdigest())])
    monkeypatch.setattr(runtime, 'specification', lambda: dict(schema=1, assets=[asset]))
    monkeypatch.setattr(runtime, 'acquire', lambda *args: archive)
    return asset, archive


def test_staging_keeps_only_reviewed_dlls_and_manifest(tmp_path, tiny_archive):
    output = runtime.prepare(tmp_path/'out', tmp_path/'cache', offline=True)
    assert {p.name for p in output.iterdir()} == {'test.dll', 'runtime.json'}
    assert json.loads((output/'runtime.json').read_text())['assets'][0]['license_sha256']
    with pytest.raises(ValueError, match='fresh'):
        runtime.prepare(output, tmp_path/'cache')


@pytest.mark.parametrize('tamper', ['license', 'dll', 'escape'])
def test_different_or_unsafe_runtime_is_rejected(tmp_path, tiny_archive, tamper):
    asset, archive = tiny_archive
    if tamper == 'license':
        asset['license_sha256'] = '0'*64
    elif tamper == 'dll':
        asset['files'][0]['sha256'] = '0'*64
    else:
        asset['files'][0]['name'] = '../escape.dll'
    with pytest.raises(ValueError):
        runtime.prepare(tmp_path/'out', tmp_path/'cache')
    assert not (tmp_path/'escape.dll').exists()


def test_payload_preparation_requires_exact_manifest(tmp_path, tiny_archive):
    (tmp_path/'manifest.json').write_text(json.dumps({'files': []}))
    with pytest.raises(ValueError, match='exact reviewed'):
        runtime.prepare_payload(tmp_path, tmp_path/'cache')


def test_partial_patch_fetches_only_changed_runtime_components(tmp_path, tiny_archive):
    target = runtime.runtime_files()[0]
    (tmp_path/'manifest.json').write_text(json.dumps({'files': [target]}))
    output = runtime.prepare_payload(tmp_path, tmp_path/'cache')
    assert {p.name for p in output.iterdir()} == {'test.dll'}


def test_added_native_resources_are_backed_up_and_removed_on_rollback(tmp_path):
    spec = importlib.util.spec_from_file_location('neural_updater', ROOT/'packaging/apply_patch.py')
    updater = importlib.util.module_from_spec(spec); spec.loader.exec_module(updater)
    root, payload = tmp_path/'install فارسی', tmp_path/'payload'
    for base in (root, payload):
        (base/'app').mkdir(parents=True)
    (root/'python').mkdir(); (root/'python/python.exe').write_bytes(b'unchanged')
    (root/'app/runtime.id').write_text('a'*64)
    target = runtime.RESOURCE+'/test.dll'
    source = payload/target; source.parent.mkdir(parents=True); source.write_bytes(b'native fixture')
    manifest = dict(schema=1, candidate='c'*40, runtime_id='a'*64, baseline={},
                    files=[dict(path=target, sha256=updater.digest(source))])
    state = updater.apply(root, payload, manifest)
    assert (root/target).read_bytes() == b'native fixture'
    updater.rollback(root, state)
    assert not (root/target).exists()
    assert (root/'python/python.exe').read_bytes() == b'unchanged'
