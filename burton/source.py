"""`burton unpack`: copy the EPUB into data/source, pin its hash, unzip to work/."""

import hashlib
import shutil
import zipfile
from pathlib import Path

from . import paths


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_lock() -> dict[str, str]:
    if not paths.SOURCE_LOCK.exists():
        return {}
    out = {}
    for line in paths.SOURCE_LOCK.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            digest, name = line.split(maxsplit=1)
            out[name] = digest
    return out


def check_lock() -> None:
    """Stop everything if the working EPUB is not the pinned one."""
    lock = read_lock()
    name = paths.EPUB_COPY.name
    if name not in lock:
        raise SystemExit("No SOURCE.lock entry: run `burton unpack` first.")
    if not paths.EPUB_COPY.exists():
        raise SystemExit(f"{paths.EPUB_COPY} is missing: run `burton unpack`.")
    actual = sha256(paths.EPUB_COPY)
    if actual != lock[name]:
        raise SystemExit(f"EPUB hash mismatch: locked {lock[name]}, found {actual}. Refusing to continue.")


def unpack(epub: Path) -> None:
    paths.SOURCE.mkdir(parents=True, exist_ok=True)
    digest = sha256(epub)
    lock = read_lock()
    name = paths.EPUB_COPY.name
    if name in lock and lock[name] != digest:
        raise SystemExit(
            f"{epub} has hash {digest}, but SOURCE.lock pins {lock[name]}. "
            "Delete the lock entry deliberately if the source is meant to change."
        )
    if not paths.EPUB_COPY.exists() or sha256(paths.EPUB_COPY) != digest:
        shutil.copyfile(epub, paths.EPUB_COPY)
    if name not in lock:
        with paths.SOURCE_LOCK.open("a", encoding="utf-8") as f:
            if not lock:
                f.write("# sha256  file   (do not edit by hand)\n")
            f.write(f"{digest}  {name}\n")
    if paths.EPUB_DIR.exists():
        shutil.rmtree(paths.EPUB_DIR)
    paths.EPUB_DIR.mkdir(parents=True)
    with zipfile.ZipFile(paths.EPUB_COPY) as z:
        for info in z.infolist():
            target = (paths.EPUB_DIR / info.filename).resolve()
            if not str(target).startswith(str(paths.EPUB_DIR.resolve())):
                raise SystemExit(f"Refusing unsafe zip member {info.filename!r}")
        z.extractall(paths.EPUB_DIR)
    print(f"EPUB pinned: sha256 {digest}")
    print(f"Unzipped {len(z.infolist())} members to {paths.EPUB_DIR.relative_to(paths.ROOT)}")
