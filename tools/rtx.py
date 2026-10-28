# Small shared layer over ovrtx / ovstage for tools/render.py, tools/render_motion.py and
# tools/smoke.py. Written against the documented ovrtx 0.6 Python API.
#
# Never import pxr in a process that imports this: ovrtx carries its own USD runtime.
import contextlib

import numpy as np


@contextlib.contextmanager
def open_renderer():
    """An ovrtx Renderer that is destroyed when the block ends."""
    import ovrtx

    rtx = ovrtx.Renderer()
    try:
        yield rtx
    finally:
        rtx.destroy()


def publish(scene, ordinal):
    """Make everything written up to `ordinal` visible to the renderer."""
    import ovstage

    scene.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()


def seek(scene, ordinal, seconds):
    """Advance USD time and propagate sampled properties at `seconds`, as ordinal `ordinal`."""
    import ovstage

    ovstage.population.update_from_usd_time(scene, ordinal=ordinal, time=seconds)
    publish(scene, ordinal)


@contextlib.contextmanager
def loaded_scene(rtx, label, usd_file):
    """A fresh ovstage scene attached to `rtx`, with `usd_file` loaded as ordinal 1 at time 0.
    Detached and destroyed when the block ends."""
    import ovstage

    scene = ovstage.Stage(label)
    rtx.attach_ovstage(scene)
    try:
        ovstage.population.open_usd(scene, str(usd_file), ordinal=1, time=0.0)
        publish(scene, 1)
        yield scene
    finally:
        rtx.detach_ovstage()
        scene.destroy()


def frame_of(step_result, product, index=-1):
    """One frame a step produced for `product` (the newest by default), or None."""
    if product not in step_result:
        return None
    produced = list(step_result[product].frames)
    return produced[index] if produced else None


def pixels(frame, render_var):
    """Copy a render var into host memory as a numpy array. The device mapping is released before
    returning, and no view into it survives."""
    import ovrtx

    handle = frame.render_vars[render_var].map(device=ovrtx.Device.CPU)
    try:
        shared = np.from_dlpack(handle)
        host = shared.copy()
        del shared
    finally:
        handle.unmap()
    return host


def converge(rtx, products, ordinal, delta_time, max_steps, var="Color", *,
             capture=True, read_pixels=None):
    """Step products to convergence and read their final render vars.

    Return (images, status), keyed by product. Status holds the last (progression,
    converged) pair; products that never produce a frame have no image entry.
    Captures must converge before readback. Discarded warmups (capture=False) may
    reach the step limit and return None markers without mapping pixels.
    read_pixels optionally replaces the default host-copy reader.
    """
    reader = pixels if read_pixels is None else read_pixels
    waiting = set(products)
    images, status = {}, {}
    for k in range(max_steps):
        final = k == max_steps - 1
        result = rtx.step(render_products=set(waiting), ordinal=ordinal, delta_time=delta_time)
        for product in list(waiting):
            fr = frame_of(result, product)
            if fr is None:
                continue
            status[product] = (fr.progression, fr.converged)
            if not fr.converged and not final:
                continue
            if capture and not fr.converged:
                raise RuntimeError(f"{product}: did not converge within {max_steps} steps")
            images[product] = reader(fr, f"{product}/{var}") if capture else None
            waiting.discard(product)
        del result
        if not waiting:
            break
    return images, status
