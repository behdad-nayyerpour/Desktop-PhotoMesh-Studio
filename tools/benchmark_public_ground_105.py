"""Evaluate ground classes against PDAL's public classified Autzen fixture.

Published class labels are independent references, not hand-labelled here.
This small tile cannot establish general terrain or GPU reconstruction accuracy.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import urllib.request

COMMIT = 'ce0024257c573526389c4db9ab26e82739b8aaa9'
SHA256 = 'c8828215facfb4c9465c9a7db9d45cf2c0e9175a6eb5b21e89417978cc85cd51'


def evaluate(source, output):
    import numpy as np
    from photomesh.survey_deps import laspy
    from photomesh.plycodec import PlyDocument, PlyElement
    from photomesh.ground import classify_cloud
    from photomesh.las_export import export_las
    from photomesh.progress import WorkProgress
    output.mkdir(parents=True, exist_ok=True)
    data = source.read_bytes()
    if hashlib.sha256(data).hexdigest() != SHA256:
        raise ValueError('Public classified reference differs from pinned PDAL LFS SHA256')
    del data
    reference = laspy().read(source)
    crs = reference.header.parse_crs()
    factors = [axis.unit_conversion_factor for axis in crs.axis_info]
    if len(factors) != 2 or not np.allclose(factors, factors[0]) or not .3047 < factors[0] < .3049:
        raise ValueError('Expected documented foot-based source coordinate system')
    # Convert both horizontal and vertical coordinates to metres. No vertical
    # datum transformation is inferred; the original height reference is kept.
    xyz = np.column_stack([reference.x, reference.y, reference.z])*factors[0]
    origin = xyz.mean(0)
    records = np.empty(len(xyz), dtype=[('x','f8'),('y','f8'),('z','f8'),('source_index','u4')])
    for i, name in enumerate('xyz'):
        records[name] = xyz[:, i]-origin[i]
    records['source_index'] = np.arange(len(xyz))
    cloud = output/'source.ply'; classified = output/'classified.ply'
    PlyDocument([PlyElement.describe(records, 'vertex')]).write(str(cloud))
    progress = WorkProgress(); samples = []; started = time.perf_counter()
    def report(done, total, stage):
        progress.update(done, total)
        samples.append(dict(elapsed=time.perf_counter()-started, done=done, total=total,
                            eta=progress.remaining(), stage=stage))
    info = classify_cloud(str(cloud), str(classified), progress=report)
    seconds = time.perf_counter()-started
    result = PlyDocument.read(str(classified))['vertex'].data
    np.testing.assert_array_equal(result['source_index'], records['source_index'])
    for axis in 'xyz':
        np.testing.assert_array_equal(result[axis], records[axis])
    ground = result['classification'] == 2; reference_labels = np.asarray(reference.classification)
    truth = reference_labels == 2
    # Unclassified/noise are not independent non-ground truth. Use only the
    # human-labelled categories documented in PDAL/data's Autzen README.
    known = np.isin(reference_labels, [2,5,6,9,15,17,19,64,65,66,67,68,69,70,71,72,73,74,75,76,77])
    tp = int(np.count_nonzero(ground & truth)); fp = int(np.count_nonzero(ground & ~truth & known))
    fn = int(np.count_nonzero(~ground & truth)); tn = int(np.count_nonzero(~ground & ~truth & known))
    assert 0 < tp < len(xyz) and 0 < tn < len(xyz)
    assert samples and samples[-1]['done'] == samples[-1]['total'] == 100
    assert all(a['done'] <= b['done'] for a, b in zip(samples, samples[1:]))
    for suffix in ('las','laz'):
        path = output/('roundtrip.'+suffix)
        export_las(str(classified), str(path), dict(offset=origin.tolist(), metric_scale=True), precision=.001)
        restored = laspy().read(path)
        np.testing.assert_array_equal(restored.classification, result['classification'])
        np.testing.assert_array_equal(restored.source_index, result['source_index'])
        np.testing.assert_allclose(np.column_stack([restored.x, restored.y, restored.z]), xyz, atol=.000501, rtol=0)
        # Coordinates were converted to a local metric convention; do not stamp
        # the original foot-based CRS onto these metre-valued coordinates.
        assert restored.header.parse_crs() is None
    record = dict(repository='PDAL/data', commit=COMMIT, path='autzen/autzen-classified.laz',
        sha256=SHA256, points=len(xyz), source_class_counts={str(c):int(n) for c,n in zip(*np.unique(reference_labels,return_counts=True))},
        attribution='Aaron Reyna / Watershed Sciences 2010 LiDAR; Max Sampson / Hobu 2021 manual classes; PDAL/data CC-BY-4.0',
        reference_ground=int(truth.sum()), predicted_ground=int(ground.sum()),
        tp=tp, fp=fp, fn=fn, tn=tn, precision=tp/(tp+fp), recall=tp/(tp+fn),
        seconds=seconds, settings={k:v for k,v in info.items() if k not in ('path','rotation')},
        units=f'Metres converted with source CRS factor {factors[0]}; XYZ use source feet, height datum unchanged',
        progress=samples, las_laz_roundtrip=True,
        limitation='One public tile with published class labels; no universal accuracy or target GPU claim')
    (output/'results.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in record.items() if k != 'progress'}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    if not args.source.is_file():
        url = f'https://media.githubusercontent.com/media/PDAL/data/{COMMIT}/autzen/autzen-classified.laz'
        urllib.request.urlretrieve(url, args.source)
    evaluate(args.source, args.output)
