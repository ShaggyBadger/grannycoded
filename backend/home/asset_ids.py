"""ULID helpers for image object names."""

from pathlib import PurePosixPath
import re

from ulid import monotonic


ULID_PATTERN = re.compile(r"[0-9A-HJKMNP-TV-Z]{26}")


def new_ulid() -> str:
    """Return a time-sortable, monotonic ULID string."""
    return str(monotonic.new())


def ulid_filename(name: str) -> str:
    """Use ULIDs for uploads while preserving ULID-prefixed rendition names."""
    path = PurePosixPath(name)
    stem = path.stem
    has_ulid_name = ULID_PATTERN.fullmatch(stem)
    has_ulid_rendition_name = (
        len(stem) > 27
        and stem[26] == "."
        and ULID_PATTERN.fullmatch(stem[:26])
    )
    if has_ulid_name or has_ulid_rendition_name:
        return name
    suffix = path.suffix.lower()
    return str(path.with_name(f"{new_ulid()}{suffix}"))
