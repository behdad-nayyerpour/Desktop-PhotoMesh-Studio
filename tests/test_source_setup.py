"""Source launch, line endings, and protection of local user data."""
import os
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(rel):
    with open(os.path.join(ROOT, rel), "rb") as f:
        return f.read()


def test_run_stops_if_first_time_setup_fails():
    s = _read("run.bat").decode()
    assert "call setup.bat || exit /b 1" in s
    assert 'if not exist .venv\\Scripts\\pythonw.exe (' in s


def test_gitattributes_line_endings():
    s = _read(".gitattributes").decode()
    assert "*.bat  text eol=crlf" in s and "*.ps1  text eol=crlf" in s and "*.py   text eol=lf" in s


@pytest.mark.skipif(not shutil.which("git") or not os.path.isdir(os.path.join(ROOT, ".git")),
                    reason="needs a git checkout")
def test_gitignore_keeps_user_data_out():
    paths = [".venv/Scripts/python.exe", "proj/site.pmsx", "proj/site.files/x.bin", "photomesh/__pycache__/a.pyc",
             "dist/x.zip", "bench_drone5/a.ply", "tools/colmap/bin/colmap.exe", "memtest/x", "sync_a.zip",
             ".pytest_cache/v", "photos/DJI_0001.JPG", "run.log", ".env", ".vscode/settings.json"]
    r = subprocess.run(["git", "-C", ROOT, "check-ignore", "--no-index", "-v", *paths], capture_output=True, text=True)
    ignored = {l.split("\t")[-1] for l in r.stdout.splitlines()}
    assert ignored == set(paths), set(paths) - ignored
    keep = ["photomesh/dense.py", "tests/data/shapes/fi.shp", "packaging/build_release.ps1", "tools/e2e_test.py"]
    r = subprocess.run(["git", "-C", ROOT, "check-ignore", "--no-index", *keep], capture_output=True, text=True)
    assert r.stdout.strip() == ""

