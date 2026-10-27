"""Warp kernels for mesh points, topology, corner normals and UVs."""
import math

import numpy as np
import warp as wp

wp.set_module_options({"fuse_fp": False, "enable_backward": False})
PI = wp.constant(wp.float64(math.pi))
DEVICE = "cuda:0"


def vectors(points, width=3):
    dtype = wp.vec3d if width == 3 else wp.vec2d
    return wp.array(np.asarray(points, dtype=np.float64), dtype=dtype, device=DEVICE)


@wp.kernel
def _face_normals(p: wp.array(dtype=wp.vec3d), offsets: wp.array(dtype=int),
                  ids: wp.array(dtype=int), origin: wp.vec3d, output: wp.array(dtype=wp.vec3d)):
    f = wp.tid()
    start, end = offsets[f], offsets[f + 1]
    normal = wp.vec3d()
    for j in range(start, end):
        k = j + 1
        if k == end:
            k = start
        a = p[ids[j]] - origin
        b = p[ids[k]] - origin
        normal += wp.vec3d((a[1] - b[1]) * (a[2] + b[2]),
                           (a[2] - b[2]) * (a[0] + b[0]),
                           (a[0] - b[0]) * (a[1] + b[1]))
    output[f] = normal


@wp.kernel
def _corner_normals(fn: wp.array(dtype=wp.vec3d), ids: wp.array(dtype=int),
                    corner_faces: wp.array(dtype=int), offsets: wp.array(dtype=int),
                    incident: wp.array(dtype=int), cosine: wp.float64,
                    output: wp.array(dtype=wp.vec3d)):
    c = wp.tid()
    v, f = ids[c], corner_faces[c]
    unit = wp.normalize(fn[f])
    acc = wp.vec3d()
    for j in range(offsets[v], offsets[v + 1]):
        other = fn[incident[j]]
        if wp.dot(wp.normalize(other), unit) >= cosine:
            acc += other
    if wp.length(acc) > wp.float64(0.0):
        output[c] = wp.normalize(acc)
    else:
        output[c] = unit


@wp.kernel
def _uv(p: wp.array(dtype=wp.vec3d), ids: wp.array(dtype=int), cf: wp.array(dtype=int),
        fn: wp.array(dtype=wp.vec3d), tile: wp.vec2d, origin: wp.vec3d,
        output: wp.array(dtype=wp.vec2d)):
    c = wp.tid()
    normal = fn[cf[c]]
    axis = int(0)
    if wp.abs(normal[1]) > wp.abs(normal[axis]):
        axis = 1
    if wp.abs(normal[2]) > wp.abs(normal[axis]):
        axis = 2
    a, b = int(1), int(2)
    if axis == 1:
        a = 0
    elif axis == 2:
        a, b = 0, 1
    point = p[ids[c]] - origin
    output[c] = wp.vec2d(point[a] / tile[0], point[b] / tile[1])


def corners(points, faces, crease_deg=None, tile=None, origin=(0., 0., 0.)):
    ids, cf, offsets = [], [], [0]
    incident = [[] for _ in points]
    for f, face in enumerate(faces):
        ids.extend(face)
        cf.extend([f] * len(face))
        offsets.append(len(ids))
        for v in face:
            incident[v].append(f)
    p = vectors(points)
    index = wp.array(ids, dtype=int, device=DEVICE)
    corner_faces = wp.array(cf, dtype=int, device=DEVICE)
    fo = wp.array(offsets, dtype=int, device=DEVICE)
    fn = wp.empty(len(faces), dtype=wp.vec3d, device=DEVICE)
    wp.launch(_face_normals, len(faces), inputs=[p, fo, index, wp.vec3d(), fn], device=DEVICE)
    normals, uv = None, None
    if crease_deg is not None:
        io, ii = [0], []
        for face_ids in incident:
            ii.extend(face_ids)
            io.append(len(ii))
        ino = wp.array(io, dtype=int, device=DEVICE)
        ini = wp.array(ii, dtype=int, device=DEVICE)
        result = wp.empty(len(ids), dtype=wp.vec3d, device=DEVICE)
        wp.launch(_corner_normals, len(ids), inputs=[fn, index, corner_faces, ino, ini,
                  math.cos(math.radians(crease_deg)), result], device=DEVICE)
        normals = result.numpy()
    if tile is not None:
        # Match the original projection's origin-relative Newell calculation, including
        # dominant-axis ties on chamfers whose components are equal within rounding.
        if any(origin):
            fn = wp.empty_like(fn)
            wp.launch(_face_normals, len(faces), inputs=[p, fo, index, wp.vec3d(*origin), fn], device=DEVICE)
        pair = (tile, tile) if np.isscalar(tile) else tile
        result = wp.empty(len(ids), dtype=wp.vec2d, device=DEVICE)
        wp.launch(_uv, len(ids), inputs=[p, index, corner_faces, fn, wp.vec2d(*pair),
                                        wp.vec3d(*origin), result], device=DEVICE)
        uv = result.numpy()
    return normals, uv


