---
title: AI Service Skripsi
emoji: 🐠
colorFrom: yellow
colorTo: green
sdk: gradio
sdk_version: 4.44.0
python_version: "3.10"
app_file: app.py
app_port: 7860
pinned: false
short_description: Layanan AI untuk skripsi
---

<div align="center">

# 🤖 Klipin AI Service - FastAPI & Machine Learning Microservice
> **Official AI Microservice for Kurikulum Merdeka Classification & LLM Summarization**

[![English](https://img.shields.io/badge/Language-English-red.svg)](README.md)
[![Bahasa Indonesia](https://img.shields.io/badge/Language-Bahasa_Indonesia-blue.svg)](README.id.md)

</div>

---

Welcome to the **AI Service Repository** of **Klipin - Smart Reference & Literature Research System**. This Python FastAPI microservice powers literature search integration (Google Scholar), **45-Class Kurikulum Merdeka Machine Learning Topic Classification**, automated PDF text extraction, and LLM text summarization.

It runs as a Hugging Face Docker/ZeroGPU Space and is consumed by the Klipin Core Backend at `/ai/search` and `/ai/summarize`.

---

## ✨ Key AI Capabilities

- **🔍 Google Scholar Crawling**: Crawls academic papers via SerpAPI with intelligent query similarity caching.
- **🧬 LaBSE Feature Extraction**: Encodes paper titles & abstracts into 768-dimensional dense vector embeddings using `sentence-transformers/LaBSE`.
- **🎯 Multi-Model Ensemble Classification**: Evaluates paper embeddings simultaneously across 4 algorithms (**KNN**, **SVM**, **Logistic Regression**, **Random Forest**) to predict subject (`Biology`, `Physics`, `Chemistry`, `Math`, `IPA`, `IPS`) and level (`SMA`, `SMP`, `SD`).
- **📄 PDF Auto-Discovery & Extraction**: Automatically locates direct PDF links (including OJS publisher sites) and parses full-text & references using `PyMuPDF` (`fitz`).
- **🧠 LLM Summarization Engine**: Synthesizes and translates papers into formal Indonesian structured JSON schemas via **Groq Cloud API** running **OpenAI GPT-OSS 20B**.
- **⚡ ZeroGPU & CPU Resilient**: Compatible with Hugging Face ZeroGPU Spaces (`@spaces.GPU`) and CPU fallback execution.

---

## 🧠 Summarization Model

Summarization runs on **Groq** with `openai/gpt-oss-20b` as the default model. This replaced the earlier
**LLaMA 3.3 70B Versatile** setup, which is no longer used anywhere in the codebase.

| Setting | Value | Why |
| :--- | :--- | :--- |
| Provider | Groq Cloud API (`/openai/v1/chat/completions`) | OpenAI-compatible, free tier |
| Model default | `openai/gpt-oss-20b` | Override with the `GROQ_MODEL` env var |
| `reasoning_effort` | `low` | gpt-oss spends hidden tokens on reasoning before answering; `low` keeps cost down |
| `max_tokens` | `1300` | Enough for the structured summary without truncating the bibliography |
| Context budget | ~1000 words body + ~200 words references | Long PDFs are trimmed before the call |
| Caching | Per article URL | Repeat requests for the same paper skip the model entirely |
| Retry | On HTTP 429 and truncated completions | Groq free tier is rate limited; a truncated reply is retried once |

Because the response is a strict JSON schema, the model is instructed to emit `judul`, `identitas`, `author`,
`kompetensi`, `isi_materi`, `temuan`, `kesimpulan`, and `daftar_pustaka`. Any of these is guaranteed to exist in
the response even when the model leaves one blank.

> **Note on titles.** gpt-oss frequently returns an empty `judul`. When that happens the service fills the title
> from the PDF's own first page (`_document_title`) instead of leaving the UI header blank.

---

## 🛠️ Tech Stack

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) `0.115.6`, `uvicorn[standard]`
- **Machine Learning & NLP**: PyTorch, `sentence-transformers`, `scikit-learn`, `joblib`, `numpy`
- **Document Processing**: `PyMuPDF` (`fitz`), `beautifulsoup4`, `requests`, `httpx`
- **LLM Integration**: Groq Cloud API (`openai/gpt-oss-20b`)
- **Database & ORM**: PostgreSQL (Supabase), `SQLAlchemy`, `psycopg2-binary`
- **Space UI**: Gradio `4.44.0`, `spaces` (ZeroGPU decorators)

### ⚠️ Pinned dependencies

Some pins are load-bearing and should not be bumped casually:

- **`fastapi==0.115.6` / `starlette==0.41.3`** — with newer releases,
  `APIRouter.include_router()` silently registers **no routes**, so `/ai/search` and `/ai/summarize` vanish
  from the app with no error at startup.
- **`transformers<5` / `huggingface_hub<1.0` / `gradio==4.44.0`** — Gradio 4.44 imports `HfFolder`, which was
  removed in `huggingface_hub >= 1.0`. Transformers 5 requires `huggingface_hub >= 2.x`, so the whole chain
  stays on 4.x.
- **`scikit-learn<2`** — the classifiers in `src/models/*.pkl` were pickled with scikit-learn 1.7.x.

---

## ⚙️ Environment Setup & Installation

### 1. Prerequisites
- **Python** v3.10.x or v3.11.x
- **pip** and `venv`

### 2. Installation Steps
```bash
# Clone repository
git clone https://github.com/AI-Research-TS/Ai-Services.git
cd Ai-Services

# Create & activate virtual environment
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Variables Configuration
Create a `.env` file in the root directory. See `.env.example` for the full list:

```env
# External APIs
SERPAPI_KEY=your_serpapi_key_here
GROQ_API_KEY=your_groq_api_key_here

# Optional: override the summarization model
# GROQ_MODEL=openai/gpt-oss-20b

# Database (Supabase connection pooler)
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=your_db_host
DB_NAME=your_db_name
DB_PORT=6543

# Query similarity cache
SIMILARITY_THRESHOLD=0.85
```

### 4. Start Development Server
```bash
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```
The server will start at: **`http://127.0.0.1:8000`**

Environment variables are guarded by a config check — a missing `GROQ_API_KEY` or `SERPAPI_KEY` fails loudly at
startup instead of at the first request.

---

## 🔗 Main API Endpoints

Mounted under the `/ai` prefix, plus a root health check:

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `GET /health` | `GET` | Lightweight health check (`{"status": "ok"}`). Does not touch the model or the DB. |
| `POST /ai/search` | `POST` | Crawls papers via SerpAPI, embeds via LaBSE, and classifies topic & level. |
| `POST /ai/summarize` | `POST` | Discovers the article PDF, extracts text, and generates a GPT-OSS summary. |

> The root path `/` serves a Gradio playground. `/health` is the endpoint to probe from infrastructure — it
> answers immediately even while the ensemble models or the database are still warming up.

### Startup behavior

Heavy work is deliberately kept off the critical path so the Space reports healthy right away:

- **ZeroGPU handshake** runs in the `startup` hook, because the app serves Gradio through
  `gr.mount_gradio_app` + `uvicorn` and never calls `launch()` — without it the Space fails with
  *"No @spaces.GPU function detected during startup"*.
- **Database auto-migration** runs in a daemon thread. It used to run at import time, which blocked the port
  from binding until Supabase answered.

---

## ☁️ Deployment

The service is deployed to a Hugging Face Space. Two things must be set in **Space → Settings → Variables and
secrets**: `GROQ_API_KEY` and `SERPAPI_KEY` (secrets), plus the `DB_*` variables.

```bash
# Push to the Space remote (configured as `hf` locally)
git push hf main
```

---

## 👥 Organization

Part of **AI-Research-TS** — Klipin Smart Reference & Literature Research System.

| Repository | Role |
| :--- | :--- |
| [Frontend](https://github.com/AI-Research-TS/Frontend) | Next.js web application |
| [Backend](https://github.com/AI-Research-TS/Backend) | Express.js API gateway |
| [Ai-Services](https://github.com/AI-Research-TS/Ai-Services) | FastAPI ML & LLM microservice (this repo) |
