"""Offline native feature/matching/mapper validation on explicitly supplied photos."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

import psutil

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from photomesh import engine  # noqa: E402
from photomesh.colmap import opt  # noqa: E402
from photomesh.colmap_io import read_model  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', required=True)
    parser.add_argument('--photos', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--cpu', action='store_true')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    photos = [p for p in args.photos.iterdir() if p.suffix.lower() in ('.jpg', '.png', '.jpeg')]
    assert len(photos) >= 3
    records = dict(hardware=engine.hardware(), engine=args.exe,
                   photos=[dict(name=p.name, sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(photos)], results=[])
    for method in ('ALIKED + LightGlue', 'SIFT + LightGlue'):
        work = args.output/method.split(' ')[0]; work.mkdir()
        settings = engine.execution_settings(args.exe, dict(feature_method=method, use_gpu=not args.cpu,
                                                            key_point_limit=1024), str(work))
        assert settings['use_gpu'] is (not args.cpu), settings
        database = str(work/'database.db')
        pairs = work/'pairs.txt'
        pairs.write_text(''.join(f'{a.name} {b.name}\n' for i,a in enumerate(photos) for b in photos[i+1:]))
        extract = ['feature_extractor', '--database_path', database, '--image_path', str(args.photos.resolve())]
        extract += engine.matching_arguments(args.exe, extract[0], settings, True)
        extract += opt(args.exe, extract[0], ['FeatureExtraction.max_image_size','SiftExtraction.max_image_size'], 1024)
        extract += opt(args.exe, extract[0], ['SiftExtraction.max_num_features'], 1024)
        match = ['matches_importer','--database_path',database,'--match_list_path',str(pairs),'--match_type','pairs']
        match += engine.matching_arguments(args.exe, match[0], settings)
        model = work/'sparse'; model.mkdir()
        mapper = ['mapper', '--database_path', database, '--image_path', str(args.photos.resolve()), '--output_path', str(model)]
        mapper += opt(args.exe, 'mapper', ['Mapper.num_threads'], 2)
        stages=[]
        for command in (extract, match, mapper):
            log = work/(command[0]+'.log')
            start=time.perf_counter(); modules=set()
            with log.open('w', encoding='utf-8') as stream:
                process=subprocess.Popen([args.exe, *command], stdout=stream, stderr=subprocess.STDOUT,
                                         env=engine.child_env(args.exe), creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                while process.poll() is None:
                    try:
                        modules.update(m.path for m in psutil.Process(process.pid).memory_maps())
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                    if time.perf_counter()-start>300:
                        process.kill(); process.wait(); raise TimeoutError(command[0])
                    time.sleep(.05)
            stages.append(dict(command=command, code=process.returncode, seconds=time.perf_counter()-start,
                               runtime_modules=sorted(p for p in modules if any(s in Path(p).name.lower() for s in ('cublas','cudart','cudnn')))))
            assert process.returncode == 0, log.read_text(encoding='utf-8',errors='replace')[-4000:]
        with sqlite3.connect(database) as connection:
            features = connection.execute('SELECT SUM(rows) FROM keypoints').fetchone()[0]
            matches = connection.execute('SELECT SUM(rows) FROM two_view_geometries').fetchone()[0]
        models=[read_model(str(p)) for p in model.iterdir() if p.is_dir() and (p/'images.bin').is_file()]
        best=max(models,key=lambda m:len(m.images))
        assert len(best.images)>=3 and len(best.points)>50 and matches>50
        if not args.cpu:
            assert any(Path(p).name.lower()=='cublaslt64_12.dll' for s in stages for p in s['runtime_modules'])
            assert all('neural-cuda12' in p for s in stages for p in s['runtime_modules'] if '_12.dll' in p)
        records['results'].append(dict(method=method, settings=settings, stages=stages, features=features,
                                        verified_observations=matches, registered=len(best.images), points=len(best.points)))
        (args.output/'results.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
        print(method, len(best.images), 'cameras;', len(best.points), 'points', flush=True)


if __name__ == '__main__':
    main()
