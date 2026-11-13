"""One-time repair of the desktop / Start-menu shortcut icon (Windows).

Older source/portable setups created "PhotoMesh Studio.lnk" with python(w).exe's
icon. When the repair helper is present, the app runs it once per version
(hidden, in the background, offline). The script changes only IconLocation
of shortcuts that start this install. Current Setup creates the correct icon."""
from __future__ import annotations

import os
import subprocess
import sys

KEY = "startup/shortcut_icon_checked"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "packaging", "fix_shortcut_icon.ps1")
MIGRATION_SCRIPT = os.path.join(ROOT, "packaging", "migrate_shortcuts.ps1")


def command(repo=ROOT):
    return ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
            "-File", SCRIPT, "-Repo", repo]


def maybe_fix(settings, version, popen=subprocess.Popen, platform=None):
    """Start the repair once per app version on Windows. Returns True if started."""
    if (platform or sys.platform) != "win32" or not os.path.exists(SCRIPT):
        return False
    if settings.value(KEY, "") == version:
        return False
    settings.setValue(KEY, version)
    try:
        popen(command(), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
              creationflags=0x08000000)        # CREATE_NO_WINDOW
    except Exception:  # noqa: BLE001 - cosmetic, never stop the app
        return False
    return True


def maybe_migrate(settings, version, popen=subprocess.Popen, platform=None):
    """Migrate this install's legacy per-user shortcut names once per version."""
    key = 'startup/lens2mesh_shortcut_migration'
    if ((platform or sys.platform) != 'win32' or not os.path.isfile(MIGRATION_SCRIPT)
            or settings.value(key, '') == version):
        return False
    try:
        popen(['powershell', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
               '-File', MIGRATION_SCRIPT, '-Repo', ROOT], stdin=subprocess.DEVNULL,
              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x08000000)
    except OSError:
        return False
    settings.setValue(key, version)
    return True
