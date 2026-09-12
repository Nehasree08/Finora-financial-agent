# FINORA — Cinematic Audit Intelligence

This bundle combines a cinematic Next.js frontend with the SQLite-persistent ingestion backend.

## Backend
```powershell
cd backend
python -m pip install -r requirements.txt
python -m pytest -q
python -m uvicorn main:app --reload --port 8000
```

## Frontend
```powershell
cd frontend
npm install
npm run dev
```
Optional `.env.local`:
```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```
Open `http://localhost:3000/app/dashboard`.

## Intelligence
The backend preserves uploaded source rows, reads every Excel sheet, profiles every discovered field, identifies semantic financial candidates and entity/dimension candidates, and exposes `/compare` to compare two persisted datasets without requiring a fixed schema.

The current AI UI is grounded in persisted profile metadata and deliberately does not fabricate audit conclusions. The next engine stage adds validation, variance, ratios, anomaly scoring, findings/evidence, workpapers and grounded AI reasoning.
