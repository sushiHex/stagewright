# Small Warp mesh kit shared by the build scripts. Pure geometry: no pxr import here.
#
# Every builder returns (points, faces): points is an (N, 3) float array, faces is a list of
# vertex-index lists wound counter-clockwise seen from outside (USD rightHanded orientation).
# MeshBuilder merges parts and computes creased face-varying normals, so flat faces stay flat
# and curved strips stay smooth without hand-authored smoothing groups.
import math

import numpy as np

import mesh_compute as compute


def newell(p):
    """Unnormalised polygon normal (length = 2 x area) of an ordered (k, 3) point array."""
    q = np.roll(p, -1, axis=0)
    return np.array([
        np.sum((p[:, 1] - q[:, 1]) * (p[:, 2] + q[:, 2])),
        np.sum((p[:, 2] - q[:, 2]) * (p[:, 0] + q[:, 0])),
        np.sum((p[:, 0] - q[:, 0]) * (p[:, 1] + q[:, 1])),
    ])


def order_convex_face(points, ids, outward):
    """Order the vertex ids of a planar convex face CCW about the outward direction."""
    P = points[ids]
    c = P.mean(axis=0)
    n = np.asarray(outward, float)
    n = n / np.linalg.norm(n)
    a = np.array([1.0, 0, 0]) if abs(n[0]) < 0.9 else np.array([0, 1.0, 0])
    u = np.cross(n, a)
    u /= np.linalg.norm(u)
    v = np.cross(n, u)
    d = P - c
    ang = np.arctan2(d @ v, d @ u)
    out = [ids[i] for i in np.argsort(ang)]
    if newell(points[out]) @ n < 0:
        out.reverse()
    return out


def creased_normals(points, faces, crease_deg):
    """Face-varying normals: each corner averages the area-weighted normals of the faces
    around its vertex whose normals lie within crease_deg of this face's normal."""
    return compute.corners(points, faces, crease_deg=crease_deg)[0]


def box_uv(points, faces, tile, origin=(0.0, 0.0, 0.0)):
    """Face-varying texture coordinates by box projection: each face is projected along its
    dominant normal axis, in world units divided by tile (cm per texture repeat; a scalar or a
    (u, v) pair). Texel density is therefore constant across parts and meshes."""
    return compute.corners(points, faces, tile=tile, origin=origin)[1]


class MeshBuilder:
    """Accumulates parts into one mesh with creased face-varying normals and, when any part is
    given a texture tile, face-varying box-projected UVs (parts without one get zeros)."""

    def __init__(self):
        self.points, self.counts, self.indices, self.normals, self.uvs = [], [], [], [], []
        self._n = 0
        self._has_uv = False

    def add(self, points, faces, crease_deg=35.0, tile=None, uv=None):
        points = np.asarray(points, float)
        normals, generated_uv = compute.corners(points, faces, crease_deg, tile if uv is None else None)
        self.normals.append(normals)
        if uv is None:
            uv = generated_uv
        corners = sum(len(f) for f in faces)
        self.uvs.append(np.zeros((corners, 2)) if uv is None else np.asarray(uv, float))
        self._has_uv |= uv is not None
        for f in faces:
            self.counts.append(len(f))
            self.indices.extend(int(i) + self._n for i in f)
        self.points.append(points)
        self._n += len(points)
        return self

    def st(self):
        """Face-varying UVs as (values, indices), or None when no part asked for them."""
        if not self._has_uv:
            return None
        uv = np.round(np.vstack(self.uvs), 6).astype(np.float32)
        values, idx = np.unique(uv, axis=0, return_inverse=True)
        return values, idx.reshape(-1).astype(np.int32)

    def arrays(self):
        """counts, indices, points, normal values, normal indices (face-varying, indexed)."""
        nrm = np.round(np.vstack(self.normals), 5).astype(np.float32)
        values, nidx = np.unique(nrm, axis=0, return_inverse=True)
        return (np.array(self.counts, dtype=np.int32), np.array(self.indices, dtype=np.int32),
                np.vstack(self.points).astype(np.float32), values, nidx.reshape(-1).astype(np.int32))

    def extent(self):
        P = np.vstack(self.points)
        return P.min(axis=0), P.max(axis=0)


