"""Progress meters for long COLMAP steps: smooth fraction, pass and ETA parsed
from the tool's console output (PipelineRunner feeds every line).

PatchMatchMeter  patch_match_stereo prints "Processing view i / N for <name>"
                 once per computed view and pass: with geometric consistency
                 first a photometric pass over all views, then a geometric one.
                 Views whose maps already exist are skipped silently, so the
                 expected counts are passed in (see dense.patch_match_meter).
FusionMeter      stereo_fusion prints "Reading workspace...", then
                 "Fusing image [k/N] with index i ... in 1.2s (123456 points)".
"""
from __future__ import annotations

import re
import time
import math
from statistics import median

_VIEW = re.compile(r"Processing view\s+(\d+)\s*/\s*(\d+)")
_FUSE = re.compile(r"Fusing image \[(\d+)/(\d+)\]")
_POINTS = re.compile(r"\((\d+) points\)")


def fmt_eta(seconds):
    if seconds is None or not math.isfinite(seconds) or seconds < 0:
        return ""
    s = int(round(seconds))
    if s < 60:
        return f"{s} s"
    m = s // 60
    if m < 60:
        return f"{m} min"
    return f"{m // 60} h {m % 60:02d} min"


class _Meter:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.work = WorkProgress(clock)

    def _eta(self, done, total):
        """Remaining time from the rate since the first counted item."""
        self.work.update(done, total)
        return self.work.remaining()


class PatchMatchMeter(_Meter):
    def __init__(self, todo_photometric, todo_geometric, views=None, clock=time.monotonic):
        super().__init__(clock)
        self.todo_p = max(0, int(todo_photometric))
        self.todo_g = max(0, int(todo_geometric))
        self.views = views
        self.count = 0

    @property
    def total(self):
        return max(1, self.todo_p + self.todo_g)

    def feed(self, line):
        m = _VIEW.search(line)
        if not m:
            return None
        self.count += 1
        if self.views is None:
            self.views = int(m.group(2))
        # Only previous views are known complete; a just-started view is not half finished.
        frac = min(1.0, (self.count - 1) / self.total)
        if self.count <= self.todo_p:
            what = f"photometric pass {self.count}/{self.todo_p}"
        else:
            what = f"geometric pass {self.count - self.todo_p}/{self.todo_g}"
        eta = self._eta(self.count - 1, self.total)
        return frac, f"Depth maps: {what}" + (f" - about {fmt_eta(eta)} left" if eta else "")


class FusionMeter(_Meter):
    def __init__(self, images=None, clock=time.monotonic):
        super().__init__(clock)
        self.images = images
        self.points = 0

    def feed(self, line):
        p = _POINTS.search(line)
        if p:
            self.points = int(p.group(1))
        if "Reading workspace" in line:
            return 0.0, "Fusion: loading depth maps"
        m = _FUSE.search(line)
        if not m:
            return None
        k, n = int(m.group(1)), int(m.group(2))
        self.images = n
        eta = self._eta(k - 1, n)
        txt = f"Fusion: image {k}/{n}"
        if self.points:
            txt += f", {self.points / 1e6:.1f} M points"
        return min(1.0, (k - 1) / max(1, n)), txt + (f" - about {fmt_eta(eta)} left" if eta else "")


class WorkProgress:
    """Observed work only. Unknown totals stay indeterminate; ETA needs a measured rate."""
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.reset()

    def reset(self):
        self.start = self.clock()
        self.done, self.total = 0, 0
        self.samples = []

    def update(self, done, total):
        if not math.isfinite(float(done)) or not math.isfinite(float(total)):
            return
        done, total = max(0, float(done)), max(0, float(total))
        if total != self.total or done < self.done:
            self.reset()
        now = self.clock()
        done = min(done, total) if total else done
        if done > self.done:
            self.samples.append((now, done))
            self.samples = self.samples[-30:]
        self.done, self.total = min(done, total) if total else done, total

    def remaining(self):
        """Recent observed throughput only; suppress short, stale or unstable rates."""
        if not self.total or len(self.samples) < 3:
            return None
        t0, d0 = self.samples[0]
        t1, d1 = self.samples[-1]
        intervals = [b[0] - a[0] for a, b in zip(self.samples, self.samples[1:])]
        if t1 - t0 < 5 or d1 <= d0 or any(dt <= 0 for dt in intervals):
            return None
        rates = [(b[1] - a[1]) / (b[0] - a[0])
                 for a, b in zip(self.samples, self.samples[1:])]
        if max(rates) > min(rates) * 3:
            return None
        if self.clock() - t1 > max(10, 3 * median(intervals)):
            return None
        return (t1 - t0) / (d1 - d0) * max(0, self.total - d1)

    def text(self, show_counts=True):
        now = self.clock()
        elapsed = fmt_eta(now - self.start)
        if not self.total:
            return f"Elapsed {elapsed} - working; remaining time unavailable"
        fraction = min(1., self.done / self.total)
        eta = self.remaining()
        left = f"about {fmt_eta(eta)} left" if eta is not None else "estimating remaining time"
        counts = f" ({self.done:g}/{self.total:g})" if show_counts else ""
        return f"{fraction:.1%}{counts} - elapsed {elapsed} - {left}"
