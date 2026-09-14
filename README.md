# ALEX — AI Knowledge & Research Assistant

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3.1-61DAFB.svg?style=flat&logo=react&logoColor=black)](https://reactjs.org/)
[![Vite](https://img.shields.io/badge/Vite-5.4.11-646CFF.svg?style=flat&logo=vite&logoColor=white)](https://vitejs.dev/)
[![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-3.4.17-38B2AC.svg?style=flat&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16_pgvector-336791.svg?style=flat&logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![Google Gemini](https://img.shields.io/badge/Google_Gemini-2.5_Flash-4285F4.svg?style=flat&logo=google&logoColor=white)](https://aistudio.google.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Workflow-1C3C3C.svg?style=flat)](https://www.langchain.com)
[![FastEmbed](https://img.shields.io/badge/FastEmbed-ONNX_CPU-FF6F00.svg?style=flat)](https://github.com/qdrant/fastembed)
[![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED.svg?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)

ALEX is an enterprise-grade AI knowledge and research assistant that pairs a modern, ChatGPT-style conversational interface with a LangGraph-orchestrated Retrieval-Augmented Generation (RAG) pipeline to deliver grounded answers, precise document citations, and strict session-isolated document workflows.

---

## 🚀 Live Demo

- **Live Demo (Frontend)**: [Live Demo](YOUR_VERCEL_URL)
- **Backend API**: [Backend API](YOUR_RAILWAY_URL)
- **API Documentation**: [Interactive Swagger Docs](YOUR_RAILWAY_URL/docs)

---

## ✨ Features

- **Dual Chat Experience**: Toggle effortlessly between general conversational AI mode and grounded document research mode.
- **Document-Grounded RAG**: Graph-orchestrated semantic retrieval ensures answers are synthesized strictly from source documents to eliminate hallucinations.
- **Multi-Format Ingestion**: Ingest, validate, and parse PDF, DOCX, and TXT files with automatic page metadata tracking.
- **Structured Source Citations**: Inspect exact source filenames, page numbers, and cosine similarity relevance scores for every generated claim.
- **Chat-Scoped Document Isolation**: Uploaded files and vector records are bound to unique session identifiers (`chat_id`), preventing cross-session context leakage.
- **Ephemeral Session Cleanup**: Starting a new chat automatically purges session files from disk and removes relational metadata and vector embeddings from PostgreSQL.
- **ChatGPT-Style Web Interface**: Polished, responsive user experience featuring an auto-expanding composer, suggestion prompts, in-composer file attachments, and token usage metrics.

---

## 🧠 How ALEX Works

### Document RAG Workflow

```
User Question + Document
           │
           ▼
  React / Vite Frontend
           │
           ▼
      FastAPI API
           │
    ┌──────┴──────────────────────────┐
    ▼                                 ▼
Document Ingestion             Question Embedding
 (PDF / DOCX / TXT)           (FastEmbed BAAI Model)
    │                                 │
 Text Extraction                      ▼
 & Chunking (LangChain)        Vector Similarity Search
    │                          (pgvector Cosine Distance)
    ▼                                 │
FastEmbed Vectorization               │
    │                                 ▼
    └──────────► PostgreSQL ◄─────────┘
                   (pgvector)
                       │
                       ▼
            LangGraph RAG Workflow
            ├─ [No Context] ──► Deterministic Fallback Notice
            └─ [Context] ────► Gemini 2.5 Flash Synthesis
                                      │
                                      ▼
                        Grounded Answer + Citations
```

### General Chat Workflow

When no document context is selected (General Chat mode), ALEX bypasses vector search and document retrieval entirely:

```
User Question ──► React Frontend ──► FastAPI (/api/v1/chat/general) ──► Google Gemini ──► Direct Answer
```

This dual-track design conserves compute, eliminates database queries for conversational prompts, and delivers instant responses for general inquiries.

---

## 🏗️ Architecture

| Component | Technology | Core Responsibility |
|---|---|---|
| **Frontend** | React 18, Vite 5, Tailwind CSS | Single-page application, chat lifecycle management, attachment uploading, and citation rendering. |
| **API Gateway** | FastAPI, Pydantic v2, Uvicorn | RESTful endpoints, request/response validation, CORS governance, and unified error handling. |
| **Document Processing** | PyMuPDF, python-docx, LangChain | File validation, text extraction, page number indexing, and recursive character chunking. |
| **Embedding Service** | FastEmbed (`BAAI/bge-small-en-v1.5`) | In-process, CPU-optimized 384-dimensional ONNX vector generation with zero PyTorch/CUDA overhead. |
| **Vector & Relational Store** | PostgreSQL 16 + `pgvector` | Relational document tracking with native HNSW/IVFFlat cosine distance similarity search. |
| **RAG Orchestration** | LangGraph, StateGraph | Deterministic DAG workflow managing context retrieval, threshold validation, answer synthesis, and citation assembly. |
| **LLM Inference** | Google Gemini (`gemini-2.5-flash`) | Context-grounded synthesis at zero temperature to guarantee deterministic, faithful generation. |

---

## 🛠️ Tech Stack

### Frontend
- **Framework**: React 18
- **Bundler & Tooling**: Vite 5
- **Styling**: Tailwind CSS 3
- **Icons**: Lucide React

### Backend
- **Language**: Python 3.11+
- **Web Framework**: FastAPI
- **Data Validation**: Pydantic v2 & Pydantic Settings
- **ORM & Database Client**: SQLAlchemy 2.0, Psycopg2-binary

### AI & Retrieval
- **LLM**: Google Gemini (`gemini-2.5-flash`) via `langchain-google-genai`
- **Workflow Orchestration**: LangGraph (`StateGraph`)
- **Text Splitter**: LangChain Text Splitters (`RecursiveCharacterTextSplitter`)
- **Embedding Model**: FastEmbed `BAAI/bge-small-en-v1.5` (384 dimensions, ONNX Runtime)

### Database & Storage
- **Relational & Vector Database**: PostgreSQL 16 with `pgvector`
- **Session File Storage**: Local filesystem or Railway Persistent Volume mount (`/app/storage/documents`)

### Infrastructure & Deployment
- **Containerization**: Docker (multi-stage Python 3.11 slim)
- **Backend Hosting**: Railway (Docker runtime with dynamic `$PORT` assignment)
- **Frontend Hosting**: Vercel (Edge CDN with SPA route rewrites)
- **CI/CD**: GitHub Actions (Linting, Pytest, and Docker build validation)

---

## 📄 Document Processing & RAG

1. **Supported Formats**: Ingests `.pdf`, `.docx`, and `.txt` files.
2. **Validation & Security**:
   - Rejects unapproved extensions.
   - Enforces an upload cap (default: 20 MB) and verifies non-empty payloads.
   - Saves files using server-generated UUID names (`<uuid>.<ext>`) to prevent directory traversal exploits.
3. **Text Extraction**:
   - **PDF**: PyMuPDF (`fitz`) parses text page-by-page, recording 1-based page indexes for granular citations.
   - **DOCX**: `python-docx` extracts structured paragraphs.
   - **TXT**: Native UTF-8 stream reader with graceful character replacement.
4. **Chunking**: `RecursiveCharacterTextSplitter` segments text into chunks (default: 1,000 characters with 150-character overlap) while preserving source page metadata.
5. **Local Vector Embeddings**: FastEmbed generates 384-dimensional embeddings in-process using the `BAAI/bge-small-en-v1.5` model, removing the latency and cost of third-party embedding APIs.
6. **Vector Search & Scoping**:
   - PostgreSQL `pgvector` computes cosine distance (`<=>`) between the query embedding and stored document chunks.
   - Queries are filtered strictly by `chat_id` and document processing status (`READY`).
   - Optional document-level filtering allows users to target queries at a single file.
7. **Relevance Thresholding & Fallback**:
   - Chunks exceeding the cosine distance threshold (default: `0.48`) are filtered out.
   - If no chunks pass the threshold, LangGraph routes execution to an `insufficient_context` node that returns:
     > *"I couldn't find enough relevant information in the uploaded documents to answer this question."*
8. **Grounded Generation & Citations**:
   - Gemini receives a strict anti-hallucination prompt instructing it to synthesize answers solely from retrieved blocks.
   - The RAG engine compiles structured citations containing `document_id`, `filename`, `page_number`, `chunk_id`, and `relevance_score`.

---

## 💬 Chat Experience

- **General Chat Mode**: Converse directly with Gemini for coding assistance, brainstorming, and general inquiries without requiring document uploads.
- **All Documents Mode**: Ask questions across all documents attached to the current active chat session.
- **Specific Document Mode**: Target a single uploaded document to narrow down retrieval scope.
- **In-Composer Attachments**: Attach documents directly from the chat input using the `+` button, with visual indicators transitioning from `PROCESSING` to `READY`.
- **Expandable Citations**: Each assistant response displays citation badges that reveal the exact source document, page number, and similarity score.
- **New Chat Session Isolation**: Clicking **`+ New Chat`** creates a fresh session identifier (`chat_id`), resets conversation history, and invokes `DELETE /api/v1/documents/chat/{chat_id}` to purge previous session documents from disk, database, and vector storage.

---

## 🔐 Security & Production Considerations

- **Server-Side Secret Management**: Google API keys and database credentials reside strictly on the server and are never exposed to the frontend client.
- **Strict Chat-Level Isolation**: Document chunks and vector embeddings are indexed by `chat_id`. Queries cannot access documents from other sessions.
- **Directory Traversal Protection**: Storage paths are validated with `_safe_file_path` to guarantee file reads and deletions remain strictly inside `STORAGE_DIR`. Files are stored under UUID filenames.
- **Safe File Deletion**: Deleting a document or resetting a chat session removes physical files from disk and triggers cascading foreign key deletions across relational chunks and vector embeddings.
- **Configurable CORS Policies**: Access is restricted to trusted origins via `ALLOWED_ORIGINS` and `FRONTEND_URL` settings.
- **Robust Input Validation**: All payloads and file uploads are validated via Pydantic schemas and MIME/extension checks.
- **Production Health Endpoint**: `GET /health` and `GET /` endpoints enable Railway and container orchestrators to monitor server liveness.

---

## 📁 Project Structure

```text
Alex/
├── app/
│   ├── agents/                 # LangGraph RAG state graph & workflow definitions
│   │   ├── base_state.py
│   │   └── rag_agent.py
│   ├── api/                    # FastAPI routes, routers, and schemas
│   │   ├── main.py             # App lifecycle, CORS, and health endpoints
│   │   ├── schemas.py          # Pydantic request & response models
│   │   └── v1/
│   │       ├── router.py       # API v1 route aggregator
│   │       └── endpoints/
│   │           ├── chat.py     # RAG and general chat endpoints
│   │           └── documents.py# Document upload, listing, and deletion
│   ├── core/                   # Core infrastructure
│   │   ├── config.py           # Pydantic BaseSettings configuration
│   │   ├── db.py               # SQLAlchemy engine & pgvector initialization
│   │   └── llm.py              # Gemini client & token usage parser
│   ├── models/                 # SQLAlchemy ORM models
│   │   ├── audit_log.py        # Query execution audit records
│   │   ├── document.py         # Document entity
│   │   └── document_chunk.py   # pgvector Vector(384) embedding chunks
│   └── services/               # Business logic services
│       ├── chunking_service.py # Recursive text chunking
│       ├── document_processor.py # Multi-format text extractors (PDF, DOCX, TXT)
│       ├── embedding_service.py# FastEmbed BAAI ONNX model singleton
│       ├── rag_service.py      # Retrieval, prompt assembly, and citations
│       └── vector_store.py     # pgvector cosine similarity search
├── frontend/                   # React + Vite client application
│   ├── src/
│   │   ├── components/
│   │   │   ├── Chat.jsx        # Message list and empty state
│   │   │   ├── ChatInput.jsx   # Auto-expanding composer & file attachment chip
│   │   │   ├── ChatMessage.jsx # Message bubble & citation cards
│   │   │   ├── Citations.jsx   # Source document citation details
│   │   │   ├── DocumentList.jsx# Document status list
│   │   │   ├── DocumentsView.jsx# Dedicated document management view
│   │   │   ├── Header.jsx      # Navigation header with New Chat button
│   │   │   └── UploadDocument.jsx # File upload drag-and-drop
│   │   ├── services/
│   │   │   └── api.js          # Client-side API service
│   │   ├── App.jsx             # Main application state and session management
│   │   └── main.jsx
│   ├── package.json
│   ├── tailwind.config.js
│   ├── vercel.json             # Vercel SPA routing configuration
│   └── vite.config.js
├── tests/                      # Pytest automated test suite (54 tests)
│   ├── test_api.py
│   ├── test_chat_api.py
│   ├── test_chat_isolation.py
│   ├── test_chunking.py
│   ├── test_deployment_config.py
│   ├── test_document_processor.py
│   ├── test_documents_api.py
│   ├── test_embedding.py
│   ├── test_general_chat_api.py
│   ├── test_llm.py
│   ├── test_rag_agent.py
│   ├── test_rag_service.py
│   └── test_vector_store.py
├── .env.example                # Backend environment variable template
├── Dockerfile                  # Production container definition
├── docker-compose.yml          # Local containerized Postgres + pgvector stack
├── railway.json                # Railway build & deployment configuration
└── requirements.txt            # Python dependencies
```

---

## ⚙️ Local Development

### Prerequisites
- **Python**: 3.11 or higher
- **Node.js**: 18 or higher & npm
- **Docker**: For running PostgreSQL with `pgvector`
- **Google Gemini API Key**: Obtainable from [Google AI Studio](https://aistudio.google.com/)

### Step 1: Clone Repository
```bash
git clone https://github.com/ankesh15/Alex.git
cd Alex
```

### Step 2: Set Up Backend Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Backend Requirements
```bash
pip install -r requirements.txt
```

### Step 4: Configure Backend Environment
```bash
cp .env.example .env
```
Edit `.env` and configure your credentials:
```env
GOOGLE_API_KEY=your_google_gemini_api_key
DATABASE_URL=postgresql://postgres:postgrespassword@localhost:5432/alex_db
```

### Step 5: Start PostgreSQL with pgvector
```bash
docker compose up -d postgres
```

### Step 6: Start FastAPI Backend
```bash
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload
```
The API is available at `http://localhost:8000`. Interactive documentation is accessible at `http://localhost:8000/docs`.

### Step 7: Install Frontend Dependencies
In a separate terminal:
```bash
cd frontend
npm install
```

### Step 8: Start Vite Frontend
```bash
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## 🔑 Environment Variables

> [!NOTE]
> Never commit actual secret keys or credentials to version control.

### Backend (`.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `GOOGLE_API_KEY` | Yes | *None* | Google Gemini API key from Google AI Studio. |
| `GEMINI_MODEL` | No | `gemini-2.5-flash` | Gemini model variant used for inference. |
| `DATABASE_URL` | Yes | `postgresql://...` | PostgreSQL connection string with `pgvector` support. |
| `ALLOWED_ORIGINS` | No | `http://localhost:5173,...` | Comma-separated list of allowed CORS origins. |
| `FRONTEND_URL` | No | *None* | Production Vercel domain (appended to allowed origins). |
| `STORAGE_DIR` | No | `storage/documents` | Filesystem path for uploaded files (`/app/storage/documents` on Railway). |
| `MAX_UPLOAD_SIZE_MB` | No | `20` | Maximum file upload size limit in megabytes. |
| `EMBEDDING_MODEL` | No | `BAAI/bge-small-en-v1.5` | FastEmbed sentence embedding model. |
| `EMBEDDING_DIMENSION` | No | `384` | Embedding vector dimension for pgvector storage. |
| `CHUNK_SIZE` | No | `1000` | Target character size for document chunks. |
| `CHUNK_OVERLAP` | No | `150` | Character overlap between consecutive chunks. |
| `RAG_TOP_K` | No | `5` | Maximum number of chunks retrieved per query. |
| `RAG_SIMILARITY_THRESHOLD` | No | `0.48` | Maximum cosine distance for relevance filtering. |

### Frontend (`frontend/.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `VITE_API_URL` | Yes | `http://localhost:8000` | Base URL of the backend API (e.g., your Railway URL in production). |

---

## 🔌 API Endpoints

### Health Checks
- **`GET /`**: Platform service status and API metadata.
- **`GET /health`**: Health check probe returning `{"status": "ok"}` for container orchestrators.

### Conversational Chat
- **`POST /api/v1/chat`**: Execute document-grounded RAG query.
  - **Body**: `{ "question": str, "document_id": Optional[str], "chat_id": Optional[str], "top_k": Optional[int] }`
  - **Response**: Grounded answer, structured citations list, task ID, and token usage metrics.
- **`POST /api/v1/chat/general`**: Direct conversational query without document retrieval.
  - **Body**: `{ "question": str }`
  - **Response**: Generated answer and token usage metrics.

### Document Management
- **`POST /api/v1/documents/upload`**: Upload and ingest document (`multipart/form-data`: `file`, `chat_id`).
- **`GET /api/v1/documents`**: List all uploaded documents, with optional `?chat_id=` filtering.
- **`GET /api/v1/documents/{document_id}`**: Retrieve document metadata, processing status, and page count.
- **`DELETE /api/v1/documents/{document_id}`**: Delete a document, its physical disk file, and associated vector chunks.
- **`DELETE /api/v1/documents/chat/{chat_id}`**: Delete all documents, physical files, and embeddings associated with a chat session.

---

## 🧪 Testing

The repository contains an automated test suite verifying API contracts, document parsing, embeddings, pgvector operations, LangGraph workflows, and chat isolation.

```bash
# Run the complete test suite (54 passed tests)
pytest -v

# Run the frontend production build verification
cd frontend && npm run build
```

The test suite leverages an in-memory SQLite database with an algorithmic Python fallback for cosine distance calculations, enabling full unit test execution without requiring an active PostgreSQL container.

---

## 🚢 Deployment

### Architecture

```
User Browser
     │
     ├── HTTPS (Static Assets) ──► Vercel (React + Vite SPA)
     │
     └── HTTPS (API Requests)  ──► Railway (Docker Container / FastAPI)
                                        │
                                        ├── Internal TCP ──► Railway PostgreSQL + pgvector
                                        │
                                        └── Volume Mount ──► Railway Persistent Storage (/app/storage)
```

### Production Configuration

1. **Backend & Database (Railway)**:
   - Built via the root [Dockerfile](Dockerfile) and configured via [railway.json](railway.json).
   - Dynamic port binding via `$PORT` environment variable.
   - Healthcheck configured at `/health`.
   - Railway PostgreSQL provisioned with `pgvector` extension.
   - A persistent volume mounted at `/app/storage` guarantees document preservation during container redeployments.
   - Environment variables required: `GOOGLE_API_KEY`, `DATABASE_URL`, `STORAGE_DIR=/app/storage/documents`, `FRONTEND_URL`.

2. **Frontend (Vercel)**:
   - Root directory set to `frontend`.
   - Build command: `npm run build` (output: `dist`).
   - [vercel.json](frontend/vercel.json) specifies Single-Page Application (SPA) rewrites routing all traffic to `/index.html`.
   - Environment variable required: `VITE_API_URL` set to the public Railway backend URL (no trailing slash).

---

## 🔮 Future Improvements

- **Conversational Memory Persistence**: Persist multi-turn conversation threads across sessions using a database-backed chat history store.
- **Live Web Research**: Integrate real-time search engine APIs to corroborate document data with verified web sources.
- **Automated Research Report Generation**: Enable users to export synthesized multi-document research findings into structured Markdown or PDF reports.
- **User Authentication & Multi-Tenancy**: Introduce OAuth2/JWT user authentication for personalized document libraries and organization-level workspaces.
- **Asynchronous Processing Queues**: Offload heavy document ingestion jobs to the configured Celery workers and Redis broker for large document batches.

---

## 📄 License

This project is licensed under the MIT License.