@wp.kernel
def _profile(half_w: wp.float64, low: wp.float64, high: wp.float64, radius: wp.float64,
             arc: int, closed: int, out: wp.array(dtype=wp.vec2d)):
    j = wp.tid()
    r = radius
    if closed == 0:
        if j == 0:
            out[j] = wp.vec2d(-half_w, low)
        elif j == 2 * (arc + 1) + 1:
            out[j] = wp.vec2d(half_w, low)
        else:
            side = (j - 1) / (arc + 1)
            i = (j - 1) % (arc + 1)
            angle = PI - (PI / wp.float64(2.0)) * wp.float64(i) / wp.float64(arc)
            cx = -half_w + r
            if side == 1:
                angle = (PI / wp.float64(2.0)) - (PI / wp.float64(2.0)) * wp.float64(i) / wp.float64(arc)
                cx = half_w - r
            out[j] = wp.vec2d(cx + r * wp.cos(angle), high - r + r * wp.sin(angle))
    else:
        corner, i = j / (arc + 1), j % (arc + 1)
        cx, cz = half_w - r, high - r
        if corner == 1 or corner == 2:
            cx = -half_w + r
        if corner >= 2:
            cz = low + r
        angle = (PI / wp.float64(2.0)) * (wp.float64(corner) + wp.float64(i) / wp.float64(arc))
        out[j] = wp.vec2d(cx + r * wp.cos(angle), cz + r * wp.sin(angle))


def profile(half_w, low, high, radius, arc, closed):
    radius = min(radius, half_w, (high - low) / (2 if closed else 1))
    count = 4 * (arc + 1) if closed else 2 * (arc + 1) + 2
    out = wp.empty(count, dtype=wp.vec2d, device=DEVICE)
    wp.launch(_profile, count, inputs=[half_w, low, high, radius, arc, int(closed), out], device=DEVICE)
    return out.numpy()


@wp.kernel
def _loft(k: int, segs: int, flip: int, out: wp.array(dtype=int, ndim=2)):
    i, j = wp.tid()
    j2 = (j + 1) % k
    f = i * segs + j
    a, b, c, d = i * k + j, i * k + j2, (i + 1) * k + j2, (i + 1) * k + j
    if flip == 0:
        out[f, 0] = a
        out[f, 1] = b
        out[f, 2] = c
        out[f, 3] = d
    else:
        out[f, 0] = d
        out[f, 1] = c
        out[f, 2] = b
        out[f, 3] = a


def loft_faces(rings, k, closed, flip):
    segs = k if closed else k - 1
    out = wp.empty(((rings - 1) * segs, 4), dtype=int, device=DEVICE)
    wp.launch(_loft, (rings - 1, segs), inputs=[k, segs, int(flip), out], device=DEVICE)
    return out.numpy().tolist()


@wp.kernel
def _rings(center: wp.vec3d, u: wp.vec3d, v: wp.vec3d, axis: wp.vec3d,
           radii: wp.array(dtype=wp.float64), heights: wp.array(dtype=wp.float64),
           n: int, spin: wp.float64, out: wp.array(dtype=wp.vec3d)):
    ring, j = wp.tid()
    a = spin + (wp.float64(2.0) * PI) * wp.float64(j) / wp.float64(n)
    out[ring * n + j] = center + heights[ring] * axis + radii[ring] * (wp.cos(a) * u + wp.sin(a) * v)


