from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "fin_audit.db"

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'completed',
    company TEXT,
    period TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS uploaded_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id INTEGER NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL,
    mime_type TEXT,
    size_bytes INTEGER NOT NULL,
    sha256 TEXT NOT NULL,
    uploaded_at TEXT NOT NULL,
    notes_json TEXT NOT NULL DEFAULT '[]',
    UNIQUE(review_id)
);

CREATE TABLE IF NOT EXISTS datasets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id INTEGER NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
    sheet_name TEXT NOT NULL DEFAULT '',
    row_count INTEGER NOT NULL,
    column_count INTEGER NOT NULL,
    missing_count INTEGER NOT NULL,
    duplicate_count INTEGER NOT NULL,
    metadata_json TEXT NOT NULL,
    UNIQUE(review_id, sheet_name)
);

CREATE TABLE IF NOT EXISTS dataset_columns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id INTEGER NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    inferred_type TEXT NOT NULL,
    nullable INTEGER NOT NULL,
    null_count INTEGER NOT NULL,
    non_null_count INTEGER NOT NULL,
    unique_count INTEGER NOT NULL,
    unique_ratio REAL NOT NULL,
    stats_json TEXT NOT NULL,
    semantic_candidates_json TEXT NOT NULL DEFAULT '[]',
    UNIQUE(dataset_id, position)
);

CREATE TABLE IF NOT EXISTS financial_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id INTEGER NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    row_number INTEGER NOT NULL,
    values_json TEXT NOT NULL,
    UNIQUE(dataset_id, row_number)
);

CREATE TABLE IF NOT EXISTS analysis_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id INTEGER NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
    run_type TEXT NOT NULL,
    status TEXT NOT NULL,
    result_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_datasets_review ON datasets(review_id);
CREATE INDEX IF NOT EXISTS idx_columns_dataset ON dataset_columns(dataset_id);
CREATE INDEX IF NOT EXISTS idx_records_dataset_row ON financial_records(dataset_id, row_number);
CREATE INDEX IF NOT EXISTS idx_runs_review ON analysis_runs(review_id, created_at);
"""


def connect(path: Path | str | None = None) -> sqlite3.Connection:
    target_path = str(path or DB_PATH)
    # check_same_thread=False prevents async threadpool segmentation faults
    conn = sqlite3.connect(target_path, check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    
    # Use standard rollback journal and normal sync to eliminate mmap/shm crashes on 512MB RAM containers
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = DELETE")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA cache_size = -8000")  # Constrain cache to 8MB
    return conn


def init_db(path: Path | str | None = None) -> None:
    conn = connect(path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


@contextmanager
def transaction(path: Path | str | None = None) -> Iterator[sqlite3.Connection]:
    conn = connect(path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)


def loads(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default

CREATE TABLE IF NOT EXISTS datasets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id INTEGER NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
    sheet_name TEXT NOT NULL DEFAULT '',
    row_count INTEGER NOT NULL,
    column_count INTEGER NOT NULL,
    missing_count INTEGER NOT NULL,
    duplicate_count INTEGER NOT NULL,
    metadata_json TEXT NOT NULL,
    UNIQUE(review_id, sheet_name)
);

CREATE TABLE IF NOT EXISTS dataset_columns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id INTEGER NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    inferred_type TEXT NOT NULL,
    nullable INTEGER NOT NULL,
    null_count INTEGER NOT NULL,
    non_null_count INTEGER NOT NULL,
    unique_count INTEGER NOT NULL,
    unique_ratio REAL NOT NULL,
    stats_json TEXT NOT NULL,
    semantic_candidates_json TEXT NOT NULL DEFAULT '[]',
    UNIQUE(dataset_id, position)
);

CREATE TABLE IF NOT EXISTS financial_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id INTEGER NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    row_number INTEGER NOT NULL,
    values_json TEXT NOT NULL,
    UNIQUE(dataset_id, row_number)
);

CREATE TABLE IF NOT EXISTS analysis_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id INTEGER NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
    run_type TEXT NOT NULL,
    status TEXT NOT NULL,
    result_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_datasets_review ON datasets(review_id);
CREATE INDEX IF NOT EXISTS idx_columns_dataset ON dataset_columns(dataset_id);
CREATE INDEX IF NOT EXISTS idx_records_dataset_row ON financial_records(dataset_id, row_number);
CREATE INDEX IF NOT EXISTS idx_runs_review ON analysis_runs(review_id, created_at);
"""


def connect(path: Path | str | None = None) -> sqlite3.Connection:
    path = path or DB_PATH
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def init_db(path: Path | str | None = None) -> None:
    conn = connect(path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


@contextmanager
def transaction(path: Path | str | None = None) -> Iterator[sqlite3.Connection]:
    conn = connect(path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)


def loads(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default
