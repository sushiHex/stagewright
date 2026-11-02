"""Leave desktop headroom between completed GPU batches."""
import contextlib
import math
import os
from pathlib import Path
import time

STOP_FILE = Path(__file__).resolve().parents[1] / "build/STOP_GPU"
_background_set = False


def _background_priority():
    global _background_set
    if os.name != "nt" or _background_set:
        return
    import ctypes
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.SetPriorityClass.restype = wintypes.BOOL
    # Lower CPU priority without lowering memory or I/O priority.
    if not kernel.SetPriorityClass(kernel.GetCurrentProcess(), 0x00004000):
        raise ctypes.WinError(ctypes.get_last_error())
    scheduler = ctypes.WinDLL("gdi32").D3DKMTSetProcessSchedulingPriorityClass
    scheduler.argtypes = [wintypes.HANDLE, ctypes.c_int]
    scheduler.restype = ctypes.c_long
    # IDLE is enum value 0. This changes only the current process.
    # https://learn.microsoft.com/windows-hardware/drivers/ddi/d3dkmthk/nf-d3dkmthk-d3dkmtsetprocessschedulingpriorityclass
    status = scheduler(kernel.GetCurrentProcess(), 0)
    if status != 0:
        raise RuntimeError(f"Cannot lower GPU process priority: 0x{status & 0xffffffff:08x}")
    _background_set = True


class GpuPacer:
    """Pace completed work, not submission to an asynchronous queue.

    Duty is a wall-time budget, not a hardware utilization ceiling. A running
    native batch must finish before it can yield or honor a stop request.
    """
    def __init__(self, duty=None):
        self.duty = float(os.environ.get("STAGEWRIGHT_GPU_DUTY", ".25") if duty is None else duty)
        if not math.isfinite(self.duty) or not 0 < self.duty <= 1:
            raise ValueError("STAGEWRIGHT_GPU_DUTY must be greater than zero and at most one")
        self.check()
        _background_priority()

    def check(self):
        if STOP_FILE.exists():
            raise KeyboardInterrupt(f"GPU work stopped by {STOP_FILE}")

    def ready_at(self, started):
        completed = time.monotonic()
        rest = max(.02, (completed-started) * (1/self.duty-1)) if self.duty < 1 else 0
        return completed + rest

    def wait_until(self, deadline):
        self.check()
        while (remaining := deadline-time.monotonic()) > 0:
            time.sleep(min(.05, remaining))
            self.check()

    @contextlib.contextmanager
    def batch(self):
        self.check()
        started = time.monotonic()
        yield
        self.wait_until(self.ready_at(started))
