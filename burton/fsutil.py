"""Atomic file writes that tolerate Windows' brief file locks (indexer, antivirus)."""

import os
import time
from pathlib import Path


def atomic_write_text(path: Path, text: str, attempts: int = 8) -> None:
    """Write via a temporary file and rename; retry the rename while Windows holds a transient lock."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(text.encode("utf-8"))
    for i in range(attempts):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            if i == attempts - 1:
                raise
            time.sleep(0.1 * (i + 1))
