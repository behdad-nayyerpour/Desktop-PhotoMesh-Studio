"""File pickers with per-operation directories; cancellation changes nothing."""
import hashlib
import os
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QFileDialog as NativeFileDialog


def _key(kind, caption):
    return "paths/dialogs/" + kind + "/" + hashlib.sha256(caption.encode("utf-8")).hexdigest()[:16]


def _initial(kind, caption, directory):
    if directory and os.path.isabs(directory):
        return directory
    settings = QSettings()
    folder = settings.value(_key(kind, caption), "", str)
    if not folder or not os.path.isdir(folder):
        folder = settings.value("paths/last_dialog_dir", "", str)
    if folder and os.path.isdir(folder):
        return os.path.join(folder, directory) if directory else folder
    return directory


def _remember(kind, caption, result):
    if not result:
        return
    folder = result if kind == "folder" else os.path.dirname(os.path.abspath(result))
    settings = QSettings()
    settings.setValue(_key(kind, caption), folder)
    settings.setValue("paths/last_dialog_dir", folder)


class QFileDialog:
    """Only static selection methods used by PhotoMesh; preserve Qt return types."""
    @staticmethod
    def getOpenFileName(parent=None, caption="", directory="", *args, **kwargs):
        result = NativeFileDialog.getOpenFileName(parent, caption, _initial("open", caption, directory), *args, **kwargs)
        _remember("open", caption, result[0])
        return result

    @staticmethod
    def getOpenFileNames(parent=None, caption="", directory="", *args, **kwargs):
        result = NativeFileDialog.getOpenFileNames(parent, caption, _initial("open", caption, directory), *args, **kwargs)
        _remember("open", caption, result[0][0] if result[0] else "")
        return result

    @staticmethod
    def getSaveFileName(parent=None, caption="", directory="", *args, **kwargs):
        result = NativeFileDialog.getSaveFileName(parent, caption, _initial("save", caption, directory), *args, **kwargs)
        _remember("save", caption, result[0])
        return result

    @staticmethod
    def getExistingDirectory(parent=None, caption="", directory="", *args, **kwargs):
        result = NativeFileDialog.getExistingDirectory(parent, caption, _initial("folder", caption, directory), *args, **kwargs)
        _remember("folder", caption, result)
        return result
