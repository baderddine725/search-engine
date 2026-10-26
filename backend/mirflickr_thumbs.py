"""
Serve MIRFLICKR-1M thumbnails directly out of the three published zip
archives, without extracting them to disk.

The archives are shipped by the MIRFLICKR project as:
  thumbs1-33.zip     (directories 1-33  → photo ids ~10_000 … 339_999)
  thumbs34-66.zip    (directories 34-66 → photo ids ~340_000 … 669_999)
  thumbs67-100.zip   (directories 67-100 → photo ids ~670_000 … 999_999)

Each archive stores files named like `thumbnails/<dir>/im<id>.jpg`.
We open each zip once, keep the ZipFile handle around, and seek inside
on each GET. `zipfile.open` returns a file-like object for a single
member — no decompression of unrelated files, no disk extraction.

If the file for a given photo id is missing (zip not downloaded yet, or
photo not in dataset), raise FileNotFoundError so the Flask layer can
return 404 cleanly.
"""

import io
import threading
import zipfile
from pathlib import Path
from typing import Dict, Optional

from config import DATA_DIR

MIR_DIR = Path(DATA_DIR) / "mirflickr"

# (zip filename, inclusive id range)
ARCHIVES = [
    ("thumbs1-33.zip",   (0,       339_999)),
    ("thumbs34-66.zip",  (340_000, 669_999)),
    ("thumbs67-100.zip", (670_000, 999_999)),
]

_zips: Dict[str, zipfile.ZipFile] = {}
_members: Dict[str, Dict[int, str]] = {}
_lock = threading.Lock()


def _open(name: str) -> Optional[zipfile.ZipFile]:
    """Memoised ZipFile open; returns None if the file is missing or still
    being downloaded (invalid zip header)."""
    if name in _zips:
        return _zips[name]
    path = MIR_DIR / name
    if not path.exists():
        return None
    with _lock:
        if name in _zips:
            return _zips[name]
        try:
            z = zipfile.ZipFile(path)
        except (zipfile.BadZipFile, OSError):
            # Partially downloaded. Caller retries on the next request.
            return None
        # Build an id → zip-member map once, so lookups are O(1) later.
        members: Dict[int, str] = {}
        for info in z.infolist():
            fn = info.filename
            if not fn.endswith(".jpg"):
                continue
            base = fn.rsplit("/", 1)[-1]  # imN.jpg
            try:
                pid = int(base[2:-4])
            except ValueError:
                continue
            members[pid] = fn
        _zips[name] = z
        _members[name] = members
        return z


def available() -> dict:
    """Which archives are present + how many thumbnails each exposes."""
    out = {}
    for name, (lo, hi) in ARCHIVES:
        path = MIR_DIR / name
        if not path.exists():
            out[name] = {"present": False, "range": [lo, hi], "members": 0}
            continue
        z = _open(name)
        out[name] = {
            "present": z is not None,
            "downloading": z is None,
            "range": [lo, hi],
            "members": len(_members.get(name, {})),
            "size_mb": round(path.stat().st_size / 2**20, 1),
        }
    return out


def thumb(photo_id: int) -> bytes:
    """
    Return the JPEG bytes for `photo_id`, from whichever archive owns it.
    Raises FileNotFoundError if the archive is missing or the id isn't there.
    """
    for name, (lo, hi) in ARCHIVES:
        if photo_id < lo or photo_id > hi:
            continue
        z = _open(name)
        if z is None:
            raise FileNotFoundError(f"Archive {name} not downloaded yet.")
        member = _members[name].get(photo_id)
        if member is None:
            raise FileNotFoundError(f"im{photo_id}.jpg not in {name}.")
        with z.open(member) as fh:
            return fh.read()
    raise FileNotFoundError(f"photo_id {photo_id} out of range.")
