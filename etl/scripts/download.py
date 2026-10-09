"""python download.py <url> <destination>"""
import sys
from pathlib import Path

import httpx

url, dest = sys.argv[1], Path(sys.argv[2])
dest.parent.mkdir(parents=True, exist_ok=True)
with httpx.stream("GET", url, follow_redirects=True, timeout=None) as r, dest.open("wb") as f:
    r.raise_for_status()
    for chunk in r.iter_bytes():
        f.write(chunk)
print("OK", dest, dest.stat().st_size)
