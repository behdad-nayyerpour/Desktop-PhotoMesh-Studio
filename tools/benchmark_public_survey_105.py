"""Public RTK/GCP hold-out validation; no personal photos or fitted checkpoints."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.request

DATA_REPO = 'OpenDroneMap/odm_data_helenenschacht'
DATA_COMMIT = 'eece33e9ece2ff358a7bdc02e1db6f67925e00c4'


def download(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'Lens2Mesh-public-survey-validation'})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def prepare(folder):
    folder.mkdir(parents=True, exist_ok=True)
    tree = json.loads(download(f'https://api.github.com/repos/{DATA_REPO}/git/trees/{DATA_COMMIT}?recursive=1'))
    entries = {r['path']: r for r in tree['tree'] if r['type'] == 'blob'}
    root = f'https://raw.githubusercontent.com/{DATA_REPO}/{DATA_COMMIT}/'
    gcp = download(root+'GCP/gcp_list.txt')
    (folder/'gcp_list.txt').write_bytes(gcp)
    (folder/'LICENSE').write_bytes(download(root+'LICENSE'))
    (folder/'README.md').write_bytes(download(root+'README.md'))
    names = sorted({line.split()[5] for line in gcp.decode('utf-8-sig').splitlines()[1:] if line.strip()})
    records = []
    photos = folder/'images'; photos.mkdir(exist_ok=True)
    for name in names:
        key = 'images/'+name; entry = entries[key]
        path = photos/name
        if not path.is_file():
            data = download(root+key)
            digest = hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
            if digest != entry['sha']:
                raise ValueError('Public image Git identity mismatch: '+name)
            path.write_bytes(data)
        records.append(dict(name=name, git_blob=entry['sha'], sha256=hashlib.sha256(path.read_bytes()).hexdigest(), bytes=path.stat().st_size))
    (folder/'dataset.json').write_text(json.dumps(dict(repository=DATA_REPO, commit=DATA_COMMIT,
        license='GPL-3.0; test data only, not bundled with application', selection='Every photo with a published GCP observation',
        controls=['1','2','4'], independent_checkpoints=['3','5'], photos=records), indent=2))
    return photos


def execute(exe, command, log):
    started = time.perf_counter()
    result = subprocess.run([str(exe), *map(str, command)], stdout=log, stderr=subprocess.STDOUT, timeout=1200)
    log.flush()
    if result.returncode:
        raise RuntimeError('Native command failed: '+command[0])
    return time.perf_counter()-started


def reconstruct(exe, data, output):
    from photomesh import colmap as cm, engine
    photos = prepare(data)
    folder = output/'alignment'; folder.mkdir(parents=True)
    database = folder/'database.db'; sparse = folder/'sparse'; sparse.mkdir()
    settings = dict(feature_method='SIFT', use_gpu=False, key_point_limit=4096)
    timings = {}
    with (folder/'native.log').open('w', encoding='utf-8') as log:
        args = ['feature_extractor', '--database_path', database, '--image_path', photos,
                '--ImageReader.single_camera', '1', '--ImageReader.camera_model', 'SIMPLE_RADIAL']
        args += engine.matching_arguments(str(exe), 'feature_extractor', settings, True)
        args += cm.opt(str(exe), 'feature_extractor', ['FeatureExtraction.max_image_size', 'SiftExtraction.max_image_size'], 2000)
        args += cm.opt(str(exe), 'feature_extractor', ['FeatureExtraction.num_threads', 'SiftExtraction.num_threads'], 2)
        timings['extract'] = execute(exe, args, log)
        args = ['exhaustive_matcher', '--database_path', database]
        args += engine.matching_arguments(str(exe), 'exhaustive_matcher', settings)
        args += cm.opt(str(exe), 'exhaustive_matcher', ['FeatureMatching.num_threads', 'SiftMatching.num_threads'], 2)
        timings['match'] = execute(exe, args, log)
        args = ['mapper', '--database_path', database, '--image_path', photos, '--output_path', sparse]
        args += cm.opt(str(exe), 'mapper', ['Mapper.multiple_models'], 0)
        args += cm.opt(str(exe), 'mapper', ['Mapper.min_model_size'], 3)
        args += cm.opt(str(exe), 'mapper', ['Mapper.num_threads'], 2)
        timings['map'] = execute(exe, args, log)
    from photomesh import colmap_io as cio
    models = [p for p in sparse.iterdir() if p.is_dir() and (p/'images.bin').is_file()]
    if not models:
        raise AssertionError('No public-data reconstruction')
    selected = max(models, key=lambda p: len(cio.read_model(str(p)).images))
    shutil.copytree(selected, output/'starting-model')
    (output/'timings.json').write_text(json.dumps(timings, indent=2))


def parse_gcps(data):
    markers = {}
    for line in (data/'gcp_list.txt').read_text(encoding='utf-8-sig').splitlines()[1:]:
        fields = line.split()
        if not fields:
            continue
        lon, lat, z, u, v = map(float, fields[:5]); name, label = fields[5:7]
        marker = markers.setdefault(label, dict(label=label, enabled=label in ('1','2','4'),
            ref=[lon, lat, z], acc=[.02,.02], projections={}))
        if marker['ref'] != [lon, lat, z]:
            raise ValueError('Conflicting published GCP coordinate')
        marker['projections'][name] = [u, v, True]
    return list(markers.values())


def independently_triangulate(model, marker):
    import numpy as np
    by_name = {im.name: im for im in model.images.values()}
    A, b = np.zeros((3, 3)), np.zeros(3)
    used = 0
    for name, (u, v, _pinned) in marker['projections'].items():
        image = by_name.get(name)
        if image is None:
            continue
        camera = model.cameras[image.camera_id]
        if camera.model != 2:
            raise ValueError('Independent validation expects SIMPLE_RADIAL calibration')
        f, cx, cy, k = camera.params
        distorted = np.array([(u-cx)/f, (v-cy)/f]); radius = np.linalg.norm(distorted)
        ru = radius
        for _ in range(20):
            ru -= (ru+k*ru**3-radius)/(1+3*k*ru**2)
        xy = distorted*(ru/radius if radius else 1.)
        ray = image.R().T @ np.r_[xy, 1.]; ray /= np.linalg.norm(ray)
        projection = np.eye(3)-np.outer(ray, ray)
        A += projection; b += projection @ image.center(); used += 1
    if used < 2:
        raise ValueError('Not enough aligned independent observations for '+marker['label'])
    return np.linalg.solve(A, b), used


def evaluate(model_path, data, output):
    import numpy as np
    import pyproj
    from PIL import Image
    from photomesh import colmap_io as cio, georef
    from photomesh.exif import photo_metadata
    output.mkdir(parents=True)
    markers = parse_gcps(data)
    original = cio.read_model(str(model_path))
    photo_count = len(list((data/'images').glob('*.JPG')))
    assert len(original.images) >= photo_count*.8, 'Too few registered public photos'
    gps = {}
    for image in original.images.values():
        with Image.open(data/'images'/image.name) as photo:
            metadata = photo_metadata(photo)
        if all(metadata.get(key) is not None for key in ('lon','lat','alt')):
            gps[image.name] = [metadata[key] for key in ('lon','lat','alt')]
    projector = pyproj.Transformer.from_crs(4326, 32633, always_xy=True)
    result = dict(cameras=len(original.images), source_photos=photo_count, points=len(original.points),
        controls=['1','2','4'], held_out=['3','5'], reference='Published Emlid RS2 GCP coordinates; source height datum retained without an assumed GPS conversion',
        registered_gps=len(gps), scenarios=[])
    for mode in ('local', 'controls', 'gps'):
        folder = output/mode; shutil.copytree(model_path, folder)
        cfg = dict(model=str(folder), markers=markers, camera_gps=gps, crs='EPSG:4326',
            use_markers=mode=='controls', use_cameras=mode=='gps', local_only=mode=='local',
            bundle=True, fit_intrinsics=True, tie_points=20000, max_iterations=12,
            strict_heights=True, marker_height_reference='unknown', camera_height_reference='unknown')
        messages = []; started = time.perf_counter()
        info = georef.run_task(cfg, log=messages.append)
        (output/(mode+'.log')).write_text('\n'.join(messages), encoding='utf-8')
        changed = cio.read_model(str(folder))
        pixels = cio.observation_errors(changed)[0]
        row = dict(mode=mode, seconds=time.perf_counter()-started,
            reprojection_rms_px=float(np.sqrt(np.mean(pixels**2))), checks=[])
        if mode != 'local':
            for marker in markers:
                if marker['enabled']:
                    continue
                xyz, n = independently_triangulate(changed, marker)
                estimated = xyz+info['offset']
                easting, northing = projector.transform(*marker['ref'][:2])
                delta = estimated-np.array([easting, northing, marker['ref'][2]])
                row['checks'].append(dict(label=marker['label'], observations=n,
                    xy_m=float(np.linalg.norm(delta[:2])), z_m=float(delta[2]) if mode=='controls' else None))
            assert len(row['checks']) == 2
            if mode == 'controls':
                # The reference was not fitted to these coordinates or their pixels.
                assert max(c['xy_m'] for c in row['checks']) < .5, row
                assert max(abs(c['z_m']) for c in row['checks']) < .5, row
                # A tagged observation edit must change its freshly triangulated estimate.
                import copy
                edited = copy.deepcopy(next(m for m in markers if m['label']=='3'))
                name = next(iter(edited['projections'])); edited['projections'][name][0] += 10
                before, _ = independently_triangulate(changed, next(m for m in markers if m['label']=='3'))
                after, _ = independently_triangulate(changed, edited)
                assert np.linalg.norm(after-before) > 1e-4
                row['edited_observation_shift_m'] = float(np.linalg.norm(after-before))
        result['scenarios'].append(row)
    mixed = output/'mixed-unknown'; shutil.copytree(model_path, mixed)
    try:
        georef.run_task(dict(model=str(mixed), markers=markers, camera_gps=gps, crs='EPSG:4326',
            use_markers=True, use_cameras=True, strict_heights=True), log=lambda *_: None)
    except ValueError as error:
        assert 'height' in str(error).lower(); result['mixed_unknown_heights_rejected'] = str(error)
    else:
        raise AssertionError('Mixed unknown GPS/GCP heights were silently accepted')
    (output/'results.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', type=Path)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--model', type=Path)
    parser.add_argument('--app-source', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    sys.path.insert(0, str(args.app_source.resolve()))
    if args.model:
        evaluate(args.model, args.data, args.output)
    else:
        reconstruct(args.exe, args.data, args.output)
        evaluate(args.output/'starting-model', args.data, args.output/'evaluation')
