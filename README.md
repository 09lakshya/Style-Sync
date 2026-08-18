# StyleSync — Smart Wardrobe & Personalized Recommendation System

StyleSync is an AI-assisted digital wardrobe management web application. Users can upload clothing photos, digitize their wardrobe, analyze outfit recommendations, track wardrobe analytics, and prevent duplicate purchases by running visual similarity checks against existing items.

---

## 1. Project Overview

StyleSync solves common wardrobe management problems through computer vision and structured recommendations:
- **Digital Wardrobe Management:** Category-based inventory tracking (tops, bottoms, dresses, footwear, accessories).
- **Duplicate Purchase Prevention:** AI visual search comparing shopping images against saved clothing items using vector embeddings.
- **Personalized Recommendations:** Rule-based outfit pairings based on color harmony, season, and occasion metrics.
- **Wardrobe Analytics:** Aggregate reporting on item usage, category counts, dominant colors, and unused clothing reminders.

---

## 2. Current Technology Stack

| Layer | Technology | Usage |
| :--- | :--- | :--- |
| **Frontend** | React 19 + Vite + TypeScript | Interactive SPA UI |
| **Styling** | Tailwind CSS + Lucide Icons | Responsive luxury editorial styling |
| **State Management** | TanStack Query (React Query) | Server-state fetching & caching |
| **Backend Framework** | FastAPI (Python 3.13) | Async REST API modular monolith |
| **ORM / Persistence** | SQLAlchemy 2.0 (AsyncSession) | Database layer abstraction |
| **Database** | SQLite (`aiosqlite`) / MySQL (`aiomysql`) | Relational application storage |
| **Authentication** | JWT + bcrypt | Stateless bearer token security |
| **Image Hosting** | Cloudinary API | Cloud storage, web optimizations, thumbnails |
| **Image Processing** | OpenCV + Pillow | CLAHE preprocessing, K-Means color extraction |
| **AI / Embeddings** | PyTorch + OpenAI CLIP (`clip-vit-base-patch32`) | 512-dim visual embeddings & cosine similarity |

---

## 3. Architecture

StyleSync uses a **Layered Modular Monolith** pattern:

```text
React + Vite Frontend
        ↓ (HTTP REST API + JWT Bearer Auth)
FastAPI Application
        ↓
Routers (Auth, Wardrobe, Shopping, Recommendations, Analytics)
        ↓
Service Layer (Business Logic, Metadata Inference, Similarity Calculations)
        ↓
Repository Layer (Data Access Abstraction)
        ↓
SQLAlchemy AsyncSession (ORM)
        ↓
SQLite (`stylesync.db`) / MySQL Database
```

### MVC Conceptual Mapping
- **Model:** SQLAlchemy ORM models (`User`, `WardrobeItem`, `Embedding`, `ShoppingCheck`) + Repository layer.
- **Controller:** FastAPI Routers (`auth`, `wardrobe`, `shopping`, `recommendations`, `analytics`).
- **View:** React frontend client UI components.

---

## 4. Authentication

Authentication is handled via JWT tokens:
- **Registration (`POST /api/v1/auth/register`):** Creates user, hashes password with `bcrypt`, generates access token.
- **Login (`POST /api/v1/auth/login`):** Validates email & password, returns JWT session token.
- **Protected Routes:** Handled via `HTTPBearer` header (`Authorization: Bearer <token>`).

---

## 5. Database Configuration

The application uses SQLAlchemy with `AsyncSession`. Database connection string is configured via `DATABASE_URL`:

- **Development / Local Default (SQLite):**
  ```env
  DATABASE_URL=sqlite+aiosqlite:///./stylesync.db
  ```
- **Production / MySQL Compatibility:**
  ```env
  DATABASE_URL=mysql+aiomysql://user:password@localhost:3306/stylesync
  ```

---

## 6. Cloudinary Image Storage

