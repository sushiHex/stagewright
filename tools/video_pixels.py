"""Limited-range BT.601 NV12 conversion for the untagged H.264 output."""
import numpy as np
import warp as wp


@wp.func
def _byte(x: float):
    return wp.uint8(wp.clamp(wp.floor(x + 0.5), 0.0, 255.0))


@wp.kernel
def _nv12(rgb: wp.array(dtype=wp.uint8, ndim=3), out: wp.array(dtype=wp.uint8), w: int, h: int):
    y, x = wp.tid()
    r = float(rgb[y, x, 0])
    g = float(rgb[y, x, 1])
    b = float(rgb[y, x, 2])
    out[y * w + x] = _byte(16.0 + (65.481 * r + 128.553 * g + 24.966 * b) / 255.0)
    if y % 2 == 0 and x % 2 == 0:
        r = float(0.0)
        g = float(0.0)
        b = float(0.0)
        for j in range(2):
            for i in range(2):
                r += float(rgb[y + j, x + i, 0]) * 0.25
                g += float(rgb[y + j, x + i, 1]) * 0.25
                b += float(rgb[y + j, x + i, 2]) * 0.25
        at = h * w + (y / 2) * w + x
        out[at] = _byte(128.0 + (-37.797 * r - 74.203 * g + 112.0 * b) / 255.0)
        out[at + 1] = _byte(128.0 + (112.0 * r - 93.786 * g - 18.214 * b) / 255.0)


def to_nv12(rgb):
    h, w = rgb.shape[:2]
    if hasattr(rgb, "__dlpack_device__") and rgb.__dlpack_device__()[0] == 2:
        source = wp.from_dlpack(rgb)
    else:
        source = wp.array(np.ascontiguousarray(rgb), dtype=wp.uint8, device="cuda:0")
    output = wp.empty(h * w * 3 // 2, dtype=wp.uint8, device="cuda:0")
    wp.launch(_nv12, (h, w), inputs=[source, output, w, h], device="cuda:0")
    return output.numpy()
