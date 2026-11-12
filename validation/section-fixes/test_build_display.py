"""Completion must activate the published product in its owning project only."""
import pytest
from PySide6.QtCore import QObject, Signal


def runner(monkeypatch, before=None, success=True):
    from photomesh import colmap as cm

    class Runner(QObject):
        progress = Signal(int, str)
        detail = Signal(str)
        log = Signal(str)
        finished = Signal(bool, str)
        failure = None

        def __init__(self, *args):
            super().__init__()

        def start(self):
            if before:
                before()
            self.finished.emit(success, "" if success else "Cancelled by user")

        def cancel(self):
            pass

    monkeypatch.setattr(cm, "PipelineRunner", Runner)
    monkeypatch.setattr(cm, "find_colmap", lambda: "colmap")


@pytest.mark.parametrize("product", ["tie", "cloud", "mesh"])
def test_published_build_activates_product(window, tmp_path, monkeypatch, no_dialogs, product):
    import numpy as np
    from photomesh.plyio import save_ply
    path = tmp_path / "result.ply"
    save_ply(str(path), np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=float))
    runner(monkeypatch)
    window.set_all_layers(False)
    window.set_layer_visible("markers", True)
    window.set_layer_visible("cameras", True)
    window.tabs.setCurrentWidget(window.plan_view)
    window._run("Fixture Build", [], lambda: window.load_result(
        "model" if product == "mesh" else product, str(path)), product=product)
    assert window.tabs.currentWidget() is window.model_view
    for key in ("tie", "cloud", "mesh", "tiled"):
        assert window.layer_action(key).isChecked() == (key == product)
    assert window.layer_action("markers").isChecked()
    assert window.layer_action("cameras").isChecked()
    assert not no_dialogs


@pytest.mark.parametrize("change", ["project", "dataset"])
def test_stale_completion_never_runs_callbacks(window, monkeypatch, no_dialogs, change):
    from photomesh.project import Project
    original = window.dataset
    def switch():
        if change == "project":
            window.project = Project()
        else:
            window.project.datasets[window.project.active] = type(original)()
    runner(monkeypatch, before=switch)
    calls = []
    window._run("Fixture Build", [], lambda: calls.append("success"),
                meta=lambda *a: calls.append("metadata"),
                on_fail=lambda: calls.append("failure"), product="cloud")
    assert calls == []
    assert original.log and not window.dataset.log


@pytest.mark.parametrize("failure", ["cancel", "publish"])
def test_unsuccessful_build_does_not_activate(window, monkeypatch, no_dialogs, failure):
    runner(monkeypatch, success=failure != "cancel")
    window.tabs.setCurrentWidget(window.plan_view)
    window.set_all_layers(False)
    def publish():
        raise FileNotFoundError("Expected result missing")
    window._run("Fixture Build", [], publish, product="cloud")
    assert window.tabs.currentWidget() is window.plan_view
    assert not window.layer_action("cloud").isChecked()
