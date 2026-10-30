"""Observe published USD revisions through one RTX owner and NVIDIA WebRTC."""
import argparse
import functools
import http.server
import json
import math
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time
import urllib.parse

os.environ.setdefault("OVRTX_SKIP_USD_CHECK", "1")
import ovstage
import ovrtx
import rtx as rt
import ovstream
from ovstream_utils.messaging import AppMessenger

ROOT = Path(__file__).resolve().parents[1]


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if urllib.parse.urlsplit(self.path).path == "/vendor/ov-web-rtc.umd.cjs":
            library = ROOT / "build/deps/ov-web-rtc-6.8.2/ov-web-rtc.umd.cjs"
            if not library.is_file():
                self.send_error(404, "Run the viewer dependency setup")
                return
            blob = library.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript")
            self.send_header("Content-Length", str(len(blob)))
            self.end_headers()
            self.wfile.write(blob)
        else:
            super().do_GET()

    def log_message(self, *args):
        pass


def wrapper(source, directory, revision, width, height):
    destination = directory / f"view-{revision:04d}.usda"
    result = subprocess.run([sys.executable, str(ROOT / "tools/viewer_scene.py"),
                             str(source), str(destination), "--width", str(width),
                             "--height", str(height)], check=True, capture_output=True, text=True)
    return destination, json.loads(result.stdout)


