#!/usr/bin/env python3
"""Reusable IIIF manifest downloader (Presentation API v2 and v3).

Downloads every canvas image of a IIIF manifest, in canvas order, as
p0001.jpg, p0002.jpg, ... into an output directory.

Usage:
  python3 -I download_iiif.py MANIFEST_URL OUT_DIR [--size auto|full|max|W,] [--delay 0.4]
                              [--retries 4] [--start N] [--end N] [--dry-run]

  --size auto   (default) "max" for IIIF Image API 3 services, "full" otherwise
  --size full   request {service}/full/full/0/default.jpg (full resolution, Image API 2)
  --size max    request {service}/full/max/0/default.jpg (IIIF Image API v3 servers)
  --size 400,   request a downscaled image (useful for previews)

Notes:
  * The manifest and the images are treated as untrusted data: nothing is
    executed, file names are generated locally, and every file is checked to
    be a real JPEG/PNG/JP2/TIFF by its magic bytes before being kept.
  * Existing valid files are skipped, so the script can be re-run to resume.
  * Stdlib only; run with `python3 -I` (isolated mode).
"""
import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error

UA = "Mozilla/5.0 (research download; personal scholarly use) python-urllib"

MAGIC = {
    b"\xff\xd8\xff": ".jpg",
    b"\x89PNG\r\n\x1a\n": ".png",
    b"\x00\x00\x00\x0cjP  ": ".jp2",
    b"II*\x00": ".tif",
    b"MM\x00*": ".tif",
}


def sniff(data):
    for sig, ext in MAGIC.items():
        if data.startswith(sig):
            return ext
    return None


def fetch(url, retries, delay, timeout=180):
    last = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            last = e
            wait = delay * (2 ** attempt)
            print(f"   retry {attempt}/{retries} for {url}: {e} (sleep {wait:.1f}s)", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"failed after {retries} tries: {url}: {last}")


def label_str(lbl):
    if lbl is None:
        return ""
    if isinstance(lbl, str):
        return lbl
    if isinstance(lbl, dict):  # v3 language map
        for v in lbl.values():
            return " ".join(v) if isinstance(v, list) else str(v)
    if isinstance(lbl, list):
        return " ".join(label_str(x) for x in lbl)
    return str(lbl)


def svc_is_v3(svc):
    if not svc:
        return False
    t = str(svc.get("type") or svc.get("@type") or "") + str(svc.get("@context") or "")
    return "ImageService3" in t or "image/3" in t


def canvases(manifest):
    """Yield (label, service_id_or_None, direct_image_url, is_v3) per canvas, in order."""
    if "sequences" in manifest:  # IIIF v2
        for c in manifest["sequences"][0].get("canvases", []):
            img = c["images"][0]["resource"]
            svc = img.get("service")
            if isinstance(svc, list):
                svc = svc[0] if svc else None
            sid = (svc or {}).get("@id") or (svc or {}).get("id")
            yield label_str(c.get("label")), sid, img.get("@id") or img.get("id"), svc_is_v3(svc)
    else:  # IIIF v3
        for c in manifest.get("items", []):
            body = c["items"][0]["items"][0]["body"]
            if isinstance(body, list):
                body = body[0]
            svc = body.get("service")
            if isinstance(svc, list):
                svc = svc[0] if svc else None
            sid = (svc or {}).get("@id") or (svc or {}).get("id")
            yield label_str(c.get("label")), sid, body.get("id"), svc_is_v3(svc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("outdir")
    ap.add_argument("--size", default="auto")
    ap.add_argument("--delay", type=float, default=0.4)
    ap.add_argument("--retries", type=int, default=4)
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--end", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if a.manifest.startswith("http"):
        manifest = json.loads(fetch(a.manifest, a.retries, a.delay).decode("utf-8"))
    else:
        with open(a.manifest, encoding="utf-8") as f:
            manifest = json.load(f)

    items = list(canvases(manifest))
    print(f"{label_str(manifest.get('label'))}: {len(items)} canvases")
    os.makedirs(a.outdir, exist_ok=True)
    ok = fail = skip = 0
    for i, (lbl, sid, direct, v3) in enumerate(items, 1):
        if i < a.start or (a.end and i > a.end):
            continue
        if sid:
            size = a.size if a.size != "auto" else ("max" if v3 else "full")
            url = f"{sid.rstrip('/')}/full/{size}/0/default.jpg"
        else:
            url = direct
        dest = os.path.join(a.outdir, f"p{i:04d}.jpg")
        if os.path.exists(dest):
            with open(dest, "rb") as f:
                if sniff(f.read(16)):
                    skip += 1
                    continue
        if a.dry_run:
            print(f"{i:4d} [{lbl}] {url}")
            continue
        try:
            data = fetch(url, a.retries, a.delay)
            ext = sniff(data[:16])
            if not ext:
                raise RuntimeError(f"not an image ({data[:40]!r})")
            if ext != ".jpg":
                dest = dest[:-4] + ext
            tmp = dest + ".part"
            with open(tmp, "wb") as f:
                f.write(data)
            os.replace(tmp, dest)
            ok += 1
            print(f"{i:4d} [{lbl}] {len(data)//1024} KB -> {os.path.basename(dest)}")
        except Exception as e:  # noqa: BLE001
            fail += 1
            print(f"{i:4d} [{lbl}] FAILED: {e}", file=sys.stderr)
        time.sleep(a.delay)
    print(f"done: {ok} downloaded, {skip} already present, {fail} failed")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
