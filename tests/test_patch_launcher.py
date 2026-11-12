"""Exercise real Windows PowerShell native process argument transport."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

spec = importlib.util.spec_from_file_location(
    "launcher", Path(__file__).parents[1] / "packaging/make_patch_launcher.py")
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows PowerShell regression")
@pytest.mark.parametrize("root", [
    "C:\\Users\\Behdad\\AppData\\Local\\Programs\\PhotoMesh Studio\\",
    "C:\\برنامه فارسی\\Lens & Mesh's\\",
    "C:\\",
    "\\\\server\\share\\folder with spaces\\",
])
def test_native_path_handoff(tmp_path, root):
    payload = tmp_path / "payload فارسی with spaces"
    payload.mkdir()
    result = tmp_path / "result.json"
    (payload / "apply_patch.py").write_text(
        "import json,os,sys\n"
        "with open(os.environ['LM_TEST_RESULT'],'w',encoding='utf-8') as f: json.dump(sys.argv[1:],f)\n",
        encoding="utf-8")
    payload_arg = str(payload) + "\\"
    env = dict(os.environ, LM_TEST_ROOT=root, LM_TEST_PAYLOAD=payload_arg,
               LM_TEST_PYTHON=sys.executable, LM_TEST_RESULT=str(result))
    script = ("$ErrorActionPreference='Stop'; $root=$env:LM_TEST_ROOT; "
              "$payload=$env:LM_TEST_PAYLOAD; $py=$env:LM_TEST_PYTHON;\n"
              + launcher.NATIVE_HANDOFF + "\nexit $LASTEXITCODE")
    process = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        env=env, capture_output=True, text=True, errors="replace", timeout=30)
    assert process.returncode == 0, process.stdout + process.stderr
    assert json.loads(result.read_text(encoding="utf-8")) == [
        "--root", root, "--payload", payload_arg]
