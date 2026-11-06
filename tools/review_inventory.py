"""Read-only repository inventory for manual release review; findings are leads."""
from __future__ import annotations
import ast
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    files = sorted(path for path in ROOT.rglob("*.py")
                   if not any(part in {".git", "__pycache__", ".venv", "release-stage"}
                              for part in path.relative_to(ROOT).parts))
    modules, duplicates, definitions = [], defaultdict(list), []
    references = Counter()
    failures = []
    for path in files:
        rel = path.relative_to(ROOT).as_posix()
        source = path.read_text(encoding="utf-8-sig")
        tree = ast.parse(source, filename=rel)
        application = rel.startswith("photomesh/")
        refs = Counter(node.id for node in ast.walk(tree) if isinstance(node, ast.Name))
        refs.update(node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute))
        references.update(refs)
        funcs, imports, writes = [], [], []
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.append({"line": node.lineno, "module": getattr(node, "module", None),
                                "level": getattr(node, "level", 0),
                                "names": [name.name for name in node.names]})
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                entry = {"name": node.name, "line": node.lineno,
                         "lines": node.end_lineno - node.lineno + 1,
                         "branches": sum(isinstance(n, (ast.If, ast.For, ast.While, ast.Try,
                                                       ast.IfExp, ast.ExceptHandler)) for n in ast.walk(node))}
                funcs.append(entry)
                if application:
                    definitions.append(dict(entry, path=rel))
                    body = list(node.body)
                    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                        body = body[1:]
                    if len(body) >= 5:
                        normalized = ast.dump(ast.Module(body=body, type_ignores=[]), include_attributes=False)
                        duplicates[hashlib.sha256(normalized.encode()).hexdigest()].append(
                            {"path": rel, "name": node.name, "line": node.lineno})
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in {"remove", "unlink", "rmtree", "replace", "rename", "write_text", "write_bytes"}:
                    writes.append({"line": node.lineno, "call": ast.unparse(node.func)})
        if application:
            modules.append({"path": rel, "lines": len(source.splitlines()),
                            "imports": imports, "functions": funcs, "file_mutations": writes})
    for flag in ("F401", "F811", "F841", "F821,F822,F823"):
        result = subprocess.run([sys.executable, "-m", "ruff", "check", "--select", flag,
                                 "--output-format", "json", "photomesh"], cwd=ROOT,
                                capture_output=True, text=True)
        if result.returncode not in (0, 1):
            raise RuntimeError(result.stderr)
        failures.extend(json.loads(result.stdout))
    report = {"python_files_including_tests_tools": len(files),
              "application_modules": modules,
              "exact_nontrivial_body_duplicate_candidates": [v for v in duplicates.values() if len(v) > 1],
              "unreferenced_name_candidates": [d for d in definitions if references[d["name"]] == 0],
              "large_function_candidates": sorted((d for d in definitions if d["lines"] >= 100
                                                    or d["branches"] >= 20),
                                                   key=lambda d: -d["lines"]),
              "static_leads": failures,
              "note": "Not a deletion list. Qt hooks, callbacks, dynamic imports, task names and resources need manual review."}
    target = ROOT / "review"
    target.mkdir(exist_ok=True)
    (target / "inventory.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({key: len(value) if isinstance(value, list) else value
                      for key, value in report.items() if key != "note"}), flush=True)


if __name__ == "__main__":
    main()
