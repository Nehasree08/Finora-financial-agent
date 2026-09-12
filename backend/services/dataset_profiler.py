from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd

from utils.data_cleaner import parse_financial_value
from utils.serializers import json_safe, round_number

DATE_HINTS = ("date", "time", "period", "month", "quarter", "year", "fy", "fiscal")
ID_HINTS = ("id", "code", "number", "no", "ref", "reference", "account", "invoice", "transaction")
COMPANY_HINTS = ("company", "entity", "business", "subsidiary", "customer", "client", "vendor", "organization", "organisation")

CONCEPT_ALIASES = {
    "revenue": ("revenue", "sales", "net sales", "turnover", "income from operations", "total income"),
    "expenses": ("expenses", "expense", "operating expenses", "total expenses", "costs"),
    "profit": ("profit", "net income", "net profit", "earnings", "pbt", "pat", "profit after tax"),
    "assets": ("assets", "total assets"),
    "liabilities": ("liabilities", "total liabilities"),
    "debt": ("debt", "borrowings", "loans", "total debt"),
    "equity": ("equity", "shareholders equity", "owners equity", "net worth"),
    "cash": ("cash", "cash and cash equivalents", "bank balance"),
    "receivables": ("receivables", "accounts receivable", "trade receivables", "debtors"),
    "inventory": ("inventory", "inventories", "stock"),
    "payables": ("payables", "accounts payable", "trade payables", "creditors"),
    "tax": ("tax", "income tax", "tax expense"),
    "interest": ("interest", "interest expense", "finance cost"),
    "cogs": ("cogs", "cost of goods sold", "cost of sales"),
    "depreciation": ("depreciation",),
    "amortization": ("amortization", "amortisation"),
    "capex": ("capex", "capital expenditure", "purchase of property plant equipment"),
}


def normalize_name(name: Any) -> str:
    text = re.sub(r"[^a-z0-9]+", " ", str(name).strip().lower())
    return re.sub(r"\s+", " ", text).strip()


def _is_date_like(series: pd.Series, name: str) -> bool:
    if any(h in normalize_name(name).split() for h in DATE_HINTS):
        return True
    if pd.api.types.is_datetime64_any_dtype(series):
        return True
    sample = series.dropna().astype(str).head(100)
    if sample.empty:
        return False
    parsed = pd.to_datetime(sample, errors="coerce", dayfirst=False, format="mixed")
    return float(parsed.notna().mean()) >= 0.8


def _infer_type(series: pd.Series, name: str) -> str:
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    if _is_date_like(series, name):
        return "date"
    parsed = series.dropna().map(parse_financial_value)
    if not parsed.empty:
        numeric_ratio = float(parsed.map(lambda x: isinstance(x, (int, float, np.integer, np.floating)) and not isinstance(x, bool)).mean())
        if numeric_ratio >= 0.9:
            return "numeric"
    return "categorical"


def _numeric_stats(series: pd.Series) -> dict[str, Any]:
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.notna().sum() == 0:
        return {}
    q = numeric.dropna()
    return json_safe({
        "count": int(q.count()),
        "mean": round_number(q.mean()),
        "std": round_number(q.std()),
        "min": round_number(q.min()),
        "q1": round_number(q.quantile(0.25)),
        "median": round_number(q.median()),
        "q3": round_number(q.quantile(0.75)),
        "max": round_number(q.max()),
        "sum": round_number(q.sum()),
    })


def _date_stats(series: pd.Series) -> dict[str, Any]:
    parsed = pd.to_datetime(series, errors="coerce")
    parsed = parsed.dropna()
    if parsed.empty:
        return {}
    return {"min": parsed.min().isoformat(), "max": parsed.max().isoformat(), "count": int(len(parsed))}


def _top_values(series: pd.Series, limit: int = 10) -> list[dict[str, Any]]:
    counts = series.dropna().astype(str).str.strip().value_counts().head(limit)
    return [{"value": str(v), "count": int(c)} for v, c in counts.items()]