def rings(center, axis, radii, heights, n, spin=0., xy=False):
    w = wp.vec3d(*axis)
    w = wp.normalize(w)
    if xy:
        u, v = wp.vec3d(1., 0., 0.), wp.vec3d(0., 1., 0.)
    else:
        a = wp.vec3d(1., 0., 0.) if abs(w[0]) < 0.9 else wp.vec3d(0., 1., 0.)
        u = wp.normalize(wp.cross(w, a))
        v = wp.cross(w, u)
    rs = wp.array(radii, dtype=wp.float64, device=DEVICE)
    hs = wp.array(heights, dtype=wp.float64, device=DEVICE)
    out = wp.empty(len(radii) * n, dtype=wp.vec3d, device=DEVICE)
    wp.launch(_rings, (len(radii), n), inputs=[wp.vec3d(*center), u, v, w, rs, hs, n, spin, out], device=DEVICE)
    return out.numpy().reshape(len(radii), n, 3)


@wp.kernel
def _sweep(path: wp.array(dtype=wp.vec3d), section: wp.array(dtype=wp.vec2d), b: wp.vec3d,
           closed: int, count: int, width: int, out: wp.array(dtype=wp.vec3d)):
    i, j = wp.tid()
    before, after = i - 1, i + 1
    if closed == 1:
        before, after = (i + count - 1) % count, (i + 1) % count
    else:
        before, after = wp.max(before, 0), wp.min(after, count - 1)
    t = wp.normalize(path[after] - path[before])
    normal = wp.normalize(wp.cross(t, b))
    out[i * width + j] = path[i] + section[j][0] * normal + section[j][1] * b


def sweep_rings(path, section, binormal, closed):
    p, sec = vectors(path), vectors(section, 2)
    b = wp.normalize(wp.vec3d(*binormal))
    out = wp.empty(len(path) * len(section), dtype=wp.vec3d, device=DEVICE)
    wp.launch(_sweep, (len(path), len(section)), inputs=[p, sec, b, int(closed), len(path), len(section), out], device=DEVICE)
    return out.numpy().reshape(len(path), len(section), 3)


@wp.kernel
def _resample(path: wp.array(dtype=wp.vec3d), count: int, spacing: wp.float64, margin: wp.float64,
              targets: int, out: wp.array(dtype=wp.vec3d), tangent: wp.array(dtype=wp.vec3d)):
    j = wp.tid()
    total = wp.float64(0.0)
    for i in range(count - 1):
        total += wp.length(path[i + 1] - path[i])
    at = margin + (wp.float64(j) + wp.float64(0.5)) * ((total - wp.float64(2.0) * margin) / wp.float64(targets))
    previous = wp.float64(0.0)
    index = int(count - 2)
    for i in range(count - 1):
        length = wp.length(path[i + 1] - path[i])
        if previous + length > at or i == count - 2:
            index = i
            break
        previous += length
    delta = path[index + 1] - path[index]
    length = wp.max(wp.length(delta), wp.float64(1e-9))
    out[j] = path[index] + ((at - previous) / length) * delta
    tangent[j] = delta / length


@wp.kernel
def _path_length(path: wp.array(dtype=wp.vec3d), count: int, out: wp.array(dtype=wp.float64)):
    total = wp.float64(0.0)
    for i in range(count - 1):
        total += wp.length(path[i + 1] - path[i])
    out[0] = total


def resample(path, spacing, margin):
    p = vectors(path)
    length = wp.empty(1, dtype=wp.float64, device=DEVICE)
    wp.launch(_path_length, 1, inputs=[p, len(path), length], device=DEVICE)
    count = max(1, int((float(length.numpy()[0]) - 2 * margin) // spacing) + 1)
    out = wp.empty(count, dtype=wp.vec3d, device=DEVICE)
    tangent = wp.empty_like(out)
    wp.launch(_resample, count, inputs=[p, len(path), spacing, margin, count, out, tangent], device=DEVICE)
    return out.numpy(), tangent.numpy()
