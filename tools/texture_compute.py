"""Periodic spectral noise and material maps computed in Warp on CUDA."""
import math

import warp as wp

from image_io import write_rgb

DEVICE = "cuda:0"


@wp.kernel
def _white(out: wp.array(dtype=wp.vec2d, ndim=2), seed: int, n: int):
    y, x = wp.tid()
    state = wp.rand_init(seed, y * n + x)
    out[y, x] = wp.vec2d(wp.float64(wp.randn(state)), wp.float64(0.0))


@wp.kernel
def _reverse(src: wp.array(dtype=wp.vec2d, ndim=2), dst: wp.array(dtype=wp.vec2d, ndim=2),
             bits: int, axis: int):
    y, x = wp.tid()
    index = x
    if axis == 0:
        index = y
    reverse = int(0)
    for i in range(bits):
        reverse = (reverse << 1) | ((index >> i) & 1)
    if axis == 0:
        dst[y, x] = src[reverse, x]
    else:
        dst[y, x] = src[y, reverse]


@wp.kernel
def _butterfly(data: wp.array(dtype=wp.vec2d, ndim=2), half: int, axis: int, direction: wp.float64):
    row, pair = wp.tid()
    j = pair % half
    a = (pair / half) * (2 * half) + j
    b = a + half
    angle = direction * wp.float64(math.pi) * wp.float64(j) / wp.float64(half)
    c, s = wp.cos(angle), wp.sin(angle)
    u = wp.vec2d()
    v = wp.vec2d()
    if axis == 1:
        u = wp.vec2d(data[row, a])
        v = wp.vec2d(data[row, b])
    else:
        u = wp.vec2d(data[a, row])
        v = wp.vec2d(data[b, row])
    t = wp.vec2d(c * v[0] - s * v[1], s * v[0] + c * v[1])
    if axis == 1:
        data[row, a] = u + t
        data[row, b] = u - t
    else:
        data[a, row] = u + t
        data[b, row] = u - t


@wp.kernel
def _spectrum(data: wp.array(dtype=wp.vec2d, ndim=2), n: int, beta: wp.float64):
    y, x = wp.tid()
    fx, fy = wp.min(x, n - x), wp.min(y, n - y)
    if fx == 0 and fy == 0:
        data[y, x] = wp.vec2d()
    else:
        f = wp.sqrt(wp.float64(fx * fx + fy * fy)) / wp.float64(n)
        data[y, x] = data[y, x] * wp.pow(f, -beta / wp.float64(2.0))


@wp.kernel
def _moments(data: wp.array(dtype=wp.vec2d, ndim=2), stats: wp.array(dtype=wp.float64), n: int):
    # One thread per row, followed by a fixed-order reduction, keeps builds deterministic.
    y = wp.tid()
    s, ss = wp.float64(0.0), wp.float64(0.0)
    for x in range(n):
        v = data[y, x][0] / wp.float64(n * n)
        s += v
        ss += v * v
    stats[y * 2] = s
    stats[y * 2 + 1] = ss


@wp.kernel
def _normalize(data: wp.array(dtype=wp.vec2d, ndim=2), stats: wp.array(dtype=wp.float64),
               output: wp.array(dtype=wp.float64, ndim=2), n: int):
    y = wp.tid()
    s, ss = wp.float64(0.0), wp.float64(0.0)
    for row in range(n):
        s += stats[row * 2]
        ss += stats[row * 2 + 1]
    mean = s / wp.float64(n * n)
    sd = wp.sqrt(ss / wp.float64(n * n) - mean * mean)
    for x in range(n):
        output[y, x] = (data[y, x][0] / wp.float64(n * n) - mean) / sd