def observe(publications, session, port=8765, width=960, height=540, run_file=None):
    publications, session = publications.resolve(), session.resolve()
    session.mkdir(parents=True, exist_ok=False)
    commands = queue.SimpleQueue()
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port),
        functools.partial(Handler, directory=str(ROOT / "viewer")))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    # Initialize OVStage before Renderer, and Renderer before USD population.
    stage = ovstage.Stage("observer-initial")
    renderer = ovrtx.Renderer()
    renderer.attach_ovstage(stage)
    waiting_scene, waiting_metadata = wrapper(ROOT / "viewer/empty.usda", session, 0, width, height)
    ovstage.population.open_usd(stage, str(waiting_scene), ordinal=1, time=0.0)
    rt.publish(stage, 1)
    ovstream.initialize()
    server = ovstream.Server(ovstream.ServerType.WEBRTC)
    messenger = AppMessenger(server)
    for event in ("select_revision", "seek", "play", "latest"):
        messenger.on(event, lambda payload, event=event: commands.put((event, payload)))
    server.start(ovstream.ServerConfig(width=width, height=height,
                 target_fps=30, cuda_device=0, video_input=ovstream.VideoInput.TENSOR,
                 webrtc_signal_port=49100))
    print(f"Viewer: http://127.0.0.1:{port}", flush=True)
    state = {"revisions": [], "selected_revision": None, "latest_revision": None,
             "playing": False, "seconds": 0.0, "start": 0.0, "end": 0.0,
             "run": {}, "error": None, "field": {"status": "unavailable"}}
    views, rejected, available = {}, set(), {}
    desired, follow, candidate = None, True, None
    metadata, pending, operation = waiting_metadata, None, None
    ordinal, rendered, sent_state, polled = 1, None, 0.0, 0.0
    playhead, held, stalled = 0.0, False, False
    # Failed wrappers have blocking destructors and no public discard method.
    # Keep known-terminal failures alive until after renderer destruction.
    retired = []
    tick, queued_at, next_render = time.monotonic(), 0.0, 0.0

    def fatal(message):
        state["error"] = message
        print(message, flush=True)
        try:
            messenger.send("state", state)
        finally:
            os._exit(2)

    def restore_candidate(error):
        nonlocal stage, metadata, ordinal, rendered, candidate, held
        state["error"] = str(error)
        state["playing"] = False
        held = True
        if candidate is None:
            return
        rejected.add(candidate["revision"])
        previous_stage, previous_metadata, previous_ordinal, previous_rendered = candidate["previous"]
        try:
            renderer.detach_ovstage()
            renderer.attach_ovstage(previous_stage)
            renderer.reset(0.0)
        except Exception as restore_error:
            fatal(f"Cannot restore the last revision: {restore_error}. Restart the observer.")
        stage.destroy()
        stage, metadata, ordinal, rendered = (previous_stage, previous_metadata,
                                               previous_ordinal, previous_rendered)
        candidate = None

    def revision(value):
        return value if type(value) is int and value in available else None

    try:
        while True:
            now = time.monotonic()
            if now - polled > .25:
                polled = now
                revision_dir = (publications / "revisions").resolve()
                available = {int(path.stem): path.resolve()
                    for path in sorted(revision_dir.glob("*.usdz"))
                    if path.stem.isascii() and path.stem.isdigit()
                    and path.resolve().parent == revision_dir and path.is_file()}
                state["revisions"] = [{"revision": number, "scene": f"revisions/{path.name}"}
                                      for number, path in available.items()]
                try:
                    latest = revision(json.loads((publications / "current.json").read_text())["revision"])
                    if latest is None:
                        raise ValueError("the current revision is not published")
                    state["latest_revision"] = latest
                    if follow:
                        desired = latest
                except FileNotFoundError:
                    pass
                except (OSError, ValueError, KeyError, TypeError) as error:
                    state["error"] = f"Publication not available: {error}"
                run = run_file or publications.parent / "run.json"
                if run.is_file():
                    try:
                        record = json.loads(run.read_text())
                        if not isinstance(record, dict):
                            raise ValueError("Run metadata must be an object")
                        state["run"] = {key: record.get(key) for key in
                            ("prompt", "requested_model", "requested_effort", "actual_model", "effective_effort", "status")}
                        state["field"] = record.get("field", {"status": "unavailable"})
                    except (OSError, ValueError):
                        pass
            while not commands.empty():
                event, payload = commands.get()
                try:
                    if not isinstance(payload, dict):
                        raise ValueError("command payload must be an object")
                    if event == "play":
                        if type(payload.get("playing")) is not bool:
                            raise ValueError("playing must be true or false")
                        state["playing"] = payload["playing"]
                    elif event == "seek":
                        seconds = payload.get("seconds")
                        if type(seconds) not in (int, float) or not math.isfinite(seconds):
                            raise ValueError("replay time must be finite")
                        playhead = max(state["start"], min(state["end"], seconds))
                    elif event == "select_revision":
                        selected = revision(payload.get("revision"))
                        if selected is None:
                            raise ValueError("revision is not published")
                        desired, follow = selected, False
                        rejected.discard(desired)
                    elif event == "latest":
                        desired, follow = state["latest_revision"], True
                        rejected.discard(desired)
                    held = False
                except (ValueError, TypeError, OverflowError) as error:
                    state["error"] = f"Command not accepted: {error}"
            if state["playing"] and state["end"] > state["start"]:
                span = state["end"] - state["start"]
                playhead = state["start"] + (playhead-state["start"]+now-tick) % span
            tick = now
            # A candidate never changes the state that describes the last displayed frame.
            if (operation is None and candidate is None and desired in available
                    and desired != state["selected_revision"] and desired not in rejected):
                candidate_stage = None
                try:
                    if desired not in views:
                        views[desired] = wrapper(available[desired], session, desired, width, height)
                    scene, next_metadata = views[desired]
                    start, end = next_metadata["start"], next_metadata["end"]
                    if not all(math.isfinite(value) for value in (start, end)) or end < start:
                        raise ValueError("revision replay bounds are invalid")
                    candidate_stage = ovstage.Stage(f"revision-{desired}")
                    ovstage.population.open_usd(candidate_stage, str(scene), ordinal=1, time=start)
                    rt.publish(candidate_stage, 1)
                except Exception as error:
                    rejected.add(desired)
                    state["error"] = f"Revision {desired} failed: {error}"
                    if candidate_stage is not None:
                        candidate_stage.destroy()
                else:
                    # Attach/detach failures can leave the renderer partly torn down.
                    # They cannot be treated as ordinary rejected scene content.
                    try:
                        renderer.detach_ovstage()
                        renderer.attach_ovstage(candidate_stage)
                    except Exception as error:
                        fatal(f"Cannot attach revision {desired}: {error}. Restart the observer.")
                    candidate = {"revision": desired, "metadata": next_metadata,
                                 "previous": (stage, metadata, ordinal, rendered)}
                    stage, metadata, ordinal, rendered = candidate_stage, next_metadata, 1, None
                    held = False
            if operation is None and metadata is not None and not held and now >= next_render:
                try:
                    next_render = now + 1/30
                    requested = metadata["start"] if candidate is not None else playhead
                    if rendered != requested:
                        ordinal += 1
                        rt.seek(stage, ordinal, requested)
                        renderer.reset(0.0)
                        rendered = requested
                    operation = renderer.step_async({metadata["product"]}, 1/30, ordinal=ordinal)
                    queued_at = now
                except Exception as error:
                    restore_candidate(f"Render update failed: {error}")
            if operation is not None and not stalled:
                try:
                    if pending is None:
                        pending = operation.wait(timeout_ns=0)
                    result = pending.fetch(timeout_ns=0) if pending is not None else None
                except Exception as error:
                    terminal = pending is not None
                    if not terminal:
                        try:
                            terminal = operation.query_status().state in (
                                ovrtx.EventStatus.COMPLETED, ovrtx.EventStatus.FAILURE)
                        except Exception:
                            pass
                    if terminal:
                        retired.append((operation, pending))
                        pending, operation = None, None
                        restore_candidate(f"Render update failed: {error}")
                    else:
                        stalled = True
                        state["error"] = f"Render state is unknown: {error}. Restart the observer."
                else:
                    if result is not None:
                        valid = False
                        error = None
                        frame = None
                        try:
                            frame = rt.frame_of(result, metadata["product"])
                            if frame is not None:
                                delivered = True
                                if metadata["var"] not in frame.render_vars:
                                    raise ValueError("the frame has no streaming image")
                                # stream_video copies into server-owned storage before return.
                                if server.is_client_connected or candidate is not None:
                                    mapped = frame.render_vars[metadata["var"]].map(device=ovrtx.Device.CUDA)
                                    video = None
                                    try:
                                        mapped.wait()
                                        video = ovstream.VideoFrame.from_dlpack(mapped)
                                        try:
                                            server.stream_video(video)
                                        except ovstream.OvstreamError as transport_error:
                                            delivered = False
                                            expected = (transport_error.status == ovstream.ApiStatus.INVALID_STATE
                                                or "NVST_R_INVALID_STATE" in str(transport_error)
                                                or "NVST_R_FRAME_DROPPED" in str(transport_error))
                                            if not expected:
                                                raise
                                    finally:
                                        video = None
                                        try:
                                            mapped.unmap()
                                        finally:
                                            del mapped
                                valid = candidate is None or delivered
                        except Exception as frame_error:
                            error = str(frame_error)
                        finally:
                            del frame, result, pending, operation
                            pending, operation = None, None
                        if error is not None:
                            restore_candidate(f"Frame not available: {error}")
                        elif valid:
                            if candidate is not None:
                                previous_stage = candidate["previous"][0]
                                state.update(selected_revision=candidate["revision"],
                                             start=metadata["start"], end=metadata["end"], error=None)
                                playhead = rendered
                                candidate = None
                                previous_stage.destroy()
                            state.update(seconds=rendered)
                            if state["error"] == "Render update pending. The last frame is retained.":
                                state["error"] = None
                if operation is not None and now-queued_at > 30 and not stalled:
                    state["error"] = "Render update pending. The last frame is retained."
            if server.is_client_connected and now-sent_state > .1:
                try:
                    messenger.send("state", state)
                except ovstream.OvstreamError as transport_error:
                    if (transport_error.status != ovstream.ApiStatus.INVALID_STATE
                            and "NVST_R_INVALID_STATE" not in str(transport_error)):
                        raise
                sent_state = now
            time.sleep(.005)
    except KeyboardInterrupt:
        pass
    except Exception as error:
        print(f"Observer failed: {type(error).__name__}: {error}", flush=True)
        raise
    finally:
        httpd.shutdown()
        if operation is not None:
            print("Native operation remains pending; close the observer process.", flush=True)
            os._exit(2)
        try:
            server.close()
            ovstream.shutdown()
            renderer.detach_ovstage()
            renderer.destroy()
            stage.destroy()
            if candidate is not None:
                candidate["previous"][0].destroy()
        except Exception as error:
            print(f"Observer cleanup failed: {error}", flush=True)
            os._exit(2)
        retired.clear()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("publications", type=Path)
    parser.add_argument("--session", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--width", type=int, default=960)
    parser.add_argument("--height", type=int, default=540)
    parser.add_argument("--run", type=Path)
    args = parser.parse_args()
    observe(args.publications, args.session, args.port, args.width, args.height, args.run)
