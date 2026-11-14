"""Generate exact reference meshes and audit an installed/source survey engine.

The expected results come from closed-form geometry, not a second invocation of
the tested functions. Does not edit an installation, user project or settings.
"""
import argparse
import hashlib
import html
import importlib
import json
import math
from pathlib import Path
import sys

import numpy as np


def write_mesh(path, vertices, faces):
    header = ('ply\nformat ascii 1.0\nelement vertex %d\nproperty double x\n'
              'property double y\nproperty double z\nelement face %d\n'
              'property list uchar int vertex_indices\nend_header\n') % (len(vertices), len(faces))
    path.write_text(header + ''.join(' '.join(format(float(x), '.17g') for x in row)+'\n' for row in vertices)
                    + ''.join('3 '+' '.join(str(int(x)) for x in row)+'\n' for row in faces), encoding='ascii')


def reference_models():
    plane = np.array([[0, 0, 100], [6, 0, 107.2], [0, 8, 116.8], [6, 8, 124]], float)
    outline = np.array([[0, 100], [3, 100], [6, 104], [10, 104]], float)
    ramp = np.array([[x, y, z] for y in (-1, 1) for x, z in outline])
    ramp_faces = np.array([[i, i+1, i+4] for i in range(3)] + [[i+1, i+5, i+4] for i in range(3)])
    gap = np.array([[x, y, 100] for left, right in ((0, 2), (5, 8))
                    for x, y in ((left, -1), (right, -1), (left, 1), (right, 1))], float)
    return {'plane_3_4_12': (plane, np.array([[0, 1, 2], [1, 3, 2]])),
            'ramp_flat_rise_flat': (ramp, ramp_faces),
            'gap_3_metres': (gap, np.array([[0, 1, 2], [1, 3, 2], [4, 5, 6], [5, 7, 6]])),
            'vertical_wall': (np.array([[3, -1, 100], [3, 1, 100], [3, -1, 104], [3, 1, 104]], float),
                              np.array([[0, 1, 2], [1, 3, 2]]))}


