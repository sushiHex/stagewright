"""Verify the canonical loop's container, decoded seam and repeated-pose images."""
import ctypes
import hashlib
import json
from pathlib import Path

import numpy as np
import PyNvVideoCodec as nvc

from image_io import read_rgb
from project_paths import ROOT, SCENES, MOTION_SETTINGS

PRODUCT = "Orbit360"
FRAMES = ROOT / "build" / "frames" / "orbit360"
VIDEO = ROOT / "build" / "out" / "orbit360.mp4"
RECORD = ROOT / "build" / "checks" / "orbit360_verified.json"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def difference(a, b):
    return float(np.abs(a.astype(np.int16) - b.astype(np.int16)).mean())


def repeated_pose(first, repeat):
    require(first.shape == repeat.shape, "Loop repeat image dimensions differ")
    delta = np.abs(first.astype(np.int16) - repeat.astype(np.int16))
    # Fixed image-acceptance tolerances allow stochastic path tracing, while rejecting
    # startup streaming/exposure changes. They do not require identical random samples.
    require(float(delta.mean()) <= 1.0 and float(np.percentile(delta, 99)) <= 8.0,
            "Repeated loop pose changes visibly after the cycle")
    require(abs(float(first.mean()) - float(repeat.mean())) <= 0.5,
            "Loop startup and closure brightness differ")


def seam_step(images, count):
    before = difference(images[count - 2], images[count - 1])
    after = difference(images[0], images[1])
    closing = difference(images[count - 1], images[0])
    require(closing <= 1.5 * max(before, after) + 1.0,
            "Loop boundary is a visual outlier compared with its adjacent motion steps")
    require(not np.array_equal(images[count - 1], images[0]),
            "Loop contains an encoded duplicate endpoint")


def check():
    RECORD.unlink(missing_ok=True)
    settings = MOTION_SETTINGS[PRODUCT]
    count, fps = settings["frames"], settings["fps"]
    require(settings["loop"], "The selected motion is not periodic")
    paths = [FRAMES / f"{i:04d}.png" for i in range(count)]
    require(all(path.is_file() for path in paths), "The numeric loop frame sequence is incomplete")
    indices = sorted({0, 1, 2, count // 4, count // 2, 3 * count // 4, count - 2, count - 1})
    source = {i: read_rgb(paths[i]) for i in indices}
    height, width = source[0].shape[:2]
    require(width * 9 == height * 16, "Loop output must match the camera's 16:9 aspect ratio")
    for i in (0, 1):
        repeated_pose(source[i], read_rgb(FRAMES / f"_loop_{i:04d}.png"))
    seam_step(source, count)
    require(all(not np.array_equal(source[0], source[i]) for i in (count // 4, count // 2, 3 * count // 4)),
            "Quarter-cycle views do not show actual camera motion")

    demux = nvc.CreateDemuxer(str(VIDEO))
    require((demux.Width(), demux.Height()) == (width, height), "Container dimensions differ from the source")
    require(demux.AvgFrameRateNum() == fps * demux.AvgFrameRateDen(), "Container frame rate differs")
    time_num, time_den = demux.GetTimebaseNum(), demux.GetTimebaseDen()
    packets = [(int(packet.pts), int(packet.dts), int(packet.duration))
               for packet in demux if packet.is_video and packet.bsl > 0]
    require(len(packets) == count, "Container has missing frames or an extra closure frame")
    for i, (pts, dts, duration) in enumerate(packets):
        require(pts == dts, "Unexpected reordered loop packet")
        require(pts * time_num * fps == i * time_den, "Loop timestamps skip or repeat")
        require(duration * time_num * fps == time_den, "Loop packet duration is not uniform")

    decoder = nvc.CreateSimpleDecoder(str(VIDEO), outputColorType=nvc.OutputColorType.RGB)
    metadata = decoder.get_stream_metadata()
    require(metadata.num_frames == count and metadata.average_fps == fps, "Decoded frame count or rate differs")
    frames = decoder.get_batch_frames_by_index(indices)
    require(len(frames) == len(indices), "Could not decode all seam and quarter-cycle views")
    decoded = {}
    for i, frame in zip(indices, frames):
        memory = (ctypes.c_uint8 * frame.framesize()).from_address(frame.GetPtrToPlane(0))
        pixels = np.ndarray(frame.shape, dtype=np.uint8, buffer=memory, strides=frame.strides).copy()
        require(pixels.shape == source[i].shape and difference(pixels, source[i]) < 6.0,
                f"Decoded loop frame {i} differs from its source")
        decoded[i] = pixels
    seam_step(decoded, count)
    record = {"product": PRODUCT, "frames": count, "fps": fps, "width": width, "height": height,
              "video_sha256": digest(VIDEO), "scene_sha256": digest(SCENES / "present.usda"),
              "repeated_poses": "pass", "source_and_decoded_seam": "pass",
              "container_timestamps": "pass"}
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    temporary = RECORD.with_suffix(".tmp")
    temporary.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    temporary.replace(RECORD)
    print("PASS: unique loop frames, repeat-pose stability, source/decoded seam and uniform container timing")


if __name__ == "__main__":
    check()
