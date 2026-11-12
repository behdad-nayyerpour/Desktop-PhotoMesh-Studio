"""Offline, exact-version dependencies for the Windows incremental candidate."""
import importlib
from pathlib import Path
import sys


def laspy():
    if sys.platform == "win32" and sys.version_info[:2] == (3, 13):
        vendor = str(Path(__file__).resolve().parent / "_vendor")
        if vendor not in sys.path:
            sys.path.insert(0, vendor)
    return importlib.import_module("laspy")
