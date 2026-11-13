"""Exercise both offline learned methods on CPU without the optional GPU DLLs."""
import argparse
import json
from pathlib import Path
import sys


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    app = args.root.resolve() / 'app'
    sys.path.insert(0, str(app))
    from photomesh import engine
    assert Path(engine.__file__).resolve().is_relative_to(app)
    private = app / 'photomesh/resources/neural-cuda12'
    assert (private / 'runtime.json').is_file()
    assert not list(private.glob('*.dll')), 'The base test must actually exclude optional DLLs'
    exe = str(args.root.resolve() / 'tools/colmap-cpu/bin/colmap.exe')
    args.output.mkdir(parents=True, exist_ok=True)
    records = []
    for method in ('ALIKED + LightGlue', 'SIFT + LightGlue'):
        messages = []
        settings = engine.execution_settings(exe, dict(feature_method=method, use_gpu=True,
                                                     key_point_limit=1024), str(args.output), messages.append)
        assert settings['feature_method'] == method and settings['use_gpu'] is False
        records.append(dict(method=method, use_gpu=False, messages=messages))
    (args.output / 'cpu-without-addon.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
    print('Both learned methods completed real offline extraction/matching probes on CPU without optional GPU DLLs')
