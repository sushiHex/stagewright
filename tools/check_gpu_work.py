"""CPU-only checks for desktop pacing, cancellation and unchanged render inputs."""
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gpu_work
import rtx


class Clock:
    now = 0.

    def sleep(self, seconds):
        self.now += seconds


def main():
    with TemporaryDirectory() as directory:
        stop = Path(directory) / 'STOP_GPU'
        clock = Clock()
        with patch.object(gpu_work, 'STOP_FILE', stop), \
             patch.object(gpu_work, '_background_priority') as priority, \
             patch.object(gpu_work.time, 'monotonic', lambda: clock.now), \
             patch.object(gpu_work.time, 'sleep', clock.sleep):
            gpu = gpu_work.GpuPacer(.25)
            with gpu.batch():
                clock.now += .02
            assert abs(clock.now-.08) < 1e-9
            assert gpu.ready_at(clock.now-.01) >= clock.now+.03-1e-9
            for invalid in [0, -1, 2, float('nan'), float('inf')]:
                try:
                    gpu_work.GpuPacer(invalid)
                except ValueError:
                    pass
                else:
                    raise AssertionError('Invalid duty accepted')

            calls = []
            def step(**arguments):
                calls.append(arguments)
                clock.now += .02
                frame = SimpleNamespace(progression=len(calls), converged=len(calls)==2)
                return {'image': SimpleNamespace(frames=[frame])}
            images, status = rtx.converge(SimpleNamespace(step=step), ['image'], 7, .125, 4,
                read_pixels=lambda frame, var: (frame.progression, var))
            assert images == {'image': (2, 'image/Color')}
            assert status == {'image': (2, True)}
            assert calls == [dict(render_products={'image'}, ordinal=7, delta_time=.125)] * 2

            def stop_during_wait(seconds):
                clock.sleep(seconds)
                stop.touch()
            with patch.object(gpu_work.time, 'sleep', stop_during_wait):
                try:
                    with gpu.batch():
                        clock.now += .1
                except KeyboardInterrupt:
                    pass
                else:
                    raise AssertionError('Stop during idle was ignored')
            priority.reset_mock()
            try:
                gpu_work.GpuPacer()
            except KeyboardInterrupt:
                pass
            else:
                raise AssertionError('Startup stop was ignored')
            priority.assert_not_called()
    print('Pacing, stop handling and render-input checks pass without GPU access.')


if __name__ == '__main__':
    main()
