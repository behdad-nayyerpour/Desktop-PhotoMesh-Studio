"""Read-only numerical checks with independent answers; no pytest required.

Run against source or an installed ``app`` directory. Absolute tolerances are
numerical regression limits, not claims of survey accuracy on real imagery.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path


def run_checks(app_dir):
    import numpy as np
    from photomesh import coordinates, georef as g, survey_geometry as sg

    app_dir = Path(app_dir).resolve()
    for module in (coordinates, g, sg):
        if not Path(module.__file__).resolve().is_relative_to(app_dir):
            raise ValueError(f'Wrong application module loaded: {module.__file__}')
    records = []

    def check(name, calculate, expected, tolerance, unit):
        row = dict(name=name, expected=np.asarray(expected).tolist(),
                   tolerance=tolerance, unit=unit)
        try:
            actual = np.asarray(calculate(), dtype=float)
            target = np.asarray(expected, dtype=float)
            row['actual'] = actual.tolist()
            if actual.shape != target.shape or not np.isfinite(actual).all():
                raise ValueError('Unexpected shape or non-finite result')
            row['max_absolute_error'] = float(np.max(np.abs(actual-target)))
            row['status'] = 'PASS' if row['max_absolute_error'] <= tolerance else 'FAIL'
        except Exception as error:
            row.update(status='ERROR', error=f'{type(error).__name__}: {error}')
        records.append(row)

    # Literal signed vectors: (3,4,0), (-6,0,8), and a separate check (0,0,-12).
    markers = [g.Marker('A', [0, 0, 0]), g.Marker('B', [0, 0, 0]),
               g.Marker('check', [0, 0, 0], enabled=False)]
    rows = g.marker_errors(markers, lambda value: np.asarray(value, float),
                           {'A': [3, 4, 0], 'B': [-6, 0, 8], 'check': [0, 0, -12]})
    check('Signed XYZ residuals, including check point',
          lambda: [[row[k] for k in ('dx', 'dy', 'dz', 'total')] for row in rows],
          [[3, 4, 0, 5], [-6, 0, 8, 10], [0, 0, -12, 12]], 1e-12, 'm')
    keys = ('n', 'x', 'y', 'z', 'xy', 'total')
    check('Control RMSE and denominator (check excluded)',
          lambda: [g.rmse(rows, 'control')[k] for k in keys],
          [2, math.sqrt(22.5), math.sqrt(8), math.sqrt(32), math.sqrt(30.5),
           math.sqrt(62.5)], 1e-12, 'm; n is a count')
    check('Check RMSE (controls excluded)',
          lambda: [g.rmse(rows, 'check')[k] for k in keys],
          [1, 0, 0, 12, 0, 12], 1e-12, 'm; n is a count')
    check('Empty statistics are unavailable, not zero',
          lambda: int(g.rmse([], 'check') is None), 1, 0, 'boolean')

    def distance(a, b):
        result = sg.distance_components(a, b)
        return [result[k] for k in ('horizontal', 'distance', 'height',
                                    'slope_percent', 'slope_degrees')]

    expected = [5, 13, 12, 240, math.degrees(math.atan2(12, 5))]
    check('3-4-12 triangle', lambda: distance([0, 0, 0], [3, 4, 12]),
          expected, 1e-12, 'm, %, degrees')
    check('Reversed endpoints preserve lengths and reverse signed height/slope',
          lambda: distance([3, 4, 12], [0, 0, 0]),
          [5, 13, -12, -240, -expected[-1]], 1e-12, 'm, %, degrees')
    check('Large map origin preserves small differences',
          lambda: distance([500000, 4500000, 100], [500003, 4500004, 112]),
          expected, 1e-12, 'm, %, degrees')
    check('Vertical endpoints do not report a finite slope',
          lambda: int(sg.distance_components([0, 0, 0], [0, 0, 2])['slope_percent'] is None),
          1, 0, 'boolean')

    # WGS84 cardinal coordinates, independent of application conversion code.
    check('WGS84 equator axes',
          lambda: g.geodetic_to_ecef([0, 0], [0, 90], [0, 0]),
          [[6378137, 0, 0], [0, 6378137, 0]], 1e-8, 'm')
    check('WGS84 pole semi-minor axis',
          lambda: g.geodetic_to_ecef([90, -90], [0, 0], [0, 0]),
          [[0, 0, 6356752.314245179], [0, 0, -6356752.314245179]], 1e-8, 'm')
    try:
        import pyproj
    except ImportError:
        records.append(dict(name='Independent PROJ comparisons', status='ERROR',
                            error='pyproj missing; independent comparisons not executed'))
        pyproj = None
    if pyproj is not None:
        geographic = np.array([[44.5152, 40.1872, 1234.5], [18.4241, -33.9249, 25],
                               [179.9, 70, 100], [-179.9, -70, -20]])
        transformer = pyproj.Transformer.from_crs(4979, 4978, always_xy=True)
        earth = np.column_stack(transformer.transform(*geographic.T))
        check('ECEF forward vs independent PROJ',
              lambda: g.geodetic_to_ecef(geographic[:, 1], geographic[:, 0], geographic[:, 2]),
              earth, 2e-7, 'm')
        inverse = g.ecef_to_geodetic(earth)
        check('ECEF inverse angles from independent input',
              lambda: np.column_stack([inverse[1], inverse[0]]), geographic[:, :2], 2e-10, 'degrees')
        check('ECEF inverse heights from independent input', lambda: inverse[2],
              geographic[:, 2], 2e-7, 'm')
        for lon, lat, zone, south in [(44.5152, 40.1872, 38, False),
                                       (18.4241, -33.9249, 34, True),
                                       (8.9, 83, 31, False), (-177, -79, 1, True)]:
            reference = pyproj.Transformer.from_crs(4326, (32700 if south else 32600)+zone,
                                                   always_xy=True)
            easting, northing = reference.transform(lon, lat)
            check(f'UTM {zone}{"S" if south else "N"} forward vs PROJ at {lat},{lon}',
                  lambda lat=lat, lon=lon, zone=zone, south=south: g.utm_forward(lat, lon, zone, south),
                  [easting, northing], .001, 'm')
            check(f'UTM {zone}{"S" if south else "N"} inverse from PROJ coordinates',
                  lambda e=easting, n=northing, zone=zone, south=south: g.utm_inverse(e, n, zone, south),
                  [lat, lon], 1e-8, 'degrees')
        frame = {'kind': 'enu', 'origin': [44.5, 40.2, 1200.]}
        transform = pyproj.Transformer.from_pipeline(
            '+proj=pipeline +step +proj=cart +ellps=WGS84 '
            '+step +proj=topocentric +ellps=WGS84 +lon_0=44.5 +lat_0=40.2 +h_0=1200')
        positions = np.array([[44.5, 40.2, 1200], [44.501, 40.201, 1203], [44.49, 40.19, 1190]])
        independent = np.column_stack(transform.transform(*positions.T))
        check('ENU origin, axes and scale vs independent PROJ topocentric pipeline',
              lambda: coordinates.geographic_to_enu(positions, frame), independent, 2e-7, 'm')

    # Analytic surface z=2x-3y+7; rectangle crosses diagonal at an oblique section.
    xy = np.array([[0, 0], [10, 0], [10, 10], [0, 10]], float)
    vertices = np.column_stack([xy, 2*xy[:, 0]-3*xy[:, 1]+7])
    for origin in ([0, 0, 0], [500000, 4500000, 100]):
        origin = np.asarray(origin, float)
        mesh = sg.MeshSurface(vertices+origin, np.array([[0, 1, 2], [0, 2, 3]]))
        for reverse in (False, True):
            a, b = np.array([1., 2.]), np.array([9., 8.])
            if reverse:
                a, b = b, a
            segments = mesh.section_segments(a+origin[:2], b+origin[:2])
            along = segments[:, :, 0]
            points = a + along[:, :, None] * ((b-a)/10)
            target_z = 2*points[:, :, 0]-3*points[:, :, 1]+7+origin[2]
            label = f'Analytic oblique section, origin={origin.tolist()}, reversed={reverse}'
            check(label+' elevations', lambda segments=segments: segments[:, :, 1], target_z, 2e-8, 'm')
            check(label+' coverage',
                  lambda segments=segments: [segments[:, :, 0].min(), segments[:, :, 0].max(),
                                             np.abs(np.diff(segments[:, :, 0], axis=1)).sum()],
                  [0, 10, 10], 2e-8, 'm')

    modules = [g, coordinates, sg]
    return dict(created_utc=datetime.now(timezone.utc).isoformat(), app_dir=str(app_dir),
                python=sys.executable, python_version=platform.python_version(),
                numpy_version=np.__version__, pyproj_version=pyproj.__version__ if pyproj else None,
                application_files={str(Path(m.__file__).resolve().relative_to(app_dir)):
                                   hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest() for m in modules},
                scope='Synthetic numerical contracts only; not real-project accuracy certification.',
                checks=records, passed=all(row['status'] == 'PASS' for row in records))


def write_report(report, output):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.with_suffix('.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    rows = []
    for row in report['checks']:
        values = [row['status'], row['name'], row.get('expected', ''), row.get('actual', ''),
                  row.get('max_absolute_error', ''), row.get('tolerance', ''),
                  row.get('unit', ''), row.get('error', '')]
        rows.append('<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in values)+'</tr>')
    heading = 'PASS' if report['passed'] else 'FAIL / INCOMPLETE'
    document = ('<!doctype html><meta charset="utf-8"><title>Lens2Mesh numerical checks</title>'
                '<style>body{font:15px sans-serif;margin:24px}table{border-collapse:collapse}'
                'td,th{border:1px solid #aaa;padding:8px;vertical-align:top}</style>'
                f'<h1>Lens2Mesh numerical checks: {heading}</h1><p>{html.escape(report["scope"])}</p>'
                f'<p>Application: {html.escape(report["app_dir"])}</p>'
                '<table><tr><th>Status</th><th>Check</th><th>Expected</th><th>Actual</th>'
                '<th>Max absolute error</th><th>Absolute tolerance</th><th>Unit</th><th>Error</th></tr>'
                +''.join(rows)+'</table><p>Provenance and file hashes: accompanying JSON report.</p>')
    output.with_suffix('.html').write_text(document, encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app-dir', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path, required=True, help='Report base path (.html and .json written)')
    args = parser.parse_args()
    sys.dont_write_bytecode = True
    os.environ['PROJ_NETWORK'] = 'OFF'
    if not (args.app_dir/'photomesh'/'georef.py').is_file():
        parser.error('--app-dir must contain photomesh/georef.py (installed root/app or source root)')
    if args.output.resolve().is_relative_to(args.app_dir.resolve()):
        parser.error('Keep reports outside application files; select another --output location')
    sys.path.insert(0, str(args.app_dir.resolve()))
    report = run_checks(args.app_dir)
    write_report(report, args.output)
    for row in report['checks']:
        print(f"{row['status']}: {row['name']}")
    print(f"Report: {args.output.with_suffix('.html')}")
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
