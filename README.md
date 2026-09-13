# ALEX — AI Knowledge & Research Assistant

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3.1-61DAFB.svg?style=flat&logo=react&logoColor=black)](https://reactjs.org/)
[![Vite](https://img.shields.io/badge/Vite-5.4.11-646CFF.svg?style=flat&logo=vite&logoColor=white)](https://vitejs.dev/)
[![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-3.4.17-38B2AC.svg?style=flat&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16_pgvector-336791.svg?style=flat&logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![Google Gemini](https://img.shields.io/badge/Google_Gemini-2.5_Flash-4285F4.svg?style=flat&logo=google&logoColor=white)](https://aistudio.google.com/)
[![LangChain](https://img.shields.io/badge/LangChain-LangGraph-1C3C3C.svg?style=flat)](https://www.langchain.com)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg?style=flat&logo=python&logoColor=white)](https://www.python.org)

Alex is a modern, ChatGPT-style conversational AI assistant built for grounded document question-answering with structured citations and session-scoped temporary file isolation.

---

## 🏛️ System Architecture

```
                    INTERNET
                       │
             ┌─────────┴─────────┐
             │                   │
          VERCEL              RAILWAY
     (React 18 + Vite)     (FastAPI Backend)
             │                   │
             │        ┌──────────┼──────────┐
             │        │          │          │
             │    PostgreSQL   pgvector   Google Gemini
             │   (Data/Chunks) (Vectors)   (Synthesis)
             │
             │              Railway Volume
             │                   │
             │           /app/storage/documents
             │           (Session Temp Files)
             │
             └──── HTTPS API ────┘
```

- **Frontend (Vercel)**: React + Vite single-page chat application with auto-expanding composer, suggestion cards, in-composer file attachments, and compact citation cards.
- **Backend (Railway)**: FastAPI monolithic web API running on Python 3.11 with dynamic `$PORT` binding.
- **Vector & Relational Storage (Railway PostgreSQL)**: Relational tables (`documents`, `document_chunks`, `agent_audit_logs`) and native 384-dimensional cosine vector indexes via `pgvector`.
- **Session File Storage (Railway Volume)**: Mounted at `/app/storage` for temporary PDF, DOCX, and TXT files.
- **Embeddings**: In-process FastEmbed (`BAAI/bge-small-en-v1.5`) eliminating heavy PyTorch/CUDA overhead.
- **LLM**: Google Gemini (`gemini-2.5-flash`) via LangGraph for hallucination-free grounded answers.

---

## 📁 Repository Structure

```text
alex/
├── app/
│   ├── api/                    # FastAPI routes, schemas, and main entry
│   │   ├── main.py             # App initialization, CORS, and health checks
│   │   ├── schemas.py          # Pydantic request & response models
│   │   └── v1/
│   │       ├── endpoints/      # Chat and Documents REST endpoints
│   │       └── router.py
│   ├── agents/                 # LangGraph RAG workflow agent
│   ├── core/                   # DB engine, LLM factory, and configuration
│   │   ├── db.py               # SQLAlchemy engine & pgvector migration safety
│   │   ├── llm.py              # Gemini client initialization
│   │   └── config.py           # Pydantic settings & CORS parsing
│   ├── models/                 # SQLAlchemy ORM models (Document, DocumentChunk)
│   └── services/               # Core services (document processing, chunking, embeddings, RAG)
├── frontend/                   # React + Vite + Tailwind CSS frontend
│   ├── src/
│   │   ├── components/         # ChatInput, ChatMessage, DocumentsView, Header
│   │   ├── services/api.js     # Backend API client
│   │   └── App.jsx             # Chat state, active scope, and New Chat cleanup
│   ├── vercel.json             # Vercel deployment & SPA rewrites configuration
│   └── package.json
├── tests/                      # Pytest automated test suite (54 tests)
├── storage/documents/          # Local/container document storage directory
├── Dockerfile                  # Production container definition (Railway ready)
├── .dockerignore               # Docker context exclusion rules
├── railway.json                # Railway build, deploy, and healthcheck specification
├── docker-compose.yml          # Local development stack (Postgres + pgvector)
├── requirements.txt            # Python dependencies
└── .env.example                # Environment variable template
```

---

## 🔒 Security & Privacy by Design

1. **Strict Chat Isolation**: Uploaded documents and vector chunks are tagged with a unique `chat_id`. Vector similarity search strictly queries `Document.chat_id == chat_id`, guaranteeing zero cross-session context leakage.
2. **Cascading Session Cleanup**: Clicking **`+ New Chat`** triggers an immediate backend deletion of all documents, chunks, and vector embeddings belonging to that chat session, and deletes the physical files from storage.
3. **Safe Storage Path Defense**: Physical files on disk are named using server-generated UUIDs (`<uuid>.<ext>`), preventing directory traversal attacks. File deletion operations verify paths remain within `STORAGE_DIR`.
4. **No Secrets Exposed**: Frontend bundle never touches database credentials, Google API keys, or storage paths. All external AI operations occur inside FastAPI.

---

## 🚀 Local Development Setup

### Prerequisites
- **Python**: 3.11 or higher
- **Node.js**: 18 or higher
- **Docker & Docker Compose**: 20.10+
- **Google Gemini API Key**: Free from [Google AI Studio](https://aistudio.google.com/)

### Step 1: Clone and Configure Environment

```bash
git clone https://github.com/ankesh15/Alex.git
cd Alex

# Copy backend environment template
cp .env.example .env

# Edit .env and set your Google API Key:
# GOOGLE_API_KEY=AIzaSy...
```

### Step 2: Start PostgreSQL with pgvector

```bash
docker compose up -d postgres
```

### Step 3: Run Backend

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run FastAPI server
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload
```

FastAPI will be available at `http://localhost:8000`. Interactive OpenAPI documentation is at `http://localhost:8000/docs`.

### Step 4: Run Frontend

In a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

---

## 🌐 Production Deployment Guide

### Part 1: Deploy Backend to Railway

#### 1. Create a Railway Project
1. Log in to [Railway](https://railway.app/).
2. Click **New Project** → **Deploy from GitHub repo** and select `ankesh15/Alex`.

#### 2. Provision PostgreSQL with pgvector
1. In your Railway project, click **Create** → **Database** → **Add PostgreSQL**.
2. Railway automatically attaches a PostgreSQL 16 database and sets the `DATABASE_URL` environment variable for your project.
3. Once the database is active, open the **Data** or **Query** tab in Railway and verify `pgvector` by running:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
   *(Note: Alex's backend also executes this automatically on startup).*

#### 3. Attach a Persistent Railway Volume for Files
1. Click on your Alex backend service in the Railway canvas.
2. Go to the **Volumes** tab and click **Add Volume**.
3. Set the **Mount Path** to:
   ```text
   /app/storage
   ```
4. Click **Add**. This guarantees uploaded documents persist across container restarts.

#### 4. Configure Railway Environment Variables
In your Alex service under **Variables**, set:

| Variable | Value | Description |
|---|---|---|
| `GOOGLE_API_KEY` | `your_gemini_api_key` | Google Gemini API key from AI Studio |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model name |
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` | Auto-populated reference to Railway Postgres |
| `STORAGE_DIR` | `/app/storage/documents` | Storage path inside Railway Volume |
| `MAX_UPLOAD_SIZE_MB` | `20` | Upload limit per document |
| `ALLOWED_ORIGINS` | `https://your-alex-frontend.vercel.app,http://localhost:5173` | Allowed CORS origins |
| `FRONTEND_URL` | `https://your-alex-frontend.vercel.app` | Vercel production frontend domain |

#### 5. Verify Railway Deployment
Railway uses the root [Dockerfile](file:///home/ankesh/ALEX/Alex/Dockerfile) and [railway.json](file:///home/ankesh/ALEX/Alex/railway.json).
- Health check path: `/health`
- Dynamic port: Automatically listens on `0.0.0.0:$PORT`
- Once deployed, copy your public Railway URL (e.g. `https://alex-backend.up.railway.app`).

---

### Part 2: Deploy Frontend to Vercel

#### 1. Import Project into Vercel
1. Log in to [Vercel](https://vercel.com/).
2. Click **Add New** → **Project** and select `ankesh15/Alex`.
3. In the project setup screen:
   - **Framework Preset**: `Vite`
   - **Root Directory**: Click **Edit** and choose `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`

#### 2. Configure Vercel Environment Variables
Under **Environment Variables**, add:

| Variable | Value | Description |
|---|---|---|
| `VITE_API_URL` | `https://<your-railway-app-name>.up.railway.app` | Your deployed Railway backend URL (no trailing slash) |

#### 3. Deploy
1. Click **Deploy**. Vercel will build the frontend in ~20 seconds using [frontend/vercel.json](file:///home/ankesh/ALEX/Alex/frontend/vercel.json).
2. Once complete, copy your Vercel URL (e.g. `https://alex-knowledge.vercel.app`) and add it to `ALLOWED_ORIGINS` / `FRONTEND_URL` in Railway.

---

## 🧪 Automated Testing & Code Quality

Run the test suite locally:

```bash
# Run all 54 unit & integration tests
venv/bin/pytest -v

# Run lint checks
venv/bin/flake8 --count --select=E9,F63,F7,F82,F401,F841,F811 app tests

# Run frontend build check
cd frontend && npm run build
```

---

## ✅ Production Smoke Test Checklist

After deploying to Railway and Vercel, verify your deployment:

1. **General Chat**:
   - Open your Vercel frontend.
   - Ask: `"What is binary search?"`
   - *Expected*: Synthesized answer from Gemini with 0 document citations.
2. **File Upload**:
   - Click the `+` attach button in the composer and select a PDF or DOCX file (e.g. `research_notes.pdf`).
   - *Expected*: Compact attachment chip appears above composer; status changes from `PROCESSING` to `READY`.
3. **Document RAG with Citations**:
   - Ask a question specific to the uploaded file.
   - *Expected*: Grounded answer with expandable source cards citing the document name, page number, and similarity score.
4. **Documents View Scoping**:
   - Click the `Documents` tab.
   - *Expected*: Only the document uploaded in the current chat is listed.
5. **New Chat Isolation & Cleanup**:
   - Click **`+ New Chat`**.
   - *Expected*: Conversation resets, attachment chips clear, Documents page becomes empty, and the backend deletes the physical file from the storage volume and purges vector records.
6. **Cross-Chat Privacy**:
   - In the new chat, ask about the previous document.
   - *Expected*: Alex states that no documents are available or context is insufficient, verifying complete session isolation.

---

## 📄 License
MIT License. Built as an AI research assistant portfolio project.
