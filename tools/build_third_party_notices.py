"""Build an offline notice index from authenticated runtime audit evidence."""
import argparse
import hashlib
from html import escape
import json
from pathlib import Path
import shutil
import zipfile


def build(inventory, evidence, upstream, output):
    data = json.loads(inventory.read_text(encoding='utf-8'))
    output.mkdir(parents=True, exist_ok=True)
    packages = [p for p in data['packages'] if p['name']]
    record = dict(schema=1, inventory_sha256=hashlib.sha256(inventory.read_bytes()).hexdigest(),
        evidence_sha256=hashlib.sha256(evidence.read_bytes()).hexdigest(), packages=packages,
        engineering_review_complete=True, redistribution_clearance=False,
        release_blockers=[
            'Exact corresponding-source/build metadata for all native engine dependencies is not established by DLL names.',
            'Qt/PySide split Pdf/WebEngine 6.12.0.140 provenance and version-matched source need confirmation.',
            'Modern and legacy CUDA runtime terms must be matched to exact redistributed DLL versions.',
        ])
    record['native_and_weights'] = [f for f in data['files'] if f['path'].startswith('tools/') and
                                   Path(f['path']).suffix.lower() in ('.dll', '.exe', '.onnx')]
    record['upstream'] = json.loads((upstream/'provenance.json').read_text())
    (output/'review.json').write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8')
    sections = []
    with zipfile.ZipFile(evidence) as archive:
        for name in sorted(archive.namelist()):
            leaf = Path(name).name.lower()
            if not any(s in leaf for s in ('license', 'licence', 'notice', 'copyright', 'copying')):
                continue
            text = archive.read(name).decode('utf-8', 'replace')
            sections.append(f'<details><summary>{escape(name)}</summary><pre>{escape(text)}</pre></details>')
    for name in ('GPL-3.0.txt', 'LGPL-3.0.txt', 'LGPL-2.1.txt', 'GCC-exception-3.1.txt',
                 'COLMAP-4.2.1.txt', 'GLOMAP-LICENSE.txt', 'LightGlue-ONNX-LICENSE.txt', 'ALIKED-ONNX-LICENSE.txt'):
        shutil.copyfile(upstream/name, output/name)
        sections.append(f'<details><summary>{escape(name)}</summary><pre>{escape((upstream/name).read_text(encoding="utf-8"))}</pre></details>')
    rows = ''.join('<tr><td>'+escape(p['name'])+'</td><td>'+escape(p['version'])+'</td><td>'+
                   escape(p.get('license_expression') or str(p.get('license') or 'See collected notices'))+'</td></tr>' for p in packages)
    html = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Lens2Mesh — Third-party Notices</title><style>
body{font:16px system-ui,sans-serif;max-width:1100px;margin:2em auto;padding:0 1em;color:#20242a;background:#fff}
table{border-collapse:collapse;width:100%}td,th{border:1px solid #bbb;padding:.5em;text-align:left;vertical-align:top}
td{max-width:400px;overflow-wrap:anywhere;white-space:pre-wrap}pre{white-space:pre-wrap;overflow-wrap:anywhere}
summary{cursor:pointer;padding:.6em;background:#eef2f4}details{margin:.6em 0}a{color:#145c92}
</style><h1>Third-party Notices</h1>
<p>Third-party software retains its own licenses and copyrights. Lens2Mesh's
personal and educational non-commercial license does not restrict the rights
granted by these component licenses. These are collected upstream notices,
not a change to the application's own license.</p>
<h2>Qt / PySide6</h2><p>The application uses dynamically linked Qt / PySide6
libraries. Where LGPL terms apply, you may replace or modify those libraries and
debug those modifications. No additional restriction on those rights is imposed
by the application's license. Full GPL and LGPL texts are provided below.</p>
<p>To test a replacement: close the application, back up the installation, and
use compatible 64-bit Windows CPython 3.13 bindings and matching Qt/PySide6 6.12
shared libraries. The folders are <code>python/Lib/site-packages/PySide6</code>
and <code>python/Lib/site-packages/shiboken6</code>. Keep native ABI and required
platform/image plugins consistent. The application contains editable Python
sources in <code>app/photomesh</code>; it does not embed a static Qt copy. Test
startup, rendering and processing after replacement. Restore the backup if needed.
The incremental updater intentionally rejects a changed baseline instead of
overwriting your replacement; ordinary application launch does not enforce its
Qt file hashes.</p>
<p>Versioned sources and build instructions:
<a href="https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.12.0-src/">PySide6 6.12.0 sources</a>,
<a href="https://download.qt.io/official_releases/qt/6.12/6.12.0/">Qt 6.12.0 sources</a>,
<a href="https://doc.qt.io/qtforpython-6/building_from_source/index.html">Qt for Python build instructions</a>.
Do not assume these links establish the exact source of every split-package or
native engine binary; outstanding provenance is recorded in the review.</p>
<h2>Reconstruction and learned models</h2>
<p>COLMAP and GLOMAP are separate processing executables. COLMAP's own BSD
license does not replace the licenses of its linked dependencies. The ALIKED
model/ONNX export is BSD-3-Clause; the LightGlue authors explicitly license
their pretrained weights and code under Apache-2.0. The bundle contains the
ALIKED and SIFT variants, not SuperPoint weights. Upstream licenses are below.</p>
<p>Sources:
<a href="https://github.com/colmap/colmap/tree/4.2.1">COLMAP 4.2.1</a>,
<a href="https://github.com/colmap/glomap">GLOMAP</a>,
<a href="https://github.com/colmap/ALIKED-ONNX">ALIKED ONNX</a>,
<a href="https://github.com/colmap/LightGlue-ONNX">LightGlue ONNX</a>.
The <a href="https://docs.nvidia.com/cuda/archive/13.2.0/eula/index.html">CUDA 13.2 terms</a>
are a versioned review reference, not evidence of the rights for every legacy or
CUDA12 library mentioned by an optional provider.
Native dependencies and model hashes are listed in the <a href="review.json">engineering review record</a>.
That record explicitly retains unresolved release provenance; this page does
not certify complete redistribution clearance.</p>
<h2>Python distributions in the audited candidate</h2>
<p>Optional unused Qt addons were removed using an exact hash-bound dependency
review. Distribution metadata is retained for version attribution; it is not a
claim that every optional module from those distributions remains installed.</p>
<table><tr><th>Component</th><th>Version</th><th>Upstream metadata</th></tr>'''+rows+'''</table>
<h2>Collected license and copyright texts</h2>'''+''.join(sections)+'</html>\n'
    (output/'index.html').write_text(html, encoding='utf-8')
    print(f'Offline notices: {len(packages)} distributions, {len(sections)} collected texts')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--upstream', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    build(args.inventory, args.evidence, args.upstream, args.output)
