from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass, field

import pandas as pd

from utils.errors import AnalysisError


MAX_UPLOAD_BYTES = 25 * 1024 * 1024
SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


@dataclass
class LoadedTable:
    sheet_name: str
    dataframe: pd.DataFrame


@dataclass
class LoadedFile:
    filename: str
    file_type: str
    size_bytes: int
    sha256: str
    tables: list[LoadedTable]
    notes: list[str] = field(default_factory=list)

    @property
    def dataframe(self) -> pd.DataFrame:
        return self.tables[0].dataframe


def _extension(filename: str) -> str:
    name = (filename or "").lower().strip()

    if "." not in name:
        return ""

    return "." + name.rsplit(".", 1)[-1]


def _read_csv(content: bytes) -> pd.DataFrame:
    last_error: Exception | None = None

    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return pd.read_csv(
                io.BytesIO(content),
                encoding=encoding,
                engine="python",
            )

        except UnicodeDecodeError as exc:
            last_error = exc

        except pd.errors.EmptyDataError as exc:
            raise AnalysisError("Uploaded CSV is empty.") from exc

        except pd.errors.ParserError as exc:
            last_error = exc

    raise AnalysisError("Could not read the uploaded CSV.") from last_error


def _read_excel(content: bytes, ext: str) -> list[LoadedTable]:
    last_error: Exception | None = None

    engine = "openpyxl" if ext == ".xlsx" else "xlrd"

    try:
        workbook = pd.ExcelFile(
            io.BytesIO(content),
            engine=engine,
        )

        tables: list[LoadedTable] = []

        for sheet in workbook.sheet_names:
            dataframe = pd.read_excel(
                workbook,
                sheet_name=sheet,
            )

            tables.append(
                LoadedTable(
                    sheet_name=str(sheet),
                    dataframe=dataframe,
                )
            )

        return tables

    except Exception as exc:
        last_error = exc

    raise AnalysisError("Could not read the uploaded Excel file.") from last_error


def _usable_dataframe(df: pd.DataFrame) -> bool:
    if df is None:
        return False

    if len(df.columns) == 0:
        return False

    if len(df) == 0:
        return False

    for column in df.columns:
        values = df[column]

        if values.notna().any():
            non_empty = (
                values.astype(str)
                .str.strip()
                .replace("nan", "")
                .ne("")
                .any()
            )

            if non_empty:
                return True

    return False


def read_uploaded_file(filename: str, content: bytes) -> LoadedFile:
    if not filename or not filename.strip():
        raise AnalysisError("A filename is required.")

    if not content:
        raise AnalysisError("Uploaded file is empty.")

    if len(content) > MAX_UPLOAD_BYTES:
        raise AnalysisError(
            "Uploaded file is too large. Maximum size is 25 MB."
        )

    ext = _extension(filename)

    if ext not in SUPPORTED_EXTENSIONS:
        raise AnalysisError(
            "Unsupported file type. Upload a CSV or Excel file."
        )

    notes: list[str] = []

    if ext == ".csv":
        tables = [
            LoadedTable(
                sheet_name="",
                dataframe=_read_csv(content),
            )
        ]

        file_type = "csv"

    else:
        tables = _read_excel(content, ext)
        file_type = ext[1:]

    usable_tables = [
        table
        for table in tables
        if _usable_dataframe(table.dataframe)
    ]

    if not usable_tables:
        raise AnalysisError(
            "No usable rows and columns were found in the uploaded file."
        )

    if len(usable_tables) != len(tables):
        ignored = len(tables) - len(usable_tables)

        notes.append(
            f"Ignored {ignored} empty worksheet(s)."
        )

    return LoadedFile(
        filename=filename,
        file_type=file_type,
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        tables=usable_tables,
        notes=notes,
    )
