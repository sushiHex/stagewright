"""Antialiased triangle downsampling in Warp, with RGB host arrays at the boundary."""
from numbers import Integral
from math import isqrt

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


def downsample_rgb(pixels, factor=2):
    """Return an owned contiguous RGB image using a scaled triangle prefilter.

    Accepts uint8 HxWx3 or HxWx4 input. Alpha is discarded. The input dimensions must
    be positive multiples of the positive integer factor. Factor one copies RGB bytes.
    For larger factors, a separable tent is centered on each destination pixel's source
    footprint. Source edges are clamped, and exact integer weighted means round half up.
    Factors that could overflow the integer accumulator are rejected.
    """
    if isinstance(factor, (bool, np.bool_)) or not isinstance(factor, Integral):
        raise ValueError("Downsample factor must be a positive integer")
    factor = int(factor)
    if factor <= 0:
        raise ValueError("Downsample factor must be a positive integer")
    if factor > _MAX_FACTOR:
        raise ValueError("Downsample factor exceeds exact integer accumulator capacity")
    source = np.asarray(pixels)
    if source.dtype != np.uint8:
        raise TypeError("Downsample input must have uint8 pixels")
    if source.ndim != 3 or source.shape[2] not in (3, 4):
        raise ValueError("Downsample input must have shape HxWx3 or HxWx4")
    height, width = source.shape[:2]
    if height == 0 or width == 0 or height % factor or width % factor:
        raise ValueError("Image dimensions must be positive multiples of the downsample factor")
    if factor == 1:
        return np.array(source[..., :3], copy=True, order="C")
    device_input = wp.array(np.ascontiguousarray(source), dtype=wp.uint8, device="cuda:0")
    output = wp.empty((height // factor, width // factor, 3), dtype=wp.uint8, device="cuda:0")
    wp.launch(_tent_mean, output.shape, inputs=[device_input, output, factor], device="cuda:0")
    return np.ascontiguousarray(output.numpy())