- Uploaded images are validated for size (max 10MB) and MIME type (`JPEG`, `PNG`, `WEBP`).
- Images are stored on Cloudinary with automatic optimized delivery URLs (`thumbnail_url`, `medium_url`, `image_url`).
- Local fallback is active when Cloudinary API credentials are not set.

---

## 7. AI & Embeddings (OpenAI CLIP)

- **Model:** OpenAI CLIP (`clip-vit-base-patch32`) via PyTorch.
- **Feature Extraction:** Preprocesses image binary using OpenCV CLAHE & contrast enhancement, extracting a 512-dimensional normalized vector embedding.
- **Similarity Detection:** Cosine similarity scoring compares shopping inquiry images against user wardrobe vector embeddings to detect duplicate clothing items.

---

## 8. Dataset Pipeline

A reproducible 5-stage data curation pipeline is implemented in `dataset/scripts/`:
1. `01_parse_and_filter.py`: Annotation parsing & resolution filtering.
2. `02_deduplicate.py`: Perceptual hashing (`imagehash`) deduplication.
3. `03_extract_colors.py`: K-Means dominant color extraction.
4. `04_balance_and_split.py`: Stratified 70/15/15 train/val/test split (800 items).
5. `05_generate_statistics.py`: Report generator.

---

## 9. Environment Variables

Create a `.env` file in `backend/`:

```env
APP_NAME=StyleSync
API_V1_PREFIX=/api/v1
FRONTEND_ORIGIN=http://localhost:5173
JWT_SECRET=stylesync-dev-super-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=1440
DATABASE_URL=sqlite+aiosqlite:///./stylesync.db

CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=
CLOUDINARY_FOLDER_PREFIX=stylesync

CLIP_MODEL_NAME=openai/clip-vit-base-patch32
AI_DEVICE=cpu
ENABLE_CLAHE_PREPROCESSING=true
```

---

## 10. Local Development & Running

### Running Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```
- API Base URL: `http://127.0.0.1:8000`
- Swagger Documentation: `http://127.0.0.1:8000/docs`

### Running Frontend

```powershell
cd frontend
npm install
npm run dev
```
- Web Application URL: `http://localhost:5173`

---

## 11. Testing & Build Verification

### Backend Test Suite
Run unit & integration tests (auth, wardrobe CRUD, Cloudinary fallbacks, CLIP embeddings):
```powershell
cd backend
python -m pytest
```

### Dependency Audit
```powershell
cd backend
pip check
```

### Frontend Build & Security Audit
```powershell
cd frontend
npm run build
npm audit --omit=dev
```

---

## 12. Current Project Status

| Component | Status | Details |
| :--- | :--- | :--- |
| **React Frontend** | **Completed** | Full SPA UI (Auth, Wardrobe, Duplicate Check, Recommendations, Analytics) |
| **FastAPI Backend** | **Completed** | Modular REST API with CORS and validation |
| **JWT Authentication** | **Completed** | Register, Login, token signing & verification |
| **SQLAlchemy Persistence** | **Completed** | Async ORM models & repository abstractions |
| **SQLite Local Database** | **Completed** | `stylesync.db` initialized and verified |
| **MySQL Compatibility** | **Completed** | `aiomysql` driver integration ready |
| **Cloudinary Storage** | **Completed** | Image upload, replacement, deletion & fallbacks |
| **CLIP Embeddings** | **Completed** | PyTorch 512-dim visual vector extraction |
| **Similarity Detection** | **Completed** | Cosine similarity scoring & decision logic |
| **Login & Signup UI** | **Completed** | Dark luxury editorial layout verified |
| **Dataset Pipeline** | **Ready** | 5-stage Python automation pipeline created |
| **Final Curated Dataset** | **Pending** | Pipeline execution on raw benchmark data pending |
| **Manual Dataset Annotation** | **Pending** | Manual tagging for season/occasion pending |
| **TensorFlow/Keras Model** | **Pending** | Optional custom classifier training pending |
| **Model Training & Evaluation** | **Pending** | Planned for subsequent academic milestone |
