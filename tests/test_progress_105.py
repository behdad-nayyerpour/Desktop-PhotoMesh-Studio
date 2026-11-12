"""Progress presentation and ETA behavior under changing real workloads."""
from photomesh.progress import WorkProgress, fmt_eta


def test_eta_needs_samples_and_expires_without_new_work():
    now = [0.0]
    meter = WorkProgress(clock=lambda: now[0])
    for when, done in ((0, 1), (4, 3)):
        now[0] = when
        meter.update(done, 10)
        assert meter.remaining() is None
    now[0] = 8
    meter.update(5, 10)
    assert meter.remaining() == 10
    now[0] = 10
    assert meter.remaining() == 10  # Do not invent throughput while idle.
    now[0] = 30
    assert meter.remaining() is None
    assert meter.done == 5 and "estimating" in meter.text()


def test_cache_burst_and_new_workload_hide_unreliable_eta():
    now = [0.0]
    meter = WorkProgress(clock=lambda: now[0])
    for when, done in ((0, 1), (5, 51), (10, 52)):
        now[0] = when
        meter.update(done, 100)
    assert meter.remaining() is None
    meter.update(1, 200)
    assert meter.remaining() is None and len(meter.samples) == 1
    meter.update(float("nan"), 200)
    assert meter.done == 1
    assert fmt_eta(float("inf")) == ""


def test_single_counter_has_one_bar_and_pipeline_keeps_distinct_bars(qtbot):
    from photomesh.dialogs import ProgressDialog
    from photomesh.activity import ProgressPanel
    dialog = ProgressDialog("Processing")
    qtbot.addWidget(dialog)
    assert dialog.bar.isHidden() and not dialog.stage_bar.isHidden()
    dialog.set_operation_steps(4)
    assert not dialog.bar.isHidden()
    dialog.set_progress(25, "Next step")
    dialog.set_stage_progress(.7, "7/10")
    assert dialog.bar.value() == 250 and dialog.stage_bar.value() == 700
    dialog.begin_stage()
    assert dialog.stage_bar.maximum() == 0 and not dialog._meter.samples
    dialog.set_operation_steps(1)
    assert dialog.bar.isHidden()
    panel = ProgressPanel()
    qtbot.addWidget(panel)
    panel.update_progress(1, 10, "Importing files")
    assert not panel.overall.isHidden() and panel.subtask.isHidden()
    dialog.running = False


def test_completed_work_is_not_published_result(qtbot):
    from photomesh.dialogs import ProgressDialog
    dialog = ProgressDialog("Build")
    qtbot.addWidget(dialog)
    dialog.set_progress(100, "Finished")
    dialog.set_stage_progress(1, "Computed")
    assert dialog.bar.value() < 1000 and dialog.stage_bar.value() < 1000
    assert "Finalizing" in dialog.stage.text()
    dialog.finish_success()
    assert dialog.bar.value() == dialog.stage_bar.value() == 1000
    dialog.running = False


def test_depth_pass_change_discards_previous_rate(qtbot):
    from photomesh.dialogs import ProgressDialog
    dialog = ProgressDialog("Cloud")
    qtbot.addWidget(dialog)
    now = [0.0]
    dialog._meter = WorkProgress(clock=lambda: now[0])
    for when, fraction in ((0, .1), (5, .2), (10, .3)):
        now[0] = when
        dialog.set_stage_progress(fraction, "Depth maps: photometric pass 4/10")
    assert dialog._meter.remaining() is not None
    dialog.set_stage_progress(.5, "Depth maps: geometric pass 1/10")
    assert dialog._meter.remaining() is None
    dialog.running = False
