from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd

NULL_TOKENS = {
    "",
    "nan",
    "none",
    "null",
    "n/a",
    "na",
    "-",
    "--",
    "—",
    "#n/a",
    "#na",
    "nil",
}

CURRENCY_PATTERN = re.compile(r"[\$\£\€\¥\₹]")
PERCENT_PATTERN = re.compile(r"%")
SUFFIX_PATTERN = re.compile(r"^([+-]?(?:\d+(?:\.\d+)?|\.\d+))\s*([kmb]|cr|lakh|lac|l)$", re.I)
INDIAN_GROUPING = re.compile(r"^([+-]?)(\d{1,3})(,\d{2})+$")
WESTERN_GROUPING = re.compile(r"^([+-]?)(\d{1,3})(,\d{3})+(\.\d+)?$")


def parse_financial_value(value: Any) -> Any:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return np.nan
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else np.nan
    if isinstance(value, bool):
        return value

    text = str(value).strip()
    if text.lower() in NULL_TOKENS:
        return np.nan

    original = text
    text = CURRENCY_PATTERN.sub("", text).replace("₹", "").strip()
    accounting_negative = text.startswith("(") and text.endswith(")")
    if accounting_negative:
        text = text[1:-1].strip()

    percent = "%" in text
    text = PERCENT_PATTERN.sub("", text).strip()
    text = text.replace(" ", "")

    multiplier = 1.0
    suffix_match = SUFFIX_PATTERN.match(text)
    if suffix_match:
        text = suffix_match.group(1)
        suffix = suffix_match.group(2).lower()
        multiplier = {
            "k": 1_000,
            "m": 1_000_000,
            "b": 1_000_000_000,
            "l": 100_000,
            "lac": 100_000,
            "lakh": 100_000,
            "cr": 10_000_000,
        }[suffix]

    if INDIAN_GROUPING.match(text) or WESTERN_GROUPING.match(text):
        text = text.replace(",", "")
    elif "," in text and "." in text:
        text = text.replace(",", "")
    elif text.count(",") == 1 and "." not in text:
        left, right = text.split(",")
        if len(right) in (1, 2) and right.isdigit() and left.replace("-", "").isdigit():
            text = f"{left}.{right}"
        else:
            text = text.replace(",", "")
    else:
        text = text.replace(",", "")

    try:
        number = float(text) * multiplier
    except ValueError:
        return original

    if accounting_negative:
        number = -abs(number)
    if percent:
        return number
    if number.is_integer() and multiplier == 1.0:
        return int(number)
    return number


def _should_numericize(series: pd.Series) -> bool:
    if pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series):
        return False
    sample = series.dropna().astype(str).head(200)
    if sample.empty:
        return False
    parsed = sample.map(parse_financial_value)
    numeric = parsed.map(lambda v: isinstance(v, (int, float, np.integer, np.floating)) and not isinstance(v, bool))
    return float(numeric.mean()) >= 0.7


def clean_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    rows_before = int(len(df))
    missing_before = int(df.isna().sum().sum())
    actions: list[str] = []

    cleaned = df.copy()
    original_names = [str(c) for c in df.columns]
    cleaned.columns = [re.sub(r"\s+", " ", str(c)).strip() for c in cleaned.columns]
    cleaned.columns = [
        f"column_{i + 1}" if not str(c) or str(c).lower() in {"nan", "none"} else str(c)
        for i, c in enumerate(cleaned.columns)
    ]
    if list(cleaned.columns) != original_names:
        actions.append("Normalized column names.")

    cleaned = cleaned.replace(r"^\s*$", np.nan, regex=True)

    def _nullify(value):
        if isinstance(value, str) and value.strip().lower() in NULL_TOKENS:
            return np.nan
        return value

    cleaned = cleaned.map(_nullify)

    converted = 0
    for column in cleaned.columns:
        if _should_numericize(cleaned[column]):
            parsed = cleaned[column].map(parse_financial_value)
            numeric = pd.to_numeric(parsed, errors="coerce")
            ratio = float(numeric.notna().mean()) if len(numeric) else 0
            if ratio >= 0.7:
                cleaned[column] = numeric
                converted += 1
    if converted:
        actions.append(f"Converted {converted} column(s) from formatted text into numbers.")

    duplicates_removed = int(cleaned.duplicated().sum())
    if duplicates_removed:
        cleaned = cleaned.drop_duplicates().reset_index(drop=True)
        actions.append(f"Removed {duplicates_removed} duplicate row(s).")

    missing_after = int(cleaned.isna().sum().sum())
    if missing_after:
        actions.append("Left remaining missing values in place rather than inventing replacements.")

    return cleaned, {
        "rows_before": rows_before,
        "rows_after": int(len(cleaned)),
        "duplicates_removed": duplicates_removed,
        "missing_values_before": missing_before,
        "missing_values_after": missing_after,
        "actions": actions,
        "notes": [],
    }
