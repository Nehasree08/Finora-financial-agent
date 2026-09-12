from __future__ import annotations

from typing import Any

from services.dataset_profiler import profile_file
from services.file_reader import read_uploaded_file
from services.repository import create_review, get_dataset, get_review
from utils.errors import AnalysisError


def analyze_upload(filename: str, content: bytes, company: str | None = None, year: str | None = None, mime_type: str | None = None) -> dict[str, Any]:
    loaded = read_uploaded_file(filename, content)
    tables = [(table.sheet_name, table.dataframe) for table in loaded.tables]
    if company:
        scoped_tables = []
        company_key = company.strip().casefold()
        for sheet_name, dataframe in tables:
            entity_column = next((column for column in dataframe.columns if any(hint in str(column).strip().casefold() for hint in ("company", "entity", "business", "organization", "customer", "client"))), None)
            if entity_column is None:
                continue
            mask = dataframe[entity_column].astype(str).str.strip().str.casefold() == company_key
            if mask.any():
                scoped_tables.append((sheet_name, dataframe.loc[mask].reset_index(drop=True)))
        if not scoped_tables:
            raise AnalysisError(f"Company '{company}' was not found in the uploaded dataset.")
        tables = scoped_tables
        loaded.notes.append(f"Analysis scoped to company: {company}.")
    profile = profile_file(tables)
    review_id = create_review(name=f"Review — {filename}", company=company, period=year, filename=loaded.filename, file_type=loaded.file_type, mime_type=mime_type, size_bytes=loaded.size_bytes, sha256=loaded.sha256, notes=loaded.notes, tables=tables)
    return {"success": True, "review_id": review_id, "file": {"filename": loaded.filename, "file_type": loaded.file_type, "size_bytes": loaded.size_bytes, "sha256": loaded.sha256, "notes": loaded.notes}, "profile": profile, "review": get_review(review_id)}
