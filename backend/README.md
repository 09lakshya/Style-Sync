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

The backend is built as a **FastAPI modular monolith** with async SQLAlchemy persistence (`sqlite+aiosqlite` for local development/testing, compatible with `mysql+aiomysql`), JWT authentication, Cloudinary media processing/storage, and OpenAI CLIP PyTorch vector embeddings for visual similarity and duplicate purchase detection.
