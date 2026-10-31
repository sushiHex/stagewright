"""Encode packed RGB frames with NVENC and mux MP4 through PyNvVideoCodec."""
from pathlib import Path
from collections import deque
from tempfile import TemporaryFile

import PyNvVideoCodec as nvc
import warp as wp

from image_io import ImageCodec
from video_pixels import to_nv12


def encode_mp4(paths, destination, fps, *, keyframe_interval=None):
    """Encode a sequence; interval 1 makes repeated endpoint images independent keyframes."""
    with ImageCodec() as codec:
        return _encode_mp4(paths, destination, fps, codec, keyframe_interval=keyframe_interval)


def _read_frames(paths, first, codec):
    yield paths[0], first
    for start in range(1, len(paths), 8):
        batch = paths[start:start + 8]
        # Decode on the consumer stream; DLPack retains the native image buffer.
        yield from zip(batch, codec.read_images(
            batch, cuda_stream=wp.get_stream("cuda:0").cuda_stream))


def _encode_mp4(paths, destination, fps, codec, *, keyframe_interval=None):
    paths = list(paths)
    if not paths:
        raise ValueError("No frames to encode")
    if fps <= 0 or 90000 % fps:
        raise ValueError("Frame rate must divide the 90 kHz MP4 clock")
    if keyframe_interval is not None and keyframe_interval < 1:
        raise ValueError("Keyframe interval must be positive")
    first = codec.read_rgb(paths[0])
    h, w = first.shape[:2]
    if w % 2 or h % 2:
        raise ValueError("H.264 4:2:0 needs even frame dimensions")
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".partial.mp4")
    # Convert explicitly: packed RGB input to the package encoder produces full-range
    # YUV without range metadata in this pinned version. NV12 preserves intended levels.
    keyframes = {} if keyframe_interval is None else {
        "gop": keyframe_interval, "idrperiod": keyframe_interval}
    encoder = nvc.CreateEncoder(w, h, "NV12", True, codec="h264", preset="P7",
                                fps=fps, rc="constqp", constqp=18, bf=0, **keyframes)
    muxer = nvc.FFmpegMuxer(str(temporary), nvc.MEDIA_FORMAT.MP4, "h264", w, h,
                            fps, 1, 1, 90000, encoder.GetSequenceParams())
    ticks = 90000 // fps
    packet_count = 0

    def mux(packets):
        nonlocal packet_count
        for packet in packets:
            # B-frames are disabled, so presentation and decode order coincide.
            if packet["picture_type"] == 1:
                raise RuntimeError("Unexpected B-frame in sequential MP4 encoder")
            stamp = packet_count * ticks
            if not muxer.Mux(packet["data"], stamp, stamp, ticks, 0,
                             int(packet["picture_type"] in (2, 3))):
                raise RuntimeError("MP4 mux failed")
            packet_count += 1

    try:
        unique_paths = list(dict.fromkeys(paths)) if keyframe_interval == 1 else paths
        if len(unique_paths) < len(paths):
            # Reuse independent frames without keeping decoded images in memory.
            pending_paths = deque()
            packet_locations = {}
            with TemporaryFile() as packet_store:
                def collect(packets):
                    for packet in packets:
                        if not pending_paths or packet["picture_type"] != 3:
                            raise RuntimeError("Expected an IDR packet for a pending frame")
                        path = pending_paths.popleft()
                        data = packet["data"]
                        packet_locations[path] = (packet_store.tell(), len(data))
                        packet_store.write(data)
                for path, rgb in _read_frames(unique_paths, first, codec):
                    if rgb.shape != (h, w, 3):
                        raise ValueError(f"Frame dimensions differ: {path}")
                    pending_paths.append(path)
                    collect(encoder.Encode(to_nv12(rgb)))
                collect(encoder.EndEncode())
                if pending_paths or len(packet_locations) != len(unique_paths):
                    raise RuntimeError("Encoder drain did not supply every unique frame")
                for path in paths:
                    offset, size = packet_locations[path]
                    packet_store.seek(offset)
                    data = packet_store.read(size)
                    if len(data) != size:
                        raise RuntimeError("Incomplete temporary packet read")
                    mux([{"data": data, "picture_type": 3}])
        else:
            for path, rgb in _read_frames(paths, first, codec):
                if rgb.shape != (h, w, 3):
                    raise ValueError(f"Frame dimensions differ: {path}")
                mux(encoder.Encode(to_nv12(rgb)))
            mux(encoder.EndEncode())
        if packet_count != len(paths):
            raise RuntimeError(f"Encoded {packet_count} packets for {len(paths)} frames")
        muxer.Finalize()
        # The package closes its buffered output in the muxer destructor.
        del muxer
        temporary.replace(destination)
    except BaseException:
        if "muxer" in locals():
            del muxer
        temporary.unlink(missing_ok=True)
        raise
    return destination
