# StyleSync

StyleSync is a smart digital wardrobe prototype built from the project prompt.

## Apps

- `frontend/`: React + Vite + Tailwind dashboard.
- `backend/`: FastAPI API with auth, wardrobe, duplicate-check, recommendation, and analytics routes.
- `StyleSync_Architecture_Document.md`: software architecture and implementation plan.

## Current Prototype Features

- Register/login with signed bearer tokens.
- Protected wardrobe, analytics, recommendation, and duplicate-check APIs.
- Wardrobe photo upload with server-side file validation.
- Prototype AI metadata extraction and similarity scoring.
- Frontend flows wired to the FastAPI backend with React Query.

## Run Frontend

```powershell
cd frontend
npm install
npm run dev
```

## Run Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend URL: `http://127.0.0.1:5173`  
Backend docs: `http://127.0.0.1:8000/docs`
