from __future__ import annotations

import io
import sqlite3

import pandas as pd
from fastapi.testclient import TestClient

import db
from main import app


client = TestClient(app)


def make_csv() -> bytes:
    return b"Date,Company,Revenue,Expenses,Account ID\n2026-01-01,Acme,1000,700,A001\n2026-02-01,Acme,1200,800,A002\n2026-03-01,Beta,900,600,B001\n"


def make_xlsx() -> bytes:
    stream = io.BytesIO()
    with pd.ExcelWriter(stream, engine="openpyxl") as writer:
        pd.DataFrame({"Date": ["2026-01-01", "2026-02-01"], "Revenue": [100, 200]}).to_excel(writer, sheet_name="Income", index=False)
        pd.DataFrame({"Account": ["A", "B"], "Assets": [500, 700]}).to_excel(writer, sheet_name="Balance", index=False)
    return stream.getvalue()


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["database"] == "fin_audit.db"


def test_csv_is_persisted_and_retrievable(tmp_path, monkeypatch):
    test_db = tmp_path / "test.db"
    monkeypatch.setattr(db, "DB_PATH", test_db)
    import services.repository as repository
    monkeypatch.setattr(repository, "DB_PATH", test_db, raising=False)

    response = client.post("/reviews", files={"file": ("audit.csv", make_csv(), "text/csv")}, data={"company": "Acme", "period": "2026"})
    assert response.status_code == 200, response.text
    payload = response.json()
    review_id = payload["review_id"]
    assert payload["profile"]["total_rows"] == 2
    assert payload["profile"]["total_columns"] == 5
    assert payload["file"]["sha256"]

    detail = client.get(f"/reviews/{review_id}").json()["review"]
    assert detail["company"] == "Acme"
    assert detail["datasets"][0]["row_count"] == 2

    records = client.get(f"/reviews/{review_id}/records?limit=10").json()
    assert records["total"] == 2
    assert records["items"][0]["values"]["Revenue"] == 1000

    columns = client.get(f"/reviews/{review_id}/columns").json()["items"]
    revenue = next(x for x in columns if x["name"] == "Revenue")
    assert revenue["inferred_type"] == "numeric"
    assert revenue["stats"]["sum"] == 2200


def test_missing_values_are_json_safe_in_records(tmp_path, monkeypatch):
    test_db = tmp_path / "test.db"
    monkeypatch.setattr(db, "DB_PATH", test_db)
    import services.repository as repository
    monkeypatch.setattr(repository, "DB_PATH", test_db, raising=False)

    response = client.post(
        "/reviews",
        files={"file": ("audit.csv", b"Company,Revenue\nAcme,100\nBeta,\n", "text/csv")},
    )
    assert response.status_code == 200, response.text
    review_id = response.json()["review_id"]

    records = client.get(f"/reviews/{review_id}/records").json()
    assert records["items"][1]["values"]["Revenue"] is None


def test_xlsx_reads_all_sheets(tmp_path, monkeypatch):
    test_db = tmp_path / "test.db"
    monkeypatch.setattr(db, "DB_PATH", test_db)
    response = client.post("/reviews", files={"file": ("audit.xlsx", make_xlsx(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["profile"]["table_count"] == 2
    assert {x["sheet_name"] for x in data["profile"]["tables"]} == {"Income", "Balance"}
    assert data["profile"]["total_rows"] == 4


def test_delete_cascades(tmp_path, monkeypatch):
    test_db = tmp_path / "test.db"
    monkeypatch.setattr(db, "DB_PATH", test_db)
    response = client.post("/reviews", files={"file": ("audit.csv", make_csv(), "text/csv")})
    review_id = response.json()["review_id"]
    assert client.delete(f"/reviews/{review_id}").status_code == 200
    assert client.get(f"/reviews/{review_id}").status_code == 404
    conn = sqlite3.connect(test_db)
    try:
        assert conn.execute("SELECT COUNT(*) FROM uploaded_files").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM datasets").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM financial_records").fetchone()[0] == 0
    finally:
        conn.close()


def test_entity_discovery_and_compare():
    import io
    csv1 = b"Company,Revenue,Expenses\nAlpha,100,60\nBeta,200,120\n"
    csv2 = b"Company,Revenue,Expenses\nAlpha,120,70\nGamma,300,180\n"
    r1 = client.post('/reviews', files={'file': ('a.csv', io.BytesIO(csv1), 'text/csv')})
    r2 = client.post('/reviews', files={'file': ('b.csv', io.BytesIO(csv2), 'text/csv')})
    assert r1.status_code == 200 and r2.status_code == 200
    a, b = r1.json()['review_id'], r2.json()['review_id']
    comparison = client.get(f'/compare?left_review_id={a}&right_review_id={b}')
    assert comparison.status_code == 200
    body = comparison.json()['comparison']
    assert 'revenue' in body['schema']['shared_concepts']
    assert 'Company' in body['entity_columns']['left']


def test_compare_entities_within_one_review(tmp_path, monkeypatch):
    test_db = tmp_path / "test.db"
    monkeypatch.setattr(db, "DB_PATH", test_db)
    csv = b"Company,Revenue,Net Income\nAmazon,100,10\nAmazon,200,20\nApple,150,30\n"
    response = client.post("/reviews", files={"file": ("companies.csv", csv, "text/csv")})
    review_id = response.json()["review_id"]

    options = client.get(f"/reviews/{review_id}/comparison-options").json()
    assert "Company" in [item["name"] for item in options["entity_columns"]]
    comparison = client.get(f"/reviews/{review_id}/compare?entity_column=Company&metric=Revenue&left=Amazon&right=Apple")
    assert comparison.status_code == 200
    body = comparison.json()["comparison"]
    assert body["left"]["sum"] == 300
    assert body["right"]["sum"] == 150
    assert body["difference"] == -150


def test_compare_all_metrics_and_company_scope(tmp_path, monkeypatch):
    test_db = tmp_path / "test.db"
    monkeypatch.setattr(db, "DB_PATH", test_db)
    csv = b"Company,Revenue,Expenses,Net Income\nAmazon,100,60,40\nApple,150,90,60\n"

    scoped = client.post("/reviews", files={"file": ("companies.csv", csv, "text/csv")}, data={"company": "Amazon"})
    assert scoped.status_code == 200, scoped.text
    scoped_id = scoped.json()["review_id"]
    scoped_records = client.get(f"/reviews/{scoped_id}/records").json()
    assert scoped_records["total"] == 1
    assert scoped_records["items"][0]["values"]["Company"] == "Amazon"

    full = client.post("/reviews", files={"file": ("companies.csv", csv, "text/csv")})
    full_id = full.json()["review_id"]
    comparison = client.get(f"/reviews/{full_id}/compare?entity_column=Company&metric=__all__&left=Amazon&right=Apple")
    assert comparison.status_code == 200
    metrics = {item["metric"] for item in comparison.json()["comparison"]["metrics"]}
    assert {"Revenue", "Expenses", "Net Income"}.issubset(metrics)
