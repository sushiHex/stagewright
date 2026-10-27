"""Numerical and codec regression checks. Writes fixtures only under build/checks."""
import ctypes
from pathlib import Path

import numpy as np
import PyNvVideoCodec as nvc
import warp as wp

import meshlib as mesh
import texture_compute as tex
from image_io import read_rgb, write_rgb
from image_compute import RGBDownsampler, downsample_rgb
from video_io import encode_mp4

OUT = Path(__file__).resolve().parent.parent / "build" / "checks"


def check_spectrum():
    n = 64
    raw = wp.empty((n, n), dtype=wp.vec2d, device=tex.DEVICE)
    wp.launch(tex._white, (n, n), inputs=[raw, 11, n], device=tex.DEVICE)
    # Independent Fourier reference for the custom radix-two Warp implementation.
    freq = np.hypot(np.fft.fftfreq(n)[:, None], np.fft.fftfreq(n)[None, :])
    freq[0, 0] = 1
    white = raw.numpy()[..., 0]
    for beta in (0.6, 2.0, 3.2):
        spectrum = np.fft.fft2(white) * freq ** (-beta / 2)
        spectrum[0, 0] = 0
        expected = np.fft.ifft2(spectrum).real
        expected = (expected - expected.mean()) / expected.std()
        actual = tex.noise(n, beta, 11).numpy()
        np.testing.assert_allclose(actual, expected, atol=1e-10)
        np.testing.assert_array_equal(actual, tex.noise(n, beta, 11).numpy())


def check_mesh():
    points = np.array([[-1., -2., 0.], [1., -2., 0.], [1., 2., 0.], [-1., 2., 0.]])
    faces = [[0, 1, 2, 3]]
    np.testing.assert_allclose(mesh.creased_normals(points, faces, 35), [[0., 0., 1.]] * 4)
    np.testing.assert_allclose(mesh.box_uv(points, faces, (2., 4.)),
                               [[-.5, -.5], [.5, -.5], [.5, .5], [-.5, .5]])
    # A bent path checks tangent interpolation, margins and nonuniform segment lengths.
    path = [[0., 0., 0.], [0., 3., 0.], [4., 3., 0.]]
    p, t = mesh.resample(path, 2., .5)
    np.testing.assert_allclose(p, [[0., 1.25, 0.], [0., 2.75, 0.], [1.25, 3., 0.], [2.75, 3., 0.]])
    np.testing.assert_allclose(t, [[0., 1., 0.], [0., 1., 0.], [1., 0., 0.], [1., 0., 0.]])
    p, f = mesh.disc(2., 3., 5., 1., 4., 32)
    np.testing.assert_allclose(p[0], [6., 3., 5.])
    np.testing.assert_allclose(p[32], [6., 3., 1.])
    assert mesh.signed_volume(p, f) > 0
    profile = mesh.u_profile(4., 7., 1., 8)
    np.testing.assert_allclose(profile[[0, -1]], [[-4., 0.], [4., 0.]])
    sec = mesh.rect_section(-1., 1., -1., 1.)
    p, f = mesh.sweep([[0., 0., 0.], [0., 3., 0.]], sec, (0., 0., 1.))
    np.testing.assert_allclose(p[4:] - p[:4], [[0., 3., 0.]] * 4)
    assert mesh.signed_volume(p, f) > 0
    # Degenerate faces must produce finite corner normals.
    assert np.isfinite(mesh.creased_normals([[0., 0., 0.]] * 3, [[0, 1, 2]], 35)).all()


