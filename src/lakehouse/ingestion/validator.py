"""Pre-flight validation of a CSV against its declared contract (header + PK presence)."""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

from lakehouse.config import DatasetSpec


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    row_count: int = 0


def validate_csv(path: Path, spec: DatasetSpec) -> ValidationResult:
    expected = [c.name for c in spec.columns]
    errors: list[str] = []
    rows = 0
    with path.open(encoding=spec.encoding, newline="") as fh:
        reader = csv.reader(fh, delimiter=spec.delimiter)
        header = next(reader, None)
        if header is None:
            return ValidationResult(False, ["empty file"])
        header = [h.strip() for h in header]
        if header != expected:
            errors.append(f"header mismatch: expected {expected}, got {header}")
            return ValidationResult(False, errors)
        pk_idx = [header.index(k) for k in spec.primary_key]
        for rows, row in enumerate(reader, start=1):
            if len(row) != len(expected):
                errors.append(f"row {rows}: expected {len(expected)} cols, got {len(row)}")
            elif any(row[i].strip() == "" for i in pk_idx):
                errors.append(f"row {rows}: null primary key {spec.primary_key}")
            if len(errors) > 50:
                errors.append("... truncated")
                break
    return ValidationResult(not errors, errors, rows)