def chamfered_box(lo, hi, c):
    """Axis-aligned box from lo to hi with every edge chamfered by c (26 faces, 24 points)."""
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    m, h = (lo + hi) / 2, (hi - lo) / 2
    c = min(c, 0.45 * float(h.min()))
    signs = [(sx, sy, sz) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
    pts, key = [], {}
    for s in signs:
        for k in range(3):
            p = [m[j] + s[j] * (h[j] - (0 if j == k else c)) for j in range(3)]
            key[(s, k)] = len(pts)
            pts.append(p)
    pts = np.array(pts)
    groups = []
    for k in range(3):  # main faces
        for sg in (-1, 1):
            groups.append([key[(s, k)] for s in signs if s[k] == sg])
    for k in range(3):  # edge chamfers
        for j in range(k + 1, 3):
            for sk in (-1, 1):
                for sj in (-1, 1):
                    groups.append([key[(s, a)] for s in signs if s[k] == sk and s[j] == sj for a in (k, j)])
    for s in signs:  # corner triangles
        groups.append([key[(s, 0)], key[(s, 1)], key[(s, 2)]])
    faces = [order_convex_face(pts, g, pts[g].mean(axis=0) - m) for g in groups]
    return pts, faces


def u_profile(half_w, height, radius, n_arc=10, z0=0.0):
    """Open 'U' cross-section in (x, z): up the left side, across the top through two rounded
    corners, down the right side. The floor closes the fourth side (three-quarter open jet)."""
    return compute.profile(half_w, z0, z0 + height, radius, n_arc, False)


def rounded_rect(half_w, z_lo, z_hi, radius, n_arc=6):
    """Closed rounded rectangle in (x, z), counter-clockwise in the (x, z) plane."""
    return compute.profile(half_w, z_lo, z_hi, radius, n_arc, True)


def loft(rings, closed, flip=False):
    """Skin consecutive rings. rings: list of (k, 3) arrays with equal k."""
    k = len(rings[0])
    pts = np.vstack(rings)
    return pts, compute.loft_faces(len(rings), k, closed, flip)


def disc(cx, cy, z_top, z_bot, radius, n=128):
    """Closed cylinder slab (top n-gon, side band, bottom n-gon)."""
    pts = compute.rings((cx, cy, 0.), (0., 0., 1.), [radius, radius],
                        [z_top, z_bot], n, xy=True).reshape(-1, 3)
    faces = [list(range(n)), list(range(2 * n - 1, n - 1, -1))]
    for j in range(n):
        j2 = (j + 1) % n
        faces.append([n + j, n + j2, j2, j])
    return pts, faces


def annulus(cx, cy, z_top, z_bot, r_in, r_out, n=128):
    """Flat ring with inner and outer side bands."""
    pts = compute.rings((cx, cy, 0.), (0., 0., 1.), [r_in, r_in, r_out, r_out],
                        [z_bot, z_top, z_top, z_bot], n, xy=True).reshape(-1, 3)
    faces = []
    for i in range(3):
        for j in range(n):
            j2 = (j + 1) % n
            faces.append([(i + 1) * n + j, (i + 1) * n + j2, i * n + j2, i * n + j])
    return pts, faces


def signed_volume(points, faces):
    """Positive for a closed mesh wound outward."""
    P = np.asarray(points, float)
    vol = 0.0
    for f in faces:
        p0 = P[f[0]]
        for i in range(1, len(f) - 1):
            vol += p0 @ np.cross(P[f[i]], P[f[i + 1]])
    return vol / 6.0


def orient_outward(points, faces, probe_face, outward):
    """Flip every face if probe_face's normal disagrees with the given outward direction."""
    if newell(np.asarray(points)[faces[probe_face]]) @ np.asarray(outward, float) < 0:
        return [f[::-1] for f in faces]
    return faces


def tube(rings, closed_path=False):
    """Skin rings (each a closed loop of k points) into a tube wound outward, with end caps
    facing away from the tube when the path is open."""
    k = len(rings[0])
    R = list(rings) + ([rings[0]] if closed_path else [])
    pts, faces = loft(R, closed=True)
    if closed_path:
        m = len(rings)
        pts = pts[: m * k]
        faces = [[i % (m * k) for i in f] for f in faces]
    # Side faces: outward means away from their own ring's centroid.
    f0 = faces[0]
    ring_c = np.asarray(rings[0], float).mean(axis=0)
    if newell(pts[f0]) @ (pts[f0].mean(axis=0) - ring_c) < 0:
        faces = [f[::-1] for f in faces]
    if not closed_path:
        # Each cap faces away along the path's own direction at that end (not the overall
        # first-to-last direction, which is perpendicular to both ends of a U-shaped path).
        n = len(R)
        cen = [np.asarray(r, float).mean(axis=0) for r in (R[0], R[1], R[-2], R[-1])]
        first, last = list(range(k)), list(range((n - 1) * k, n * k))
        if newell(pts[first]) @ (cen[1] - cen[0]) > 0:
            first.reverse()
        if newell(pts[last]) @ (cen[3] - cen[2]) < 0:
            last.reverse()
        faces = faces + [first, last]
    return pts, faces


def sweep(path, section, binormal, closed_path=False):
    """Sweep a closed 2D section along a polyline. A section point (n, b) lands at
    P + n * N + b * B, where B is the fixed binormal and N = T x B. For a u_profile path in an
    XZ plane with B = +Y, N points away from the profile centre, so n is an outward offset and
    b runs upstream. Returns a closed, outward-wound mesh (capped when the path is open)."""
    return tube(compute.sweep_rings(path, section, binormal, closed_path), closed_path)


def rect_section(n0, n1, b0, b1):
    return np.array([(n0, b0), (n1, b0), (n1, b1), (n0, b1)])


def circle_section(r, n=12, n_off=0.0, b_off=0.0):
    points = compute.rings((n_off, b_off, 0.), (0., 0., 1.), [r], [0.], n, xy=True)
    return points[0, :, :2]


def resample(path, spacing, margin=0.0):
    """Points every `spacing` along a polyline (arc length), keeping `margin` clear of each end.
    Returns (points, unit tangents)."""
    return compute.resample(path, spacing, margin)


def ngon_prism(centre, axis, radius, height, n=6, spin=0.0, chamfer=0.0):
    """Closed n-gon prism from centre along axis (a hex bolt head when n = 6). With chamfer > 0
    the far cap is inset by that much, giving the head a bevelled top."""
    radii, heights = [radius], [0.]
    if chamfer > 0:
        radii.append(radius)
        heights.append(height - chamfer)
    radii.append(radius - chamfer)
    heights.append(height)
    return tube(compute.rings(centre, axis, radii, heights, n, spin))
