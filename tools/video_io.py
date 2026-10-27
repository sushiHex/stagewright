"""Encode packed RGB frames with NVENC and mux MP4 through PyNvVideoCodec."""
from pathlib import Path

import PyNvVideoCodec as nvc

from image_io import read_rgb
from video_pixels import to_nv12


def encode_mp4(paths, destination, fps):
    paths = list(paths)
    if not paths:
        raise ValueError("No frames to encode")
    if fps <= 0 or 90000 % fps:
        raise ValueError("Frame rate must divide the 90 kHz MP4 clock")
    first = read_rgb(paths[0])
    h, w = first.shape[:2]
    if w % 2 or h % 2:
        raise ValueError("H.264 4:2:0 needs even frame dimensions")
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".partial.mp4")
    # Convert explicitly: packed RGB input to the package encoder produces full-range
    # YUV without range metadata in this pinned version. NV12 preserves intended levels.
    encoder = nvc.CreateEncoder(w, h, "NV12", True, codec="h264", preset="P7",
                                fps=fps, rc="constqp", constqp=18, bf=0)
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
        for i, path in enumerate(paths):
            rgb = first if i == 0 else read_rgb(path)
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