def noise(n, beta, seed):
    if n < 2 or n & (n - 1):
        raise ValueError("Spectral noise size must be a power of two")
    a = wp.empty((n, n), dtype=wp.vec2d, device=DEVICE)
    b = wp.empty_like(a)
    wp.launch(_white, (n, n), inputs=[a, seed, n], device=DEVICE)
    for direction in (-1.0, 1.0):
        for axis in (1, 0):
            wp.launch(_reverse, (n, n), inputs=[a, b, n.bit_length() - 1, axis], device=DEVICE)
            a, b = b, a
            half = 1
            while half < n:
                wp.launch(_butterfly, (n, n // 2), inputs=[a, half, axis, direction], device=DEVICE)
                half *= 2
        if direction < 0:
            wp.launch(_spectrum, (n, n), inputs=[a, n, beta], device=DEVICE)
    stats = wp.empty(n * 2, dtype=wp.float64, device=DEVICE)
    out = wp.empty((n, n), dtype=wp.float64, device=DEVICE)
    wp.launch(_moments, n, inputs=[a, stats, n], device=DEVICE)
    wp.launch(_normalize, n, inputs=[a, stats, out, n], device=DEVICE)
    return out


@wp.func
def _clip(v: wp.float64):
    return wp.clamp(v, wp.float64(0.0), wp.float64(1.0))


@wp.func
def _mod(v: wp.float64, period: wp.float64):
    return v - wp.floor(v / period) * period


@wp.kernel
def _material(kind: int, n: int, params: wp.array(dtype=wp.float64),
              low: wp.array(dtype=wp.float64, ndim=2), mid: wp.array(dtype=wp.float64, ndim=2),
              fine: wp.array(dtype=wp.float64, ndim=2), rnoise: wp.array(dtype=wp.float64, ndim=2),
              color: wp.array(dtype=wp.float64, ndim=2), height: wp.array(dtype=wp.float64, ndim=2),
              orm: wp.array(dtype=wp.vec3d, ndim=2)):
    y, x = wp.tid()
    tile, tz = params[0], params[1]
    u = (wp.float64(x) + wp.float64(0.5)) * tile / wp.float64(n)
    v = (wp.float64(n - y) - wp.float64(0.5)) * tz / wp.float64(n)
    col, h, occ, rough, metal = wp.float64(0.0), wp.float64(0.0), wp.float64(1.0), wp.float64(0.5), wp.float64(0.0)
    if kind == 0:  # acoustic perforations
        pitch, radius, depth, edge = params[2], params[3], params[4], params[5]
        row = wp.floor(v / pitch)
        du = _mod(u + _mod(row, wp.float64(2.0)) * pitch / wp.float64(2.0), pitch) - pitch / wp.float64(2.0)
        dv = _mod(v, pitch) - pitch / wp.float64(2.0)
        hole = _clip((radius - wp.sqrt(du * du + dv * dv)) / edge + wp.float64(0.5))
        nz = low[y, x]
        col = wp.float64(0.075) * (wp.float64(1.0) + wp.float64(0.05) * nz) * (wp.float64(1.0) - hole) + wp.float64(0.006) * hole
        rough = (wp.float64(0.48) + wp.float64(0.03) * nz) * (wp.float64(1.0) - hole) + wp.float64(0.95) * hole
        h, occ = -depth * hole, wp.float64(1.0) - wp.float64(0.8) * hole
    elif kind == 1:  # honeycomb
        side, wall = params[2], params[3]
        r3 = wp.sqrt(wp.float64(3.0))
        ax = _mod(u + wp.float64(1.5) * side, wp.float64(3.0) * side) - wp.float64(1.5) * side
        az = _mod(v + r3 * side / wp.float64(2.0), r3 * side) - r3 * side / wp.float64(2.0)
        bx = _mod(u, wp.float64(3.0) * side) - wp.float64(1.5) * side
        bz = _mod(v, r3 * side) - r3 * side / wp.float64(2.0)
        px, pz = ax, az
        if bx * bx + bz * bz < ax * ax + az * az:
            px, pz = bx, bz
        d = wp.max(wp.abs(pz), wp.max(wp.abs(px * r3 / wp.float64(2.0) + pz / wp.float64(2.0)), wp.abs(px * r3 / wp.float64(2.0) - pz / wp.float64(2.0))))
        ap = r3 * side / wp.float64(2.0)
        w = _clip((d - (ap - wall / wp.float64(2.0))) / wp.float64(0.08) + wp.float64(0.5))
        t = _clip(d / ap)
        col = wp.float64(0.60) * w + (wp.float64(0.010) + wp.float64(0.10) * wp.pow(t, wp.float64(5.0))) * (wp.float64(1.0) - w)
        h = -wp.float64(0.6) * (wp.float64(1.0) - w) * (wp.float64(1.0) - wp.pow(t, wp.float64(3.0)))
        occ = wp.float64(0.25) + wp.float64(0.75) * (w + (wp.float64(1.0) - w) * wp.pow(t, wp.float64(4.0)))
        rough, metal = wp.float64(0.35) * w + wp.float64(0.85) * (wp.float64(1.0) - w), w
    elif kind == 2:  # floor
        base, mottle, grain, rgh, variation, seam_w = params[2], params[3], params[4], params[5], params[6], params[7]
        col = base * (wp.float64(1.0) + mottle * (wp.float64(0.75) * low[y, x] + wp.float64(0.25) * mid[y, x]) + grain * fine[y, x])
        rough = rgh + variation * (wp.float64(0.7) * low[y, x] + wp.float64(0.3) * rnoise[y, x])
        h = wp.float64(0.004) * fine[y, x]
        if seam_w > wp.float64(0.0):
            e = wp.min(wp.min(u, tile - u), wp.min(v, tile - v))
            seam = _clip((seam_w / wp.float64(2.0) - e) / (tile / wp.float64(n)) + wp.float64(0.5))
            col = col * (wp.float64(1.0) - seam) + wp.float64(0.25) * base * seam
            rough = rough * (wp.float64(1.0) - seam) + wp.float64(0.85) * seam
            h -= wp.float64(0.35) * seam
        rough = wp.clamp(rough, wp.float64(0.05), wp.float64(1.0))
    else:  # belt
        h = wp.float64(0.04) * wp.cos(wp.float64(2.0 * math.pi) * u * params[2] / tile)
        col = wp.float64(0.035) * (wp.float64(1.0) + wp.float64(0.08) * low[y, x])
        rough = wp.float64(0.68) + wp.float64(0.04) * low[y, x]
    color[y, x] = col
    height[y, x] = h
    orm[y, x] = wp.vec3d(occ, rough, metal)


@wp.func
def _byte(v: wp.float64):
    return wp.uint8(_clip(v) * wp.float64(255.0) + wp.float64(0.5))


@wp.kernel
def _maps(color: wp.array(dtype=wp.float64, ndim=2), height: wp.array(dtype=wp.float64, ndim=2),
          orm: wp.array(dtype=wp.vec3d, ndim=2), output: wp.array(dtype=wp.uint8, ndim=4),
          n: int, cm: wp.float64):
    y, x = wp.tid()
    c = _clip(color[y, x])
    srgb = wp.float64(12.92) * c
    if c > wp.float64(0.0031308):
        srgb = wp.float64(1.055) * wp.pow(c, wp.float64(1.0 / 2.4)) - wp.float64(0.055)
    du = (height[y, (x + 1) % n] - height[y, (x + n - 1) % n]) / (wp.float64(2.0) * cm)
    dv = -(height[(y + 1) % n, x] - height[(y + n - 1) % n, x]) / (wp.float64(2.0) * cm)
    normal = wp.normalize(wp.vec3d(-du, -dv, wp.float64(1.0))) * wp.float64(0.5) + wp.vec3d(wp.float64(0.5))
    for ch in range(3):
        output[0, y, x, ch] = _byte(srgb)
        output[1, y, x, ch] = _byte(normal[ch])
        output[2, y, x, ch] = _byte(orm[y, x][ch])


def material_maps(directory, name, kind, n, params, spectra=(), seed=0):
    fields = [noise(n, beta, seed + i) for i, beta in enumerate(spectra)]
    zero = wp.zeros((n, n), dtype=wp.float64, device=DEVICE)
    fields += [zero] * (4 - len(fields))
    color, height = wp.empty_like(zero), wp.empty_like(zero)
    orm = wp.empty((n, n), dtype=wp.vec3d, device=DEVICE)
    output = wp.empty((3, n, n, 3), dtype=wp.uint8, device=DEVICE)
    p = wp.array(params, dtype=wp.float64, device=DEVICE)
    wp.launch(_material, (n, n), inputs=[kind, n, p, *fields, color, height, orm], device=DEVICE)
    wp.launch(_maps, (n, n), inputs=[color, height, orm, output, n, params[0] / n], device=DEVICE)
    host = output.numpy()
    for i, suffix in enumerate(("color", "normal", "orm")):
        write_rgb(directory / f"{name}_{suffix}.png", host[i])
