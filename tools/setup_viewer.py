"""Fetch the pinned NVIDIA browser runtime into ignored build dependencies."""
import base64
import hashlib
import io
from pathlib import Path
import tarfile
import urllib.request

VERSION = "6.8.2"
URL = ("https://edge.urm.nvidia.com/artifactory/api/npm/omniverse-client-npm/"
       "@nvidia/ov-web-rtc/-/@nvidia/ov-web-rtc-6.8.2.tgz")
INTEGRITY = "s2xNYlKg7SjxQo++MDm8aE3tuGdDHsLzaQnJzEdcI27Uf1wVwmNDueGOccJCGLk18HNsVin4+vePdJBNvnRnFQ=="


def setup():
    destination = Path(__file__).resolve().parents[1] / "build/deps" / f"ov-web-rtc-{VERSION}"
    blob = urllib.request.urlopen(URL, timeout=60).read()
    if base64.b64encode(hashlib.sha512(blob).digest()).decode() != INTEGRITY:
        raise ValueError("Browser runtime integrity mismatch")
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as archive:
        for entry in archive.getmembers():
            if entry.isfile() and (entry.name == "package/dist/ov-web-rtc.umd.cjs"
                                   or entry.name.startswith("package/LICENSE")
                                   or entry.name == "package/package.json"):
                (destination / Path(entry.name).name).write_bytes(archive.extractfile(entry).read())
    print(f"NVIDIA browser runtime: {destination}")


if __name__ == "__main__":
    setup()
