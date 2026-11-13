"""Prepare an exact reviewed unused-Qt removal list from remote evidence."""
import argparse
import hashlib
import json
from pathlib import Path

PREFIX = 'python/Lib/site-packages/PySide6/'
QML = ('qml/QtCharts/', 'qml/QtDataVisualization/', 'qml/QtGraphs/', 'qml/QtQuick3D/',
       'qml/QtQuick/Timeline/', 'qml/QtQuick/VirtualKeyboard/')


def plan(inventory, native, output, optional_web=False):
    inv = json.loads(inventory.read_text(encoding='utf-8'))
    report = json.loads(native.read_text(encoding='utf-8'))
    removed = set(report['qt_review_targets'])
    if optional_web:
        removed |= {r['path'] for r in report['modules'] if r['path'].startswith(PREFIX)
                    and Path(r['path']).name.startswith(('Qt6Pdf', 'Qt6WebEngine', 'Qt6WebView',
                                                          'QtPdf', 'QtWebEngine', 'QtWebView'))}
    while True:
        names = {Path(p).name.casefold() for p in removed}
        consumers = {r['path'] for r in report['modules'] if
                     any(n.casefold() in names for n in r['imports']+r['delayed'])}
        if consumers <= removed:
            break
        removed |= consumers
    assert all(p.startswith(PREFIX) for p in removed), 'Consumer outside reviewed PySide6 scope'
    binding_stems = {Path(p).stem for p in removed if p.endswith('.pyd')}
    files = []
    qml = QML + (('qml/QtQuick/Pdf/', 'qml/QtWebEngine/', 'qml/QtWebView/') if optional_web else ())
    for entry in inv['files']:
        path = entry['path']
        if not path.startswith(PREFIX):
            continue
        relative = path[len(PREFIX):]
        web_resource = optional_web and (
            relative.startswith(('resources/qtwebengine_', 'translations/qtwebengine_'))
            or relative in ('resources/icudtl.dat', 'resources/v8_context_snapshot.bin'))
        if (path in removed or relative.startswith(qml) or web_resource or
                (Path(relative).parent == Path('.') and Path(relative).stem in binding_stems)):
            files.append(dict(path=path, sha256=entry['sha256'], bytes=entry['bytes']))
    result = dict(schema=1, scope='Reviewed unused GPL-only Qt addon families and their static consumers; exact 1.0.4 bytes',
        native_evidence_sha256=hashlib.sha256(native.read_bytes()).hexdigest(), files=files)
    if optional_web:
        result['scope'] = 'Candidate review only: unused GPL addons plus optional Pdf/WebEngine/WebView PE consumers and QML; requires installed behavior validation before adoption'
    output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(f'Reviewed removal: {len(files)} files, {sum(f["bytes"] for f in files)/2**20:.1f} MiB; {len(removed)} PE files')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--native', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--optional-web', action='store_true')
    args = parser.parse_args()
    plan(args.inventory, args.native, args.output, args.optional_web)
