"""PNG/JPEG IO through nvImageCodec, with sequence-scoped codec ownership."""
from pathlib import Path

import numpy as np
from nvidia import nvimgcodec


class ImageCodec:
    """Caller-owned, serial codec session. Returned arrays are independent snapshots."""

    def __init__(self):
        self._encoder = None
        self._decoder = None
        self._closed = False

    def __enter__(self):
        if self._closed:
            raise RuntimeError("Image codec session is closed")
        return self

    def __exit__(self, *exc):
        self.close()

    def close(self):
        self._encoder = None
        self._decoder = None
        self._closed = True

    def _open(self):
        if self._closed:
            raise RuntimeError("Image codec session is closed")

    def read_rgb(self, path):
        self._open()
        if not Path(path).is_file():
            raise FileNotFoundError(path)
        if self._decoder is None:
            self._decoder = nvimgcodec.Decoder()
        image = self._decoder.read(str(path))
        if image is None:
            raise RuntimeError(f"Could not decode {path}")
        return np.array(image.cpu(), copy=True)[..., :3]

    def read_rgb_batch(self, paths):
        """Decode a small batch in input order, returning owned RGB snapshots."""
        return [np.array(image.cpu(), copy=True)[..., :3]
                for image in self.read_images(paths)]

    def read_images(self, paths, *, cuda_stream=0):
        """Return native decoded images in order, with their buffers owned by each image."""
        self._open()
        paths = list(paths)
        for path in paths:
            if not Path(path).is_file():
                raise FileNotFoundError(path)
        if not paths:
            return []
        if self._decoder is None:
            self._decoder = nvimgcodec.Decoder()
        images = self._decoder.read([str(path) for path in paths], cuda_stream=cuda_stream)
        if len(images) != len(paths):
            raise RuntimeError("Incomplete image decode batch")
        for path, image in zip(paths, images):
            if image is None:
                raise RuntimeError(f"Could not decode {path}")
        return images

    def write_rgb(self, path, pixels):
        self._open()
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        rgb = np.ascontiguousarray(pixels[..., :3], dtype=np.uint8)
        params = None
        if path.suffix.lower() in (".jpg", ".jpeg"):
            params = nvimgcodec.EncodeParams(quality_type=nvimgcodec.QualityType.QUALITY,
                                             quality_value=92)
        if self._encoder is None:
            self._encoder = nvimgcodec.Encoder()
        result = self._encoder.write(str(path), rgb, params=params)
        if result is None or not path.is_file():
            raise RuntimeError(f"Could not encode {path}")


def read_rgb(path):
    with ImageCodec() as codec:
        return codec.read_rgb(path)


def write_rgb(path, pixels):
    with ImageCodec() as codec:
        codec.write_rgb(path, pixels)
