"""Antialiased triangle downsampling in Warp, with RGB host arrays at the boundary."""
from numbers import Integral
from math import isqrt
import traceback

import numpy as np
import warp as wp

# Each one-dimensional weight sum is 2*f^2. Bound the maximum uint8 weighted sum
# plus half its normalization before converting to the kernel's signed int64.
_MAX_FACTOR = isqrt(isqrt((2**63 - 1) // 1022))


@wp.kernel
def _tent_mean(source: wp.array(dtype=wp.uint8, ndim=3),
               output: wp.array(dtype=wp.uint8, ndim=3), factor: int):
    y, x, channel = wp.tid()
    total = wp.int64(0)
    norm = wp.int64(0)
    for row in range(-factor, 2 * factor):
        wy = wp.max(0, 2 * factor - wp.abs(2 * row - (factor - 1)))
        source_y = wp.clamp(y * factor + row, 0, source.shape[0] - 1)
        for column in range(-factor, 2 * factor):
            wx = wp.max(0, 2 * factor - wp.abs(2 * column - (factor - 1)))
            weight = wp.int64(wy) * wp.int64(wx)
            if weight > wp.int64(0):
                source_x = wp.clamp(x * factor + column, 0, source.shape[1] - 1)
                total += wp.int64(source[source_y, source_x, channel]) * weight
                norm += weight
    output[y, x, channel] = wp.uint8((total + norm / wp.int64(2)) / norm)


def _factor(factor):
    if isinstance(factor, (bool, np.bool_)) or not isinstance(factor, Integral):
        raise ValueError("Downsample factor must be a positive integer")
    factor = int(factor)
    if factor <= 0:
        raise ValueError("Downsample factor must be a positive integer")
    if factor > _MAX_FACTOR:
        raise ValueError("Downsample factor exceeds exact integer accumulator capacity")
    return factor


def _shape(shape, factor):
    if len(shape) != 3 or shape[2] not in (3, 4):
        raise ValueError("Downsample input must have shape HxWx3 or HxWx4")
    height, width = shape[:2]
    if height == 0 or width == 0 or height % factor or width % factor:
        raise ValueError("Image dimensions must be positive multiples of the downsample factor")
    return height // factor, width // factor, 3


class RGBDownsampler:
    """Sequence-owned scratch buffers; each call returns an independent RGB host image.

    Instances are used serially. capture() filters a CUDA render-var mapping before
    readback; capture_cpu() retains the explicit host-copy reference path.
    """

    def __init__(self, factor=2, device="cuda:0"):
        self.factor = _factor(factor)
        self.device = device
        self._input = None
        self._output = None

    def _launch(self, source, stream):
        try:
            if source.dtype != wp.uint8:
                raise TypeError("Downsample input must have uint8 pixels")
            shape = _shape(source.shape, self.factor)
            if self._output is None or self._output.shape != shape or self._output.device != source.device:
                self._output = wp.empty(shape, dtype=wp.uint8, device=source.device)
            wp.launch(_tent_mean, shape, inputs=[source, self._output, self.factor],
                      device=source.device, stream=stream)
            return self._output
        finally:
            # Do not retain a mapped view in this helper's exception traceback.
            source = None

    def __call__(self, pixels):
        source = np.asarray(pixels)
        if source.dtype != np.uint8:
            raise TypeError("Downsample input must have uint8 pixels")
        _shape(source.shape, self.factor)
        if self.factor == 1:
            return np.array(source[..., :3], copy=True, order="C")
        stream = wp.get_stream(self.device)
        try:
            if self._input is None or self._input.shape != source.shape:
                self._input = wp.empty(source.shape, dtype=wp.uint8, device=self.device)
            with wp.ScopedStream(stream):
                self._input.assign(np.ascontiguousarray(source))
                output = self._launch(self._input, stream)
            wp.synchronize_stream(stream)
            return np.array(output.numpy(), copy=True, order="C")
        finally:
            wp.synchronize_stream(stream)

    def capture(self, frame, render_var):
        """Wait for the producer, filter its CUDA view, then release all mapped aliases.

        Cleanup synchronizes the consumer even when conversion, launch or readback
        fails. The unmap stream hint also protects release if synchronization raises.
        """
        import ovrtx

        handle = frame.render_vars[render_var].map(device=ovrtx.Device.CUDA)
        shared = None
        stream = None
        try:
            handle.wait()
            shared = wp.from_dlpack(handle)
            if shared.device != wp.get_device(self.device):
                raise ValueError("Render pixels must be on the downsampler CUDA device")
            stream = wp.get_stream(shared.device)
            output = self._launch(shared, stream)
            wp.synchronize_stream(stream)
            return np.array(output.numpy(), copy=True, order="C")
        except BaseException as error:
            # Keep diagnostic locations without retaining mapped views in lower
            # launch/conversion/readback frames after the mapping is released.
            traceback.clear_frames(error.__traceback__)
            raise
        finally:
            try:
                if stream is not None:
                    wp.synchronize_stream(stream)
            finally:
                shared = None
                if stream is None:
                    handle.unmap()
                else:
                    handle.unmap(stream=stream.cuda_stream)

    def capture_cpu(self, frame, render_var):
        """Reference capture through the existing owned host-copy boundary."""
        from rtx import pixels
        return self(pixels(frame, render_var))


def downsample_rgb(pixels, factor=2):
    """Return an owned contiguous RGB image using an exact integer triangle prefilter.

    Accepts uint8 HxWx3 or HxWx4 input with positive dimensions divisible by factor.
    Edges clamp, means round half up, alpha is discarded and factor one copies RGB.
    Use RGBDownsampler for a sequence to reuse scratch allocations.
    """
    return RGBDownsampler(factor)(pixels)
