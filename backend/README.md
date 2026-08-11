# StyleSync Backend

FastAPI prototype for the StyleSync smart wardrobe system.

## Run Locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.

## Current Scope

This first milestone uses in-memory storage and deterministic AI placeholders. The route structure is intentionally aligned with the final architecture so MongoDB, Cloudinary, CLIP, and FAISS can be added module by module without changing frontend flows.