def check_sampling():
    pixels = np.arange(48, dtype=np.uint8).reshape(4, 4, 3)
    expected = np.array([[[9, 10, 11], [15, 16, 17]],
                         [[30, 31, 32], [36, 37, 38]]], dtype=np.uint8)
    np.testing.assert_array_equal(downsample_rgb(pixels, 2), expected)
    np.testing.assert_array_equal(downsample_rgb(pixels, 4), [[[23, 24, 25]]])
    rgba = np.concatenate((pixels, np.full((4, 4, 1), 255, np.uint8)), axis=2)
    np.testing.assert_array_equal(downsample_rgb(rgba, 2), expected)
    same = downsample_rgb(rgba, 1)
    np.testing.assert_array_equal(same, pixels)
    assert not np.shares_memory(same, rgba) and same.flags.c_contiguous
    for bad, factor in ((pixels, 0), (pixels, True), (pixels[:3], 2)):
        try:
            downsample_rgb(bad, factor)
        except (TypeError, ValueError):
            pass
        else:
            raise AssertionError("Invalid downsample request accepted")

    workspace = RGBDownsampler(2)
    first = workspace(rgba)
    input_buffer, output_buffer = workspace._input, workspace._output
    second = workspace(np.zeros_like(rgba))
    assert workspace._input is input_buffer and workspace._output is output_buffer
    np.testing.assert_array_equal(first, expected)
    np.testing.assert_array_equal(second, np.zeros_like(expected))
    assert first.flags.owndata and first.flags.c_contiguous
    assert not np.shares_memory(first, second)
    resized = np.arange(8 * 4 * 3, dtype=np.uint8).reshape(8, 4, 3)
    np.testing.assert_array_equal(workspace(resized), downsample_rgb(resized, 2))
    np.testing.assert_array_equal(workspace(pixels), expected)
    np.testing.assert_array_equal(first, expected)
    np.testing.assert_array_equal(RGBDownsampler(4)(rgba), [[[23, 24, 25]]])
    np.testing.assert_array_equal(RGBDownsampler(1)(rgba), pixels)


def check_capture_policy():
    """CPU-only scheduler check: discarded warmups must not map pixels."""
    from types import SimpleNamespace
    from unittest.mock import Mock, patch
    import rtx

    def result(**products):
        return {name: SimpleNamespace(frames=frames) for name, frames in products.items()}

    class Renderer:
        def __init__(self):
            frame = lambda progress, done: SimpleNamespace(progression=progress, converged=done)
            self.results = iter((result(A=[frame(1, False)], B=[]),
                                 result(A=[frame(2, True)], B=[frame(1, False)]),
                                 result(B=[frame(2, False)])))
            self.calls = []

        def step(self, **kwargs):
            self.calls.append(kwargs)
            return next(self.results)

    discarded, captured = Renderer(), Renderer()
    reader = Mock(side_effect=lambda frame, name: name)
    with patch.object(rtx, "pixels", side_effect=AssertionError("Unexpected pixel map")):
        markers, status = rtx.converge(discarded, ["A", "B"], 7, .25, 3,
                                       capture=False, read_pixels=reader)
        reader.assert_not_called()
        images, captured_status = rtx.converge(captured, ["A", "B"], 7, .25, 3,
                                               read_pixels=reader)
        assert markers == {"A": None, "B": None}
        assert images == {"A": "A/Color", "B": "B/Color"}
        assert status == captured_status == {"A": (2, True), "B": (2, False)}
        assert discarded.calls == captured.calls
        assert [call["render_products"] for call in discarded.calls] == [{"A", "B"}, {"A", "B"}, {"B"}]
        empty = Mock()
        empty.step.return_value = {}
        assert rtx.converge(empty, ["A"], 7, .25, 2, capture=False) == ({}, {})


def check_codecs():
    OUT.mkdir(parents=True, exist_ok=True)
    paths = []
    colors = ([230, 30, 15], [15, 30, 230])
    for i, color in enumerate(colors):
        pixels = np.empty((256, 256, 3), dtype=np.uint8)
        pixels[:] = color
        path = OUT / f"color_{i}.png"
        write_rgb(path, pixels)
        np.testing.assert_array_equal(read_rgb(path), pixels)
        write_rgb(OUT / f"color_{i}.jpg", pixels)
        np.testing.assert_allclose(read_rgb(OUT / f"color_{i}.jpg").mean((0, 1)), color, atol=3)
        paths.append(path)
    output = encode_mp4(paths * 12, OUT / "colors.mp4", 24)
    decoder = nvc.CreateSimpleDecoder(str(output), outputColorType=nvc.OutputColorType.RGB)
    metadata = decoder.get_stream_metadata()
    assert metadata.num_frames == 24 and metadata.average_fps == 24
    frames = decoder.get_batch_frames_by_index([0, 1, 22, 23])
    assert len(frames) == 4
    for frame, expected in zip(frames, (colors[0], colors[1], colors[0], colors[1])):
        memory = (ctypes.c_uint8 * frame.framesize()).from_address(frame.GetPtrToPlane(0))
        pixels = np.ctypeslib.as_array(memory).reshape(frame.shape)
        np.testing.assert_allclose(pixels.mean((0, 1)), expected, atol=3)
    try:
        encode_mp4([paths[0], OUT / "missing.png"], OUT / "colors.mp4", 24)
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("Missing frame was accepted")
    assert output.is_file() and not output.with_suffix(".partial.mp4").exists()


