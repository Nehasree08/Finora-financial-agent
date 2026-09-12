from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile

from services.analysis_pipeline import analyze_upload
from services.repository import compare_reviews, compare_within_review, delete_review, get_audit_analysis, get_columns, get_comparison_options, get_dataset, get_records, get_review, list_reviews

router = APIRouter()


@router.get("/")
def root():
    return {
        "service": "FINORA financial statement review API",
        "status": "online",
        "health": "/health",
        "docs": "/docs",
    }


@router.get("/health")
def health():
    return {"ok": True, "engine": "finora-python", "mode": "sqlite-persistent-ingestion", "database": "fin_audit.db"}


@router.post("/analyze")
async def analyze(file: UploadFile = File(...), company: str | None = Form(default=None), year: str | None = Form(default=None)):
    content = await file.read()
    return analyze_upload(file.filename or "upload", content, company, year, file.content_type)


@router.post("/reviews")
async def create_review(file: UploadFile = File(...), company: str | None = Form(default=None), period: str | None = Form(default=None)):
    content = await file.read()
    return analyze_upload(file.filename or "upload", content, company, period, file.content_type)


@router.get("/reviews")
def reviews():
    return {"success": True, "items": list_reviews()}


@router.get("/reviews/{review_id}")
def review(review_id: int):
    item = get_review(review_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Review not found.")
    return {"success": True, "review": item}


@router.get("/reviews/{review_id}/dataset")
def dataset(review_id: int):
    item = get_dataset(review_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Review not found.")
    return {"success": True, "dataset": item}


@router.get("/reviews/{review_id}/columns")
def columns(review_id: int):
    if get_review(review_id) is None:
        raise HTTPException(status_code=404, detail="Review not found.")
    return {"success": True, "items": get_columns(review_id)}


@router.get("/reviews/{review_id}/records")
def records(review_id: int, offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=1000)):
    if get_review(review_id) is None:
        raise HTTPException(status_code=404, detail="Review not found.")
    total, items = get_records(review_id, offset, limit)
    return {"success": True, "offset": offset, "limit": limit, "total": total, "items": items}


@router.get("/reviews/{review_id}/comparison-options")
def comparison_options(review_id: int):
    options = get_comparison_options(review_id)
    if options is None:
        raise HTTPException(status_code=404, detail="Review not found.")
    return {"success": True, **options}


@router.get("/reviews/{review_id}/audit")
def audit(review_id: int):
    result = get_audit_analysis(review_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Review not found.")
    return {"success": True, "audit": result}


@router.get("/reviews/{review_id}/compare")
def compare_within_dataset(review_id: int, entity_column: str, metric: str, left: str, right: str):
    try:
        result = compare_within_review(review_id, entity_column, metric, left, right)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Review not found.")
    return {"success": True, "comparison": result}


@router.delete("/reviews/{review_id}")
def remove_review(review_id: int):
    if not delete_review(review_id):
        raise HTTPException(status_code=404, detail="Review not found.")
    return {"success": True, "deleted": review_id}


@router.get("/compare")
def compare(left_review_id: int = Query(..., ge=1), right_review_id: int = Query(..., ge=1)):
    result = compare_reviews(left_review_id, right_review_id)
    if result is None:
        raise HTTPException(status_code=404, detail="One or both reviews were not found.")
    return {"success": True, "comparison": result}
