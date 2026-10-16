"""Local filesystem storage for uploaded files.

File bytes stay outside PostgreSQL; documents.storage_key holds the
relative key. Swap this class for an object-store implementation later.
"""

import os
from functools import lru_cache
from pathlib import Path

from neuralshelf.core.config import get_settings


class LocalFileStorage:
    """Uploaded files on the local disk, under one root directory."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def path_for(self, key: str) -> Path:
        """Absolute path for ``key``.

        Raises:
            ValueError: The key would escape the storage root (e.g. ``../``).
        """
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("Storage key escapes the storage root.")
        return path

    def save(self, key: str, data: bytes) -> None:
        """Write ``data`` atomically: to a temporary file, then rename."""
        path = self.path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_name(f".{path.name}.tmp")
        temp_path.write_bytes(data)
        os.replace(temp_path, path)

    def delete(self, key: str) -> None:
        """Delete the file for ``key``; a missing file is not an error."""
        self.path_for(key).unlink(missing_ok=True)


@lru_cache
def get_file_storage() -> LocalFileStorage:
    """The configured storage (cached; also used as a FastAPI dependency)."""
    return LocalFileStorage(get_settings().upload_dir)
