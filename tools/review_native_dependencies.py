"""Read PE dependency evidence on a disposable installed Windows runtime."""
import argparse
import json
from pathlib import Path
import pefile

GPL_QT = ('Charts', 'Graphs', 'DataVisualization', 'Quick3D', 'Quick3DPhysics',
          'VirtualKeyboard', 'QuickTimeline', 'Coap', 'Grpc', 'HttpServer',
          'Lottie', 'Mqtt', 'NetworkAuth', 'QmlCompiler', 'WaylandCompositor', 'CanvasPainter')


def inspect(root, output):
    root, output = Path(root), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    records = []
    for path in root.rglob('*'):
        if not path.is_file() or path.suffix.casefold() not in ('.exe', '.dll', '.pyd'):
            continue
        if '.lens2mesh-patches' in path.parts:
            continue
        record = dict(path=path.relative_to(root).as_posix(), imports=[], delayed=[])
        try:
            pe = pefile.PE(str(path), fast_load=True)
            pe.parse_data_directories(directories=[1, 13])
            for attribute, field in [('DIRECTORY_ENTRY_IMPORT', 'imports'), ('DIRECTORY_ENTRY_DELAY_IMPORT', 'delayed')]:
                record[field] = [entry.dll.decode('ascii', 'replace') for entry in getattr(pe, attribute, [])]
            pe.close()
        except pefile.PEFormatError as error:
            record['error'] = str(error)
        records.append(record)
    targets = [r for r in records if any(r['path'].rsplit('/', 1)[-1].startswith('Qt6'+module) for module in GPL_QT)]
    target_names = {r['path'].rsplit('/', 1)[-1].casefold() for r in targets}
    incoming = [dict(path=r['path'], requires=[n for n in r['imports']+r['delayed'] if n.casefold() in target_names])
                for r in records if any(n.casefold() in target_names for n in r['imports']+r['delayed'])]
    report = dict(scope='Exact published 1.0.4 disposable installation; static PE imports, not proof of dynamic non-use',
                  modules=records, qt_review_targets=[r['path'] for r in targets], incoming=incoming)
    (output/'native-dependencies.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(f'Read {len(records)} PE modules; {len(targets)} Qt review targets; {len(incoming)} direct consumers')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    inspect(args.root, args.output)
