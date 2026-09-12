from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd

from db import dumps, loads, transaction, init_db
from services.dataset_profiler import profile_table
from utils.serializers import json_safe


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_review(*, name: str, company: str | None, period: str | None, filename: str, file_type: str, mime_type: str | None, size_bytes: int, sha256: str, notes: list[str], tables: list[tuple[str, pd.DataFrame]]) -> int:
    init_db()
    created = now()
    with transaction() as conn:
        cur = conn.execute("INSERT INTO reviews(name, status, company, period, created_at, updated_at) VALUES(?,?,?,?,?,?)", (name, "completed", company, period, created, created))
        review_id = int(cur.lastrowid)
        conn.execute("INSERT INTO uploaded_files(review_id, filename, file_type, mime_type, size_bytes, sha256, uploaded_at, notes_json) VALUES(?,?,?,?,?,?,?,?)", (review_id, filename, file_type, mime_type, size_bytes, sha256, created, dumps(notes)))
        for sheet_name, df in tables:
            profile = profile_table(df, sheet_name)
            cur = conn.execute("INSERT INTO datasets(review_id, sheet_name, row_count, column_count, missing_count, duplicate_count, metadata_json) VALUES(?,?,?,?,?,?,?)", (review_id, sheet_name, profile["rows"], profile["columns"], profile["missing_values"], profile["duplicate_rows"], dumps(profile)))
            dataset_id = int(cur.lastrowid)
            for col in profile["columns_profile"]:
                conn.execute("INSERT INTO dataset_columns(dataset_id, position, name, normalized_name, inferred_type, nullable, null_count, non_null_count, unique_count, unique_ratio, stats_json, semantic_candidates_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (dataset_id, col["position"], col["name"], col["normalized_name"], col["inferred_type"], int(col["nullable"]), col["null_count"], col["non_null_count"], col["unique_count"], col["unique_ratio"], dumps(col["stats"]), dumps(col["semantic_candidates"])))
            for row_number, record in enumerate(df.to_dict(orient="records"), start=1):
                conn.execute("INSERT INTO financial_records(dataset_id, row_number, values_json) VALUES(?,?,?)", (dataset_id, row_number, dumps(json_safe(record))))
        result = {"table_count": len(tables), "total_rows": sum(len(df) for _, df in tables)}
        conn.execute("INSERT INTO analysis_runs(review_id, run_type, status, result_json, created_at) VALUES(?,?,?,?,?)", (review_id, "ingestion", "completed", dumps(result), created))
    return review_id


def list_reviews() -> list[dict[str, Any]]:
    init_db()
    with transaction() as conn:
        rows = conn.execute("SELECT * FROM reviews ORDER BY id DESC").fetchall()
        out = []
        for row in rows:
            item = dict(row)
            item["uploaded_file"] = dict(conn.execute("SELECT filename, file_type, size_bytes, sha256 FROM uploaded_files WHERE review_id=?", (row["id"],)).fetchone() or {})
            item["datasets"] = [dict(r) for r in conn.execute("SELECT id, sheet_name, row_count, column_count, missing_count, duplicate_count FROM datasets WHERE review_id=? ORDER BY id", (row["id"],)).fetchall()]
            out.append(item)
        return out


def get_review(review_id: int) -> dict[str, Any] | None:
    init_db()
    with transaction() as conn:
        row = conn.execute("SELECT * FROM reviews WHERE id=?", (review_id,)).fetchone()
        if not row:
            return None
        item = dict(row)
        f = conn.execute("SELECT * FROM uploaded_files WHERE review_id=?", (review_id,)).fetchone()
        item["uploaded_file"] = dict(f) if f else None
        item["datasets"] = []
        for d in conn.execute("SELECT * FROM datasets WHERE review_id=? ORDER BY id", (review_id,)).fetchall():
            ds = dict(d)
            ds["metadata"] = loads(ds.pop("metadata_json"), {})
            item["datasets"].append(ds)
        return item


def get_columns(review_id: int) -> list[dict[str, Any]]:
    init_db()
    with transaction() as conn:
        rows = conn.execute("SELECT dc.*, d.sheet_name FROM dataset_columns dc JOIN datasets d ON d.id=dc.dataset_id WHERE d.review_id=? ORDER BY d.id, dc.position", (review_id,)).fetchall()
        out = []
        for r in rows:
            x = dict(r)
            x["nullable"] = bool(x["nullable"])
            x["stats"] = loads(x.pop("stats_json"), {})
            x["semantic_candidates"] = loads(x.pop("semantic_candidates_json"), [])
            out.append(x)
        return out


def get_records(review_id: int, offset: int, limit: int) -> tuple[int, list[dict[str, Any]]]:
    init_db()
    with transaction() as conn:
        total = conn.execute("SELECT COUNT(*) FROM financial_records fr JOIN datasets d ON d.id=fr.dataset_id WHERE d.review_id=?", (review_id,)).fetchone()[0]
        rows = conn.execute("SELECT fr.row_number, fr.values_json, d.sheet_name FROM financial_records fr JOIN datasets d ON d.id=fr.dataset_id WHERE d.review_id=? ORDER BY d.id, fr.row_number LIMIT ? OFFSET ?", (review_id, limit, offset)).fetchall()
        return int(total), [{"sheet_name": r["sheet_name"], "row_number": r["row_number"], "values": json_safe(loads(r["values_json"], {}))} for r in rows]


def _review_records(review_id: int) -> list[dict[str, Any]]:
    return get_records(review_id, 0, 1_000_000)[1]


def get_comparison_options(review_id: int) -> dict[str, Any] | None:
    if get_review(review_id) is None:
        return None
    records = _review_records(review_id)
    values_by_column: dict[str, list[Any]] = {}
    for record in records:
        for name, value in record["values"].items():
            if value is not None and value != "":
                values_by_column.setdefault(str(name), []).append(value)

    entity_columns = []
    metric_columns = []
    for name, values in values_by_column.items():
        unique_values = list(dict.fromkeys(str(value) for value in values))
        numeric_values = [value for value in values if isinstance(value, (int, float)) and not isinstance(value, bool)]
        if len(unique_values) > 1 and len(unique_values) <= 200 and len(numeric_values) < len(values):
            entity_columns.append({"name": name, "entities": unique_values})
        if numeric_values:
            metric_columns.append(name)
    return {"entity_columns": entity_columns, "metric_columns": metric_columns}


def compare_within_review(review_id: int, entity_column: str, metric: str, left: str, right: str) -> dict[str, Any] | None:
    options = get_comparison_options(review_id)
    if options is None:
        return None
    if entity_column not in {item["name"] for item in options["entity_columns"]}:
        raise ValueError("Choose a valid entity column.")
    if metric != "__all__" and metric not in options["metric_columns"]:
        raise ValueError("Choose a valid numeric metric.")

    records = _review_records(review_id)
    def summarize(name: str, metric_name: str) -> dict[str, Any]:
        numbers = [float(record["values"][metric_name]) for record in records if str(record["values"].get(entity_column, "")) == name and isinstance(record["values"].get(metric_name), (int, float)) and not isinstance(record["values"].get(metric_name), bool)]
        total = sum(numbers) if numbers else None
        return {"entity": name, "count": len(numbers), "sum": total, "average": total / len(numbers) if numbers else None, "min": min(numbers) if numbers else None, "max": max(numbers) if numbers else None}

    if metric == "__all__":
        metrics = [{"metric": name, "left": summarize(left, name), "right": summarize(right, name)} for name in options["metric_columns"]]
        return {"review_id": review_id, "entity_column": entity_column, "metric": "All metrics", "left": {"entity": left}, "right": {"entity": right}, "metrics": metrics}

    left_summary, right_summary = summarize(left, metric), summarize(right, metric)
    left_total, right_total = left_summary["sum"], right_summary["sum"]
    return {"review_id": review_id, "entity_column": entity_column, "metric": metric, "left": left_summary, "right": right_summary, "difference": right_total - left_total if left_total is not None and right_total is not None else None}


def get_audit_analysis(review_id: int) -> dict[str, Any] | None:
    review = get_review(review_id)
    if review is None:
        return None
    columns = get_columns(review_id)
    records = _review_records(review_id)
    numeric_columns = [column for column in columns if column["inferred_type"] == "numeric"]
    validation = {
        "missing_values": sum(column["null_count"] for column in columns),
        "duplicate_rows": sum(dataset["duplicate_count"] for dataset in review["datasets"]),
        "nullable_fields": [column["name"] for column in columns if column["nullable"]],
        "empty_fields": [column["name"] for column in columns if column["non_null_count"] == 0],
    }

    def find_column(*hints: str) -> str | None:
        return next((column["name"] for column in numeric_columns if any(hint in column["name"].lower() for hint in hints)), None)

    math_checks: list[dict[str, Any]] = []
    revenue_col = find_column("revenue", "sales")
    expense_col = find_column("expense", "cost")
    profit_col = find_column("net income", "net profit", "profit")
    assets_col = find_column("assets")
    liabilities_col = find_column("liabilities")
    equity_col = find_column("equity")

    def check_formula(name: str, expected: str, actual: str, tolerance: float = 0.01):
        checked = matches = 0
        examples = []
        for record in records:
            values = record["values"]
            expected_value = values.get(expected)
            actual_value = values.get(actual)
            if isinstance(expected_value, (int, float)) and isinstance(actual_value, (int, float)):
                checked += 1
                difference = float(expected_value) - float(actual_value)
                scale = max(abs(float(expected_value)), abs(float(actual_value)), 1)
                if abs(difference) <= scale * tolerance:
                    matches += 1
                elif len(examples) < 3:
                    examples.append({"row": record["row_number"], "expected": expected_value, "actual": actual_value, "difference": difference})
        if checked:
            math_checks.append({"check": name, "status": "pass" if matches == checked else "review", "checked_rows": checked, "matching_rows": matches, "evidence": examples})

    if revenue_col and expense_col and profit_col:
        checked = matches = 0
        examples = []
        for record in records:
            values = record["values"]
            if all(isinstance(values.get(column), (int, float)) for column in (revenue_col, expense_col, profit_col)):
                checked += 1
                expected = float(values[revenue_col]) - float(values[expense_col])
                actual = float(values[profit_col])
                if abs(expected - actual) <= max(abs(expected), abs(actual), 1) * 0.01:
                    matches += 1
                elif len(examples) < 3:
                    examples.append({"row": record["row_number"], "expected": expected, "actual": actual, "difference": expected - actual})
        math_checks.append({"check": "Revenue - expenses = profit", "status": "pass" if matches == checked else "review", "checked_rows": checked, "matching_rows": matches, "evidence": examples})
    if assets_col and liabilities_col and equity_col:
        math_checks.append({"check": "Assets = liabilities + equity", "status": "review", "checked_rows": 0, "matching_rows": 0, "evidence": []})
        for record in records:
            values = record["values"]
            if all(isinstance(values.get(column), (int, float)) for column in (assets_col, liabilities_col, equity_col)):
                expected = float(values[liabilities_col]) + float(values[equity_col])
                actual = float(values[assets_col])
                math_checks[-1]["checked_rows"] += 1
                if abs(expected - actual) <= max(abs(expected), abs(actual), 1) * 0.01:
                    math_checks[-1]["matching_rows"] += 1
                elif len(math_checks[-1]["evidence"]) < 3:
                    math_checks[-1]["evidence"].append({"row": record["row_number"], "expected": expected, "actual": actual, "difference": expected - actual})
        math_checks[-1]["status"] = "pass" if math_checks[-1]["matching_rows"] == math_checks[-1]["checked_rows"] else "review"

    year_column = next((column["name"] for column in columns if "year" in column["name"].lower() or column["name"].lower() in {"date", "period"}), None)
    year_over_year: list[dict[str, Any]] = []
    if year_column:
        years = sorted({str(record["values"].get(year_column)) for record in records if record["values"].get(year_column) is not None})
        if len(years) >= 2:
            previous, current = years[-2], years[-1]
            for column in numeric_columns[:8]:
                previous_total = sum(float(record["values"][column["name"]]) for record in records if str(record["values"].get(year_column)) == previous and isinstance(record["values"].get(column["name"]), (int, float)))
                current_total = sum(float(record["values"][column["name"]]) for record in records if str(record["values"].get(year_column)) == current and isinstance(record["values"].get(column["name"]), (int, float)))
                if previous_total or current_total:
                    year_over_year.append({"metric": column["name"], "previous_year": previous, "current_year": current, "previous_value": previous_total, "current_value": current_total, "change": current_total - previous_total, "change_percent": ((current_total - previous_total) / abs(previous_total) * 100) if previous_total else None})

    internal_consistency = [{"check": item["check"], "status": item["status"], "evidence": item["evidence"]} for item in math_checks]

    options = get_comparison_options(review_id) or {"entity_columns": [], "metric_columns": []}
    entity = options["entity_columns"][0] if options["entity_columns"] else None
    variance: list[dict[str, Any]] = []
    if entity and numeric_columns:
        entity_name = entity["name"]
        for metric in numeric_columns[:8]:
            groups: dict[str, list[float]] = {}
            for record in records:
                values = record["values"]
                group = str(values.get(entity_name, ""))
                value = values.get(metric["name"])
                if group and isinstance(value, (int, float)) and not isinstance(value, bool):
                    groups.setdefault(group, []).append(float(value))
            ranked = sorted(((name, sum(values)) for name, values in groups.items()), key=lambda item: abs(item[1]), reverse=True)
            if len(ranked) >= 2:
                variance.append({"metric": metric["name"], "entity_column": entity_name, "highest": {"entity": ranked[0][0], "value": ranked[0][1]}, "lowest": {"entity": ranked[-1][0], "value": ranked[-1][1]}, "difference": ranked[0][1] - ranked[-1][1]})

    sums = {column["name"]: column["stats"].get("sum") for column in numeric_columns}
    ratio_pairs = (("profit", "revenue", "profit_margin"), ("net income", "revenue", "net_margin"), ("cash", "assets", "cash_to_assets"), ("debt", "equity", "debt_to_equity"))
    ratios = []
    for numerator_hint, denominator_hint, name in ratio_pairs:
        numerator = next((value for column, value in sums.items() if numerator_hint in column.lower() and isinstance(value, (int, float))), None)
        denominator = next((value for column, value in sums.items() if denominator_hint in column.lower() and isinstance(value, (int, float)) and value), None)
        if numerator is not None and denominator is not None:
            ratios.append({"name": name, "numerator": numerator, "denominator": denominator, "value": numerator / denominator})

    anomalies = []
    for column in numeric_columns[:12]:
        values = [record["values"].get(column["name"]) for record in records]
        numbers = [float(value) for value in values if isinstance(value, (int, float)) and not isinstance(value, bool)]
        if len(numbers) < 4:
            continue
        mean = sum(numbers) / len(numbers)
        deviation = (sum((value - mean) ** 2 for value in numbers) / len(numbers)) ** 0.5
        if deviation:
            outliers = [value for value in numbers if abs(value - mean) > deviation * 3]
            if outliers:
                anomalies.append({"field": column["name"], "count": len(outliers), "max_abs_z": max(abs(value - mean) / deviation for value in outliers), "examples": outliers[:5]})

    review_comments = []
    for check in math_checks:
        if check["status"] == "review":
            review_comments.append(f"{check['check']} needs review: {check['checked_rows'] - check['matching_rows']} row(s) do not reconcile. Evidence: {check['evidence'][:1]}.")
    for item in year_over_year:
        if item["change_percent"] is not None and abs(item["change_percent"]) >= 20:
            review_comments.append(f"{item['metric']} changed {item['change_percent']:.1f}% from {item['previous_year']} to {item['current_year']}; investigate the supporting movement.")
    if not review_comments:
        review_comments.append("No material formula or year-over-year review comments were generated from the available fields.")

    ai_review = [f"The review contains {len(records):,} persisted source rows across {len(review['datasets'])} table(s)."]
    ai_review.append(f"Validation found {validation['missing_values']:,} missing values and {validation['duplicate_rows']:,} duplicate rows.")
    if variance:
        ai_review.append(f"Variance is available across {len(variance)} numeric metric and entity combinations.")
    if ratios:
        ai_review.append(f"{len(ratios)} grounded financial ratio(s) were calculated from discovered fields.")
    if anomalies:
        ai_review.append(f"{len(anomalies)} field(s) contain values beyond a 3-sigma review threshold.")
    else:
        ai_review.append("No 3-sigma numeric anomalies were detected in the profiled records.")
    return {"review": {"id": review_id, "name": review["name"]}, "validation": validation, "math_checks": math_checks, "internal_consistency": internal_consistency, "year_over_year": year_over_year, "variance": variance, "ratios": ratios, "anomalies": anomalies, "review_comments": review_comments, "ai_review": ai_review}


def get_dataset(review_id: int) -> dict[str, Any] | None:
    review = get_review(review_id)
    if review is None:
        return None
    return {"review_id": review_id, "tables": [d["metadata"] for d in review["datasets"]], "summary": {"table_count": len(review["datasets"]), "total_rows": sum(d["row_count"] for d in review["datasets"]), "total_columns": sum(d["column_count"] for d in review["datasets"]), "total_missing_values": sum(d["missing_count"] for d in review["datasets"]), "total_duplicate_rows": sum(d["duplicate_count"] for d in review["datasets"])}}


def delete_review(review_id: int) -> bool:
    init_db()
    with transaction() as conn:
        cur = conn.execute("DELETE FROM reviews WHERE id=?", (review_id,))
        return cur.rowcount > 0


def compare_reviews(left_review_id: int, right_review_id: int) -> dict[str, Any] | None:
    """Compare two persisted reviews without inventing a shared schema."""
    left = get_review(left_review_id)
    right = get_review(right_review_id)
    if not left or not right:
        return None
    left_cols = get_columns(left_review_id)
    right_cols = get_columns(right_review_id)

    def concepts(cols: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        out: dict[str, list[dict[str, Any]]] = {}
        for col in cols:
            for candidate in col.get("semantic_candidates", []):
                out.setdefault(candidate["concept"], []).append(col)
        return out

    lc, rc = concepts(left_cols), concepts(right_cols)
    shared = sorted(set(lc) & set(rc))
    concept_comparison = []
    for concept in shared:
        l = max(lc[concept], key=lambda x: x.get("unique_count", 0))
        r = max(rc[concept], key=lambda x: x.get("unique_count", 0))
        ls, rs = l.get("stats", {}), r.get("stats", {})
        lval, rval = ls.get("sum"), rs.get("sum")
        delta = ((rval - lval) / abs(lval) * 100) if isinstance(lval, (int, float)) and isinstance(rval, (int, float)) and lval != 0 else None
        concept_comparison.append({"concept": concept, "left_column": l["name"], "right_column": r["name"], "left_sum": lval, "right_sum": rval, "delta_percent": round(delta, 2) if delta is not None else None})

    def dims(review_id: int) -> list[dict[str, Any]]:
        data = get_dataset(review_id)
        return [d for table in (data.get("tables", []) if data else []) for d in table.get("dimension_candidates", [])]

    left_entities = {(d["name"], tuple(d.get("sample_values", []))) for d in dims(left_review_id)}
    right_entities = {(d["name"], tuple(d.get("sample_values", []))) for d in dims(right_review_id)}
    return {
        "left": {"id": left["id"], "name": left["name"], "file": left.get("uploaded_file", {}).get("filename")},
        "right": {"id": right["id"], "name": right["name"], "file": right.get("uploaded_file", {}).get("filename")},
        "schema": {"left_columns": len(left_cols), "right_columns": len(right_cols), "shared_concepts": shared, "left_only_concepts": sorted(set(lc)-set(rc)), "right_only_concepts": sorted(set(rc)-set(lc))},
        "concept_comparison": concept_comparison,
        "entity_columns": {"left": sorted({x[0] for x in left_entities}), "right": sorted({x[0] for x in right_entities})},
    }
