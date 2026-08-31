# Alex — AI Knowledge & Research Assistant

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![LangChain](https://img.shields.io/badge/LangChain-LangGraph-1C3C3C.svg?style=flat)](https://www.langchain.com)
[![Celery](https://img.shields.io/badge/Celery-5.3.6-37814A.svg?style=flat&logo=celery&logoColor=white)](https://docs.celeryq.dev)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg?style=flat&logo=python&logoColor=white)](https://www.python.org)

Backend platform for **Alex — AI Knowledge & Research Assistant**, built with **FastAPI**, **LangChain / LangGraph**, **Celery**, **Redis**, and **PostgreSQL**.

---

## 📁 Repository Structure

```text
alex/
├── app/
│   ├── api/                    # FastAPI routes, schemas, and main entry
│   │   ├── main.py
│   │   ├── schemas.py
│   │   └── v1/
│   │       ├── endpoints/
│   │       └── router.py
│   ├── agents/                 # LangGraph agents directory
│   ├── core/                   # DB, LLM integration, Celery, and Config settings
│   │   ├── db.py
│   │   ├── llm.py
│   │   ├── celery_app.py
│   │   └── config.py
│   ├── models/                 # Database models directory
│   ├── services/               # Alex services (document processing, RAG, search, reports)
│   └── tasks/                  # Celery background tasks
├── tests/                      # Automated test suite (Pytest)
├── docker-compose.yml          # Container orchestration (FastAPI, Postgres, Redis, Celery)
├── Dockerfile                  # Production container build definition
├── requirements.txt            # Python dependencies
└── .env.example                # Environment variable template
```

---

## 🚀 Quick Start Guide

### Prerequisites
* **Python**: `3.11` or higher
* **Docker & Docker Compose**: `20.10+`
* **Google Gemini API Key**: Obtainable from [Google AI Studio](https://aistudio.google.com/)

---

### Step 1: Environment Setup

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Update `.env` with your API key and database settings.

---

### Step 2: Running with Docker Compose

```bash
docker compose up --build
```

Access the API at `http://localhost:8000/docs`.