def check_sample_batches():
    import render as rendering

    for budget in range(1, 130):
        for limit in (1, 2, 3, 4, 8):
            batch = rendering.iteration_samples(budget, limit)
            assert 1 <= batch <= min(budget, limit) and budget % batch == 0
    assert rendering.iteration_samples(0, 4) is None
    for budget, limit in ((-1, 4), (64, 0), (64, -1)):
        try:
            rendering.iteration_samples(budget, limit)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid sample budget/batch accepted")
    options = dict(scene=rendering.DEFAULT_SCENE, products=["Hero", "Main"], res=(320, 180),
                   ghost=False, qc=False, out_dir=OUT / "sample_settings")
    text = rendering.write_override(**options, spp=6, sample_batch=4).read_text()
    assert text.count("custom uint omni:rtx:pt:samplesPerPixel = 6") == 2
    assert text.count("custom int omni:rtx:pt:samplesPerIteration = 2") == 2
    text = rendering.write_override(**options, spp=64, sample_batch=1).read_text()
    assert text.count("custom int omni:rtx:pt:samplesPerIteration = 1") == 2
    text = rendering.write_override(**options, spp=0, sample_batch=4).read_text()
    assert "samplesPerPixel" not in text and "samplesPerIteration" not in text


def check_motion_routes():
    import contextlib
    import io
    from unittest.mock import patch
    import render_motion as motion

    custom = OUT / "private_fixture" / "present.usda"
    with contextlib.redirect_stderr(io.StringIO()):
        try:
            motion.parse_args(["--scene", str(custom), "--no-render", "--encode"])
        except SystemExit as error:
            assert error.code == 2
        else:
            raise AssertionError("Custom scene accepted the public frame directory")
    orbit = motion.parse_args(["--product", "Orbit360", "--no-render", "--encode"])
    assert (orbit.count, orbit.fps, orbit.loop) == (360, 24, True)
    assert orbit.out == motion.frame_directory("Orbit360")
    for product in ("Dolly", "Orbit360"):
        with contextlib.redirect_stderr(io.StringIO()):
            try:
                motion.parse_args(["--scene", str(custom), "--product", product,
                                   "--out", str(motion.frame_directory(product)), "--no-render", "--encode"])
            except SystemExit as error:
                assert error.code == 2
            else:
                raise AssertionError("Custom scene accepted a built-in public frame directory")
    alternate = motion.parse_args(["--scene", str(custom), "--product", "Orbit360", "--count", "8",
                                    "--fps", "30", "--loop", "--out", str(OUT / "custom_orbit"),
                                    "--no-render", "--encode"])
    assert (alternate.count, alternate.fps, alternate.loop) == (8, 30, True)
    frames = OUT / "custom_frames"
    frames.mkdir(parents=True, exist_ok=True)
    (frames / "0000.png").write_bytes((OUT / "color_0.png").read_bytes())
    args = motion.parse_args(["--scene", str(custom), "--out", str(frames),
                              "--count", "1", "--no-render", "--encode"])
    assert args.count == 1
    with patch("video_io.encode_mp4") as encoder, patch("subprocess.run") as external:
        motion.encode(frames, 640, 12, fps=24, count=1)
        destination = encoder.call_args.args[1]
        assert destination == frames.resolve() / "dolly.mp4"
        assert destination != motion.OUT / "dolly.mp4"
        external.assert_not_called()


if __name__ == "__main__":
    check_spectrum()
    check_mesh()
    check_sampling()
    check_capture_policy()
    check_sample_batches()
    check_codecs()
    check_motion_routes()
    print("PASS: spectral reference, mesh geometry, filtered downsampling, PNG/JPEG, MP4 color/frame order and private output separation")
