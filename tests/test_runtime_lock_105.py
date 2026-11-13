import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('runtime_lock', Path(__file__).resolve().parents[1]/'packaging/verify_runtime_lock.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_exact_runtime_lock_rejects_missing_changed_and_unexpected(tmp_path):
    lock = tmp_path/'requirements.lock'
    lock.write_text('one==1.0 --hash=sha256:'+64*'a'+'\n')
    site = tmp_path/'python/Lib/site-packages/one-1.0.dist-info'
    site.mkdir(parents=True)
    (site/'METADATA').write_text('Name: one\nVersion: 1.0\n')
    assert module.verify(tmp_path, lock)['packages'] == 1
    empty = site.parent/'plyfile-1.1.dist-info'
    empty.mkdir()
    assert module.verify(tmp_path, lock)['packages'] == 1
    (empty/'METADATA').write_text('Version: 1.1\n')
    with pytest.raises(ValueError, match='has no Name'):
        module.verify(tmp_path, lock)
    (empty/'METADATA').unlink()
    (site/'METADATA').write_text('Name: one\nVersion: 2.0\n')
    with pytest.raises(ValueError, match='changed'):
        module.verify(tmp_path, lock)
    (site/'METADATA').write_text('Name: two\nVersion: 1.0\n')
    with pytest.raises(ValueError, match='missing.*one.*unexpected.*two'):
        module.verify(tmp_path, lock)


def test_duplicate_and_unhashed_pins_rejected(tmp_path):
    lock = tmp_path/'requirements.lock'
    lock.write_text('one==1.0\n')
    with pytest.raises(ValueError, match='Invalid hashed'):
        module.verify(tmp_path, lock)
    lock.write_text(2*('one==1.0 --hash=sha256:'+64*'a'+'\n'))
    with pytest.raises(ValueError, match='Duplicate runtime pin'):
        module.verify(tmp_path, lock)
