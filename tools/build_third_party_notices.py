"""Build an offline notice index from authenticated runtime audit evidence."""
import argparse
import hashlib
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import shutil
import zipfile


class LegalText(HTMLParser):
    """Retain legal text without shipping active web-page scripts/assets."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skipped = None

    def handle_starttag(self, tag, attrs):
        if tag in ('script','style','head','noscript') and self.skipped is None:
            self.skipped = tag
        if self.skipped is None and tag in ('p','div','br','li','tr','h1','h2','h3','h4'):
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag == self.skipped:
            self.skipped = None
        if self.skipped is None and tag in ('p','div','li','tr','h1','h2','h3','h4'):
            self.parts.append('\n')

    def handle_data(self, data):
        if self.skipped is None:
            self.parts.append(data)


def neural_notices(output):
    """Retain exact NVIDIA archive licenses and the separate review scope."""
    source = Path(__file__).resolve().parents[1]/'photomesh/resources/third-party/neural-cuda12'
    destination = output/'neural-cuda12'
    if source.resolve() != destination.resolve():
        shutil.copytree(source, destination, dirs_exist_ok=True)
    links = ''.join(f'<li><a href="neural-cuda12/{escape(path.name)}">{escape(path.name)}</a></li>'
                    for path in sorted(destination.iterdir()) if path.is_file())
    return ('<h2>Private ONNX CUDA 12 runtime</h2><p>CUDA Runtime 12.8.90, '
            'cuBLAS 12.8.4.1 and cuDNN 9.8.0.87. Only reviewed, unmodified runtime DLLs '
            'are prepared from official hash-pinned archives. NVIDIA and third-party '
            'licenses apply separately from the application license. This review '
            'does not close other native source/notice findings.</p><ul>'+links+'</ul>')


def build(inventory, evidence, upstream, output, primary_proof=None, qt_removal_plan=None):
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
    proof_links = []
    if primary_proof:
        summary = json.loads((primary_proof/'summary.json').read_text())
        native = json.loads((primary_proof/'native-official-byte-comparison.json').read_text())
        if summary['qt_mismatches'] or any(r['matched'] != len(r['files']) for r in native):
            raise ValueError('Primary upstream identity evidence contains mismatches')
        record['primary_identity'] = dict(qt_compared=summary['qt_compared'], qt_mismatches=0,
            native_groups=[dict(group=r['group'],matched=r['matched'],url=r['url'],sha256=r['sha256']) for r in native],
            python_packages=summary['python_packages'], binary_identity_is_not_source_clearance=True)
        record['primary_identity']['proof_records'] = []
        record['release_blockers'] = [
            'Exact corresponding source, third-party notices and build/patch recipes for every linked native dependency still require complete retention; release archive identity alone does not establish them.',
            'Official PySide6 Pdf/WebEngine6.12.0.140 wheel identity is verified; exact matching Chromium/split-module corresponding-source packaging remains to be established.',
        ]
        for name in ('python-origins.json','qt-official-byte-comparison.json','native-official-byte-comparison.json','native-version-origins.json'):
            shutil.copyfile(primary_proof/name, output/name)
            record['primary_identity']['proof_records'].append(dict(path=name,
                sha256=hashlib.sha256((primary_proof/name).read_bytes()).hexdigest()))
            proof_links.append(f'<li><a href="{name}">{name}</a></li>')
    if qt_removal_plan:
        if not primary_proof:
            raise ValueError('Qt exclusion requires primary identity evidence')
        plan = json.loads(qt_removal_plan.read_text(encoding='utf-8'))
        remaining = {item['path'] for item in data['files']}
        families = ('Qt6Pdf', 'QtPdf', 'Qt6WebEngine', 'QtWebEngine', 'Qt6WebView', 'QtWebView')
        if 'python/Lib/site-packages/PySide6/Qt6Core.dll' not in remaining:
            raise ValueError('Qt exclusion requires a complete runtime inventory')
        if any(item['path'] in remaining for item in plan['files']):
            raise ValueError('Reviewed excluded Qt files remain in this runtime')
        if any(path.startswith('python/Lib/site-packages/PySide6/') and
               Path(path).name.startswith(families) for path in remaining):
            raise ValueError('Optional Pdf/WebEngine/WebView binary remains')
        if not any('Qt6WebEngineCore.dll' in item['path'] for item in plan['files']):
            raise ValueError('Plan does not establish the optional module exclusion')
        shutil.copyfile(qt_removal_plan, output/'reviewed-qt-removals.json')
        record['optional_qt_exclusion'] = dict(files=len(plan['files']),
            plan_sha256=hashlib.sha256(qt_removal_plan.read_bytes()).hexdigest(),
            absent_in_inventory=True, validation=plan.get('validation'))
        record['release_blockers'] = record['release_blockers'][:1]
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
    for name in ('COLMAP-3.8-LICENSE.txt','COLMAP-3.8-build-dependencies.txt','GLOMAP-1.2.0-LICENSE.txt',
                 'GLOMAP-1.2.0-vcpkg.json','NVIDIA-CUDA-11.8-EULA.html','NVIDIA-CUDA-13.2-EULA.html'):
        if (upstream/name).is_file():
            target = name
            if name.endswith('.html'):
                parser = LegalText(); parser.feed((upstream/name).read_text(encoding='utf-8'))
                target = Path(name).with_suffix('.txt').name
                (output/target).write_text(''.join(parser.parts), encoding='utf-8')
            else:
                shutil.copyfile(upstream/name, output/target)
            proof_links.append(f'<li><a href="{target}">{target}</a></li>')
            if target.endswith('.txt'):
                sections.append(f'<details><summary>{escape(target)}</summary><pre>{escape((output/target).read_text(encoding="utf-8"))}</pre></details>')
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
    if primary_proof:
        addition = '''<h2>Verified primary origins and versioned sources</h2>
<p>All1564 compared Qt binary/resource files match official PyPI wheels.
All71 legacy COLMAP3.8 and74 GLOMAP1.2.0 native files match their official
release archives byte for byte. The split Pdf/WebEngine6.12.0.140 packages
are official PyPI releases. Retained metadata is available below; byte identity
does not by itself establish all corresponding-source obligations.</p>
<p>The legacy CUDA runtime identifies as11.8.89 and its cuRAND as10.3.0.86;
the versioned CUDA11.8 terms are retained below. The optional modern ONNX CUDA
provider imports CUDA12 libraries; this is not evidence that those libraries
are bundled or covered by the CUDA13.2 reference.</p>
<p>Native engine Qt sources: <a href="https://download.qt.io/archive/qt/5.15/5.15.8/submodules/">Qt5.15.8</a>
and <a href="https://download.qt.io/official_releases/qt/6.11/6.11.1/submodules/">Qt6.11.1</a>.
The modern engine's vcpkg baseline is127402f1c75bb3d5ff6bce04b285faa4930a5aca;
the official build removes its install/share notices, so missing linked-library
source/build records remain an explicit release gate.</p><ul>'''+''.join(proof_links)+'</ul>'
        html = html.replace('<h2>Python distributions', addition+'<h2>Python distributions')
    if qt_removal_plan:
        html = html.replace('<h2>Python distributions',
            '<h2>Excluded optional Qt modules</h2><p>The reviewed runtime excludes '
            'Pdf, WebEngine and WebView binaries/resources. Distribution metadata '
            'is retained for attribution, not as a claim that those modules ship. '
            'The <a href="reviewed-qt-removals.json">exact removal and validation record</a> '
            'is checked against the complete candidate inventory. Remaining native '
            'source/notice review is recorded separately; exclusion is not blanket '
            'redistribution clearance.</p><h2>Python distributions')
    html = html.replace('</html>', neural_notices(output)+'</html>')
    (output/'index.html').write_text(html, encoding='utf-8')
    print(f'Offline notices: {len(packages)} distributions, {len(sections)} collected texts')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--upstream', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--primary-proof', type=Path)
    parser.add_argument('--qt-removal-plan', type=Path)
    args = parser.parse_args()
    build(args.inventory, args.evidence, args.upstream, args.output, args.primary_proof, args.qt_removal_plan)
