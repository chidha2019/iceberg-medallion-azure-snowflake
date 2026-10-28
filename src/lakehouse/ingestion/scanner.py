"""Discover new on-prem CSV files for a dataset (idempotent via checksum ledger)."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from lakehouse.config import DatasetSpec
from lakehouse.logging import get_logger

log = get_logger(__name__)
PROCESSED_DIR = "_processed"


@dataclass(frozen=True)
class SourceFile:
    dataset: str
    path: Path
    sha256: str
    size_bytes: int
    discovered_at: datetime

    @property
    def blob_name(self) -> str:
        """landing/<dataset>/ingest_date=YYYY-MM-DD/<sha-prefix>_<filename>"""
        d = self.discovered_at.strftime("%Y-%m-%d")
        return f"{self.dataset}/ingest_date={d}/{self.sha256[:12]}_{self.path.name}"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def scan(source_root: Path, spec: DatasetSpec) -> list[SourceFile]:
    """Return unprocessed files for ``spec`` under ``source_root/<dataset>/``."""
    folder = source_root / spec.name
    if not folder.exists():
        log.warning("source_folder_missing", dataset=spec.name, folder=str(folder))
        return []
    now = datetime.now(UTC)
    files = [
        SourceFile(spec.name, p, _sha256(p), p.stat().st_size, now)
        for p in sorted(folder.glob(spec.file_pattern))
        if p.is_file() and PROCESSED_DIR not in p.parts
    ]
    log.info("scan_complete", dataset=spec.name, files=len(files))
    return files


def archive(f: SourceFile) -> Path:
    """Move a successfully-uploaded file into ``_processed/`` so re-runs skip it."""
    dest = f.path.parent / PROCESSED_DIR
    dest.mkdir(exist_ok=True)
    target = dest / f.path.name
    f.path.rename(target)
    return target
