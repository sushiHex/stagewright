"""Sample transform-only USD animation into a static override layer.

Run in the author process, separately from the renderer. Geometry, materials,
instances and transform-stack order remain composed from the original scene.
"""
import argparse
import math
from pathlib import Path

from pxr import Usd


def sample(source, destination, seconds, render_layer=None):
    source = source.resolve(strict=True)
    destination = destination.resolve()
    if destination.exists():
        raise FileExistsError(destination)
    if source == destination or not math.isfinite(seconds):
        raise ValueError("Use a new output path and a finite source time")
    original = Usd.Stage.Open(str(source))
    time = Usd.TimeCode(seconds * original.GetTimeCodesPerSecond())
    result = Usd.Stage.CreateInMemory()
    base = source if render_layer is None else render_layer.resolve(strict=True)
    result.GetRootLayer().subLayerPaths = [base.as_posix()]
    for key in ("upAxis", "metersPerUnit", "kilogramsPerUnit", "timeCodesPerSecond", "framesPerSecond", "defaultPrim"):
        value = original.GetMetadata(key)
        if value is not None:
            result.SetMetadata(key, value)
    for prim in original.Traverse(Usd.TraverseInstanceProxies()):
        for attr in prim.GetAttributes():
            if not attr.GetNumTimeSamples():
                continue
            if not str(attr.GetName()).startswith("xformOp:"):
                raise ValueError(f"Only transform animation is supported: {attr.GetPath()}")
            if prim.IsInstanceProxy():
                raise ValueError(f"Animated instance-proxy transforms are unsupported: {attr.GetPath()}")
            target = result.OverridePrim(prim.GetPath()).CreateAttribute(attr.GetName(), attr.GetTypeName())
            value = attr.Get(time)
            if value is None:
                target.Block()
            else:
                target.Set(value)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not result.GetRootLayer().Export(str(destination)):
        raise RuntimeError("USD transform sample export failed")
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--seconds", type=float, required=True)
    parser.add_argument("--render-layer", type=Path,
                        help="compose an existing render override below the sampled transforms")
    args = parser.parse_args()
    sample(args.source, args.destination, args.seconds, args.render_layer)