def run_checks(app, output):
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(Path(app).resolve()))
    geometry = importlib.import_module('photomesh.survey_geometry')
    checks = []

    def check(name, actual, expected, tolerance=1e-8):
        if expected is None:
            passed = actual is None; error = None
        else:
            a, b = np.asarray(actual, float), np.asarray(expected, float)
            error = float(np.max(np.abs(a-b))) if a.shape == b.shape else float('inf')
            passed = a.shape == b.shape and np.isfinite(a).all() and error <= tolerance
        checks.append(dict(name=name, actual=np.asarray(actual).tolist() if actual is not None else None,
                           expected=np.asarray(expected).tolist() if expected is not None else None,
                           absolute_error=error, tolerance=tolerance, passed=bool(passed)))

    for origin in ([0., 0., 0.], [500000., 4500000., 1000.]):
        a=np.array(origin); b=a+[3., 4., 12.]
        for reverse in (False, True):
            result=geometry.distance_components(*( (b,a) if reverse else (a,b)))
            label=f'3-4-12 origin={origin[0]} reverse={reverse}'
            check(label+' horizontal',result['horizontal'],5)
            check(label+' straight 3D',result['distance'],13)
            check(label+' signed height',result['height'],-12 if reverse else 12)
            check(label+' slope percent',result['slope_percent'],-240 if reverse else 240)
            check(label+' slope degrees',result['slope_degrees'],(-1 if reverse else 1)*67.38013505195958)
    check('Vertical separation',geometry.distance_components([0,0,1],[0,0,6])['distance'],5)
    check('Vertical slope undefined',geometry.distance_components([0,0,1],[0,0,6])['slope_percent'],None)
    check('Coincident distance',geometry.distance_components([2,3,4],[2,3,4])['distance'],0)

    models=reference_models()
    for name,(vertices,faces) in models.items():
        path=output/(name+'.ply');write_mesh(path,vertices,faces)
        surface=geometry.load_surface(str(path))
        if name=='plane_3_4_12':
            for reverse in (False,True):
                start,end=([3,4],[0,0]) if reverse else ([0,0],[3,4])
                segments=surface.section_segments(start,end)
                s=segments[:,:,0];expected=112-2.4*s if reverse else 100+2.4*s
                check(f'Plane reverse={reverse} all section elevations',segments[:,:,1],expected)
                check(f'Plane reverse={reverse} section horizontal coverage',np.abs(np.diff(s,axis=1)).sum(),5)
                check(f'Plane reverse={reverse} section surface length',np.linalg.norm(np.diff(segments,axis=1),axis=2).sum(),13)
            check('Plane surface pick A',surface.pick([0,0,150],[0,0,-1]),[0,0,100])
            check('Plane surface pick B',surface.pick([3,4,150],[0,0,-1]),[3,4,112])
            # Submillimetre detail at a survey-sized coordinate origin, through
            # actual double-precision PLY loading, not only an in-memory mesh.
            shift=np.array([500000.001,4500000.002,.003])
            shifted=output/'plane_utm_double.ply';write_mesh(shifted,vertices+shift,faces)
            loaded=geometry.load_surface(str(shifted))
            check('Large-coordinate double PLY pick',loaded.pick([*shift[:2],150],[0,0,-1]),vertices[0]+shift,2e-9)
            segments=loaded.section_segments(shift[:2],shift[:2]+[3,4])
            check('Large-coordinate section elevation',segments[:,:,1],100+shift[2]+2.4*segments[:,:,0],2e-8)
        elif name=='ramp_flat_rise_flat':
            segments=surface.section_segments([0,0],[10,0]);s=segments[:,:,0]
            expected=np.where(s<=3,100,np.where(s<6,100+(s-3)*4/3,104))
            check('Broken ramp every section vertex',segments[:,:,1],expected)
            check('Broken ramp horizontal coverage',np.abs(np.diff(s,axis=1)).sum(),10)
            check('Broken ramp surface length 3+5+4',np.linalg.norm(np.diff(segments,axis=1),axis=2).sum(),12)
            endpoints=[surface.pick([x,0,150],[0,0,-1]) for x in (0,10)]
            measurement=geometry.distance_components(*endpoints)
            check('Broken ramp straight endpoint chord',measurement['distance'],math.sqrt(116))
            check('Broken ramp signed height',measurement['height'],4)
        elif name=='gap_3_metres':
            segments=surface.section_segments([0,0],[8,0]);s=segments[:,:,0]
            check('Gap retains exactly five metres of surface',np.abs(np.diff(s,axis=1)).sum(),5)
            crossing=any(min(pair)<5-1e-8 and max(pair)>2+1e-8 for pair in s)
            check('No invented bridge across gap',int(crossing),0)
            check('Ray inside gap has no surface',surface.pick([3,0,150],[0,0,-1]),None)
            _,_,components=geometry.section_plot_data(segments)
            check('Two disconnected section components',len(set(components)),2)
        else:
            segments=surface.section_segments([0,0],[6,0])
            check('Vertical wall station',segments[:,:,0],np.full_like(segments[:,:,0],3.))
            check('Vertical wall section length',np.linalg.norm(np.diff(segments,axis=1),axis=2).sum(),4)

    for name,callback in [('NaN measurement',lambda:geometry.distance_components([0,0,0],[0,np.nan,1])),
                          ('Zero section span',lambda:surface.section_segments([0,0],[0,0]))]:
        try:callback(); rejected=False
        except ValueError:rejected=True
        check(name+' rejected',int(rejected),1)
    module=Path(geometry.__file__)
    report=dict(passed=all(row['passed'] for row in checks),checks=checks,
                engine=str(module),sha256=hashlib.sha256(module.read_bytes()).hexdigest(),
                scope='Length, signed height, slope, exact mesh section, PLY precision, gaps and vertical walls. No reconstruction, area or volume certification.')
    (output/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    rows=''.join('<tr><td>'+html.escape(row['name'])+'</td><td>'+('PASS' if row['passed'] else 'FAIL')+
                 '</td><td>'+html.escape(str(row['absolute_error']))+'</td></tr>' for row in checks)
    (output/'report.html').write_text('<!doctype html><meta charset="utf-8"><title>Reference survey audit</title>'
        '<style>body{font:16px sans-serif;max-width:1100px;margin:30px auto}td,th{padding:7px;border:1px solid #ccc}table{border-collapse:collapse}</style>'
        f'<h1>{"PASS" if report["passed"] else "FAIL"}: {len(checks)} reference comparisons</h1>'
        '<p>Known plane: horizontal 5, height 12, straight 3D length 13. Broken ramp: horizontal 10, height 4, straight chord sqrt(116), surface profile 12. These are different quantities.</p>'
        '<p>Numbers are model units; the reference projects define one unit as one metre. Absolute tolerances are recorded in report.json. Passing does not certify reconstructed field data.</p>'
        '<table><tr><th>Comparison</th><th>Status</th><th>Absolute error</th></tr>'+rows+'</table>',encoding='utf-8')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();sys.dont_write_bytecode=True
    result=run_checks(args.app,args.output)
    print(json.dumps(dict(passed=result['passed'],comparisons=len(result['checks']),engine=result['engine'])))
    raise SystemExit(0 if result['passed'] else 1)
