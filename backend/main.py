from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routes import router
from db import init_db
from utils.errors import AnalysisError

init_db()

app = FastAPI(title="FINORA", description="Persistent financial dataset ingestion and profiling engine.", version="2.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001", "http://127.0.0.1:3001"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(router)


@app.exception_handler(AnalysisError)
async def analysis_error_handler(_: Request, exc: AnalysisError):
    return JSONResponse(status_code=exc.status_code, content={"success": False, "error": exc.message, "errors": [exc.message]})


@app.exception_handler(Exception)
async def unhandled_error_handler(_: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"success": False, "error": "Processing failed while handling the uploaded file.", "errors": [str(exc)]})
