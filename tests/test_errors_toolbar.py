"""Reported high-resolution ONNX and Windows publication regressions."""
import os
from types import SimpleNamespace
import pytest
from photomesh import engine, workflow


def test_aliked_size_policy_preserves_other_methods():
    for method in ("SIFT", "SIFT + LightGlue"):
        assert engine.extraction_size(5472, {"feature_method": method}) == 5472
    assert engine.extraction_size(5472, {"feature_method": "ALIKED + LightGlue"}) == 2048
    assert engine.extraction_size(1024, {"feature_method": "ALIKED + LightGlue"}) == 1024


@pytest.mark.parametrize("mode", ["Fast", "Exhaustive", "Sequential"])
def test_reported_aliked_size_is_bounded_in_all_builders(tmp_path, monkeypatch, mode):
    from photomesh import colmap
    options = {"FeatureExtraction.max_image_size", "FeatureExtraction.type",
               "FeatureExtraction.num_threads", "FeatureExtraction.use_gpu",
               "AlikedExtraction.n16rot_model_path", "AlikedExtraction.max_num_features",
               "FeatureMatching.type", "FeatureMatching.num_threads",
               "AlikedMatching.lightglue_model_path"}
    monkeypatch.setattr(colmap, "colmap_options", lambda *_: options)
    monkeypatch.setattr(colmap, "image_max_dim", lambda *_: 5472)
    monkeypatch.setattr(engine, "gpu_device", lambda *_: None)
    monkeypatch.setattr(engine, "verified_model", lambda *a: "/offline/" + a[-1])
    settings = {"accuracy": "High", "mode": mode, "feature_method": "ALIKED + LightGlue",
                "key_point_limit": 2048, "use_gpu": False, "mapper": "Incremental"}
    chunk = SimpleNamespace(cameras=[SimpleNamespace(path="a.jpg", enabled=True)] * 2)
    steps = colmap.align_steps("engine", chunk, str(tmp_path), settings,
                               ["a.jpg", "b.jpg"], [{"width": 5472, "height": 3648}] * 2)
    args = next(args for _, args, _ in steps
                if isinstance(args, list) and args and args[0] == "feature_extractor")
    assert args[args.index("--FeatureExtraction.max_image_size") + 1] == "2048"
    assert args[args.index("--FeatureExtraction.num_threads") + 1] == "1"
    if mode == "Fast":
        labels = [label for label, _, _ in steps]
        assert labels.index("Rescaling key points") < labels.index("Grouping cameras")


@pytest.mark.parametrize("winerror", [5, 32, 33])
def test_publication_retries_windows_locks(tmp_path, monkeypatch, winerror):
    stage, target = tmp_path / "stage", tmp_path / "product"
    stage.mkdir(); target.mkdir()
    (stage / "new").write_text("complete")
    (target / "old").write_text("healthy")
    replace = os.replace
    failed = []
    def locked(source, destination):
        if str(source) == str(stage) and not failed:
            failed.append(True)
            error = PermissionError("temporary sharing lock"); error.winerror = winerror
            raise error
        replace(source, destination)
    monkeypatch.setattr(workflow.os, "replace", locked)
    monkeypatch.setattr(workflow.time, "sleep", lambda _: None)
    workflow.publish_directory(str(stage), str(target))
    assert (target / "new").read_text() == "complete"
    assert not (tmp_path / "product.previous").exists()


def test_persistent_publication_lock_retains_completed_build_and_old_output(tmp_path, monkeypatch):
    target = tmp_path / "product"; target.mkdir()
    (target / "old").write_text("healthy")
    real_replace = os.replace
    def locked(source, destination):
        if ".building-" in str(source):
            error = PermissionError("locked"); error.winerror = 5
            raise error
        real_replace(source, destination)
    monkeypatch.setattr(workflow.os, "replace", locked)
    monkeypatch.setattr(workflow.time, "sleep", lambda _: None)
    @workflow.product_transaction
    def build(cfg):
        from pathlib import Path
        (Path(cfg["out_dir"]) / "new").write_text("complete")
        return {"dir": cfg["out_dir"]}
    with pytest.raises(OSError, match="Completed files were retained"):
        build({"out_dir": str(target)})
    assert (target / "old").read_text() == "healthy"
    stages = list(tmp_path.glob("product.building-*"))
    assert len(stages) == 1 and (stages[0] / "new").read_text() == "complete"


def test_publication_does_not_retry_disk_errors(monkeypatch):
    calls = []
    def fail(*args):
        calls.append(args); raise OSError("disk failure")
    monkeypatch.setattr(workflow.os, "replace", fail)
    with pytest.raises(OSError, match="disk failure"):
        workflow.replace_output("source", "target")
    assert len(calls) == 1


def test_toolbar_separates_processing_display_and_view(window):
    from PySide6.QtWidgets import QToolButton
    process_names = {a.text() for a in window.processing_toolbar.actions()}
    assert {"Align Photos...", "Build Point Cloud...", "Build Model..."} <= process_names
    display_actions = window.display_toolbar.actions()
    for key in ("tie", "cloud", "mesh"):
        assert window.layer_action(key) not in display_actions
    for key, button in zip(("tie", "cloud", "mesh"), window.mode_buttons):
        assert button.popupMode() == QToolButton.InstantPopup
        window.set_layer_visible(key, False)
        assert "Hidden" in button.toolTip() and button.hidden_action.isChecked()
        window.set_layer_visible(key, True)
        assert "Hidden" not in button.toolTip() and not button.hidden_action.isChecked()
        button.hidden_action.trigger()
        assert not window.layer_action(key).isChecked()
        button.hidden_action.trigger()
        assert button.hidden_action.isChecked() and "Hidden" in button.toolTip()
    window.actions["View/Toolbar"].setChecked(False)
    assert all(tb.isHidden() for tb in window.toolbars)
    window.actions["View/Toolbar"].setChecked(True)
    assert all(not tb.isHidden() for tb in window.toolbars)


def test_predefined_views_switch_from_photo_and_preserve_zoom(window, monkeypatch):
    called = []
    monkeypatch.setattr(window.model_view, "set_predefined", called.append)
    window.tabs.setCurrentWidget(window.photo_view)
    window.actions["Top"].trigger()
    assert called == ["Top"] and window.tabs.currentWidget() == window.model_view
    window.actions["Isometric"].trigger()
    assert called[-1] == "Isometric"


def test_alignment_summary_discloses_aliked_resolution(window):
    from photomesh.project import Camera
    from photomesh.dialogs import AlignPhotosDialog
    window.chunk.cameras = [Camera("a.jpg", width=5472, height=3648)]
    dialog = AlignPhotosDialog(window)
    dialog.feature_method.setCurrentText("ALIKED + LightGlue")
    assert "2048" in dialog.summary.text() and "ONNX memory" in dialog.summary.text()
