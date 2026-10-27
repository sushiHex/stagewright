"""PNG and JPEG IO through nvImageCodec, with packed RGB host arrays."""
from pathlib import Path

import numpy as np
from nvidia import nvimgcodec


def read_rgb(path):
    if not Path(path).is_file():
        raise FileNotFoundError(path)
    image = nvimgcodec.Decoder().read(str(path))
    if image is None:
        raise RuntimeError(f"Could not decode {path}")
    return np.array(image.cpu(), copy=True)[..., :3]


def write_rgb(path, pixels):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rgb = np.ascontiguousarray(pixels[..., :3], dtype=np.uint8)
    params = None
    if path.suffix.lower() in (".jpg", ".jpeg"):
        params = nvimgcodec.EncodeParams(quality_type=nvimgcodec.QualityType.QUALITY,
                                         quality_value=92)
    result = nvimgcodec.Encoder().write(str(path), rgb, params=params)
    if result is None or not path.is_file():
        raise RuntimeError(f"Could not encode {path}")
