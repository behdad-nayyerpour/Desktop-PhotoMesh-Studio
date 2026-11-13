"""Report only installation-owned processes relevant to the app-close guard."""
import json
import os
from pathlib import Path
import sys

import psutil

root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'packaging'))
import apply_patch as updater  # noqa: E402

parents = {p.pid for p in psutil.Process().parents()}
records = []
for process in psutil.process_iter(['pid', 'exe', 'cmdline', 'ppid']):
    try:
        exe = Path(process.info['exe'] or '').resolve()
        args = process.info['cmdline'] or []
        own_python = exe.is_relative_to(root / 'python')
        app_argument = any(str(root / 'app').casefold() in arg.casefold() for arg in args)
        if own_python or app_argument:
            records.append(dict(pid=process.pid, parent=process.info['ppid'], exe=str(exe),
                                own_python=own_python, app_argument=app_argument,
                                ancestor=process.pid in parents, self=process.pid == os.getpid(),
                                scripts=[Path(arg.strip('"')).name for arg in args if arg.strip('"').endswith('.py')]))
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
try:
    updater.ensure_closed(root)
    guard = 'passed'
except RuntimeError as error:
    guard = str(error)
print(json.dumps(dict(pid=os.getpid(), executable=sys.executable, guard=guard, matching_processes=records), indent=2))
