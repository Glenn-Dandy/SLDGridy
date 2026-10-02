"""Reading and writing drawing files."""

import json
import os
import shutil
import tempfile
from pathlib import Path

from sldgridy.fileio.json_format import FileFormatError, document_from_dict, document_to_dict
from sldgridy.model.document import Document

DRAWING_SUFFIX = ".sldg"


def write_json_atomic(path: Path, data: dict) -> None:
    """Write ``data`` to ``path`` via a temporary file; keep the previous file as ``.bak``."""
    path = Path(path)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        if path.exists():
            shutil.copy2(path, path.with_name(path.name + ".bak"))
        os.replace(tmp_name, path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise


def save_document(doc: Document, path: Path) -> None:
    write_json_atomic(Path(path), document_to_dict(doc))


def load_document(path: Path) -> Document:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise FileFormatError(f"not a valid JSON file: {exc}") from exc
    if not isinstance(data, dict):
        raise FileFormatError("not a drawing file")
    return document_from_dict(data)
