"""Strict JSON, content identities, and crash-safe local records."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time

SOURCE_ID = "885ca45b75faa092d5e9116faeed2c2df9a7aaad089204522647a443e2bcfb41"
METRIC_ID = "3681ca11258da031fe473ea335f7df20f1a386b12d5cf49dc6dd7100cca6531c"

def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()

def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result

def read(path):
    return json.loads(Path(path).read_text(), object_pairs_hook=_unique,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))

def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as f:
        temp = Path(f.name)
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)

def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def within(root, relative):
    p = Path(relative)
    root = Path(root).resolve()
    if p.is_absolute() or ".." in p.parts:
        raise ValueError("relative nonescaping artifact path required")
    result = (root / p).resolve()
    if not result.is_relative_to(root):
        raise ValueError("artifact symlink escapes bundle")
    return result