def _semantic_candidates(name: str, series: pd.Series) -> list[dict[str, Any]]:
    norm = normalize_name(name)
    inferred = _infer_type(series, name)
    candidates: list[dict[str, Any]] = []
    for concept, aliases in CONCEPT_ALIASES.items():
        score = 0.0
        matched = None
        for alias in aliases:
            a = normalize_name(alias)
            if norm == a:
                score = 1.0
                matched = alias
                break
            if a in norm or norm in a:
                score = max(score, 0.85)
                matched = alias
        if score and inferred not in {"numeric"}:
            score *= 0.35
        if score >= 0.7:
            candidates.append({"concept": concept, "confidence": round(score, 2), "matched_alias": matched})
    return sorted(candidates, key=lambda x: x["confidence"], reverse=True)


def _dimension_candidates(df: pd.DataFrame) -> list[dict[str, Any]]:
    dimensions: list[dict[str, Any]] = []
    for position, original in enumerate(df.columns):
        name = str(original)
        norm = normalize_name(name)
        series = df[original]
        non_null = int(series.notna().sum())
        unique = int(series.nunique(dropna=True))
        if non_null == 0 or unique == 0:
            continue
        ratio = unique / non_null
        looks_like_dimension = (
            any(h in norm.split() for h in COMPANY_HINTS)
            or (series.dtype == object and 1 < unique <= min(100, max(2, int(non_null * 0.5))))
        )
        if looks_like_dimension:
            dimensions.append({
                "position": position,
                "name": name,
                "unique_count": unique,
                "sample_values": json_safe(series.dropna().astype(str).drop_duplicates().head(20).tolist()),
                "role": "entity" if any(h in norm.split() for h in COMPANY_HINTS) else "categorical_dimension",
                "confidence": 0.95 if any(h in norm.split() for h in COMPANY_HINTS) else 0.7,
            })
    return dimensions


def profile_table(df: pd.DataFrame, sheet_name: str = "") -> dict[str, Any]:
    columns: list[dict[str, Any]] = []
    normalized_names: list[str] = []
    for position, original in enumerate(df.columns):
        name = str(original)
        normalized = normalize_name(name)
        normalized_names.append(normalized)
        series = df[original]
        null_count = int(series.isna().sum())
        non_null = int(series.notna().sum())
        unique_count = int(series.nunique(dropna=True))
        inferred = _infer_type(series, name)
        stats: dict[str, Any] = {
            "sample_values": json_safe(series.dropna().head(5).tolist()),
        }
        if inferred == "numeric":
            stats.update(_numeric_stats(series))
        elif inferred == "date":
            stats.update(_date_stats(series))
        else:
            stats["top_values"] = _top_values(series)
        columns.append({
            "position": position,
            "name": name,
            "normalized_name": normalized,
            "inferred_type": inferred,
            "nullable": null_count > 0,
            "null_count": null_count,
            "non_null_count": non_null,
            "unique_count": unique_count,
            "unique_ratio": round(unique_count / non_null, 6) if non_null else 0.0,
            "stats": stats,
            "semantic_candidates": _semantic_candidates(name, series),
        })

    duplicate_count = int(df.duplicated().sum())
    return {
        "sheet_name": sheet_name,
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "column_names": [str(c) for c in df.columns],
        "missing_values": int(df.isna().sum().sum()),
        "duplicate_rows": duplicate_count,
        "columns_profile": columns,
        "preview": json_safe(df.head(50).where(pd.notna(df.head(50)), None).to_dict(orient="records")),
        "dimension_candidates": _dimension_candidates(df),
    }


def profile_file(tables: list[tuple[str, pd.DataFrame]]) -> dict[str, Any]:
    profiles = [profile_table(df, sheet) for sheet, df in tables]
    entities: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for profile in profiles:
        for dim in profile.get("dimension_candidates", []):
            if dim["role"] != "entity":
                continue
            key = (profile["sheet_name"], dim["name"])
            if key in seen:
                continue
            seen.add(key)
            entities.append({"sheet_name": profile["sheet_name"], **dim})
    return {
        "table_count": len(profiles),
        "total_rows": sum(p["rows"] for p in profiles),
        "total_columns": sum(p["columns"] for p in profiles),
        "total_missing_values": sum(p["missing_values"] for p in profiles),
        "total_duplicate_rows": sum(p["duplicate_rows"] for p in profiles),
        "tables": profiles,
        "entity_candidates": entities,
        "concept_candidates": sorted({c["concept"] for p in profiles for col in p["columns_profile"] for c in col["semantic_candidates"]}),
    }
