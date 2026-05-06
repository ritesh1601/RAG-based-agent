# 📄 RAG-Based PDF Assistant
https://documentchat4u.streamlit.app/
A production-ready **Retrieval-Augmented Generation (RAG)** pipeline for querying PDF documents using natural language. Built with FastAPI, Inngest, Streamlit, and Qdrant — fully deployable on Render + Streamlit Cloud with no OpenAI dependency required.

---

## 🏗️ Architecture

```
Streamlit Cloud (UI)
        ↓
Render FastAPI (Backend)
        ↓
Inngest Cloud (Workflow Orchestration)
        ↓
Qdrant Cloud (Vector Database)
```

**PDF Upload Flow**
```
Streamlit → POST /upload → Save PDF on Render
         → Trigger rag/ingest_pdf via Inngest
         → Load → Chunk → Embed → Store in Qdrant
```

**Query Flow**
```
Streamlit → POST /query → Trigger rag/query_pdf_ai via Inngest
         → Embed question → Search Qdrant
         → Return extractive answer → Display in UI
```

---

## ✨ Features

- Upload and ingest PDF documents via a modern Streamlit dashboard
- Semantic search using sentence-transformers (no OpenAI required)
- Extractive answer mode — returns retrieved context directly
- Inngest-powered durable workflow orchestration with retries and throttling
- Qdrant Cloud vector store with configurable dimensions
- Secure backend proxy for Inngest polling (no secrets exposed in the frontend)
- Deterministic chunk UUIDs to avoid duplicate vectors on re-ingestion
- OpenAI support available as an optional drop-in for embeddings and answer generation

---

## 🧰 Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit |
| Backend API | FastAPI + Uvicorn |
| Workflow Engine | Inngest |
| Vector Database | Qdrant Cloud |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` (or OpenAI) |
| PDF Parsing | LlamaIndex (`PDFReader`, `SentenceSplitter`) |
| Deployment | Render (backend), Streamlit Cloud (frontend) |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager
- Docker (for local Qdrant)
- Node.js (for local Inngest Dev Server)

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/RAG-based-agent.git
cd RAG-based-agent
```

### 2. Install Dependencies

```bash
uv sync --frozen
```

### 3. Configure Environment

Copy the example env file and fill in your values:

```bash
cp .env.example .env
```

```env
# Inngest
INNGEST_EVENT_KEY=your_event_key
INNGEST_SIGNING_KEY=your_signing_key

# Qdrant
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your_qdrant_api_key
QDRANT_COLLECTION=docs_minilm
QDRANT_DIM=384

# Embeddings
EMBED_PROVIDER=sentence-transformers
SENTENCE_TRANSFORMER_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBED_DIM=384

# Answer generation
ANSWER_PROVIDER=extractive

# Optional: OpenAI
# OPENAI_API_KEY=sk-...
```

### 4. Start Local Qdrant (Docker)

```bash
docker run -d --name qdrantRAGdb \
  -p 6333:6333 \
  -v "$(pwd)/qdrant_storage:/qdrant/storage" \
  qdrant/qdrant
```

### 5. Start the Inngest Dev Server

```bash
npx --yes --ignore-scripts=false inngest-cli@latest dev \
  -u http://127.0.0.1:8000/api/inngest --no-discovery
```

### 6. Start the FastAPI Backend

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 7. Start the Streamlit Frontend

```bash
uv run streamlit run streamlit_app.py
```

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/upload` | Upload a PDF and trigger ingestion |
| `POST` | `/query` | Ask a question over ingested documents |
| `GET` | `/runs/{event_id}` | Poll Inngest run status (server-side proxy) |
| `POST` | `/api/inngest` | Inngest webhook handler |

### Example: Query

```bash
curl -X POST https://your-backend.onrender.com/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the main topic?", "top_k": 5}'
```

---

## ☁️ Deployment

### Render (FastAPI Backend)

| Setting | Value |
|---|---|
| Build Command | `pip install uv && uv sync --frozen` |
| Start Command | `uv run uvicorn main:app --host 0.0.0.0 --port $PORT` |

**Required environment variables on Render:**

```
INNGEST_EVENT_KEY
INNGEST_SIGNING_KEY
QDRANT_URL
QDRANT_API_KEY
QDRANT_COLLECTION=docs_minilm
QDRANT_DIM=384
EMBED_PROVIDER=sentence-transformers
SENTENCE_TRANSFORMER_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBED_DIM=384
ANSWER_PROVIDER=extractive
```

### Streamlit Cloud

Add the following to your Streamlit secrets:

```toml
FASTAPI_URL = "https://your-backend.onrender.com"
INNGEST_UI_URL = "https://app.inngest.com"
```

---

## 🔑 Inngest Cloud Setup

1. Create an account at [inngest.com](https://www.inngest.com)
2. Go to **Production environment** → **Event Keys** → create a new event key
3. Go to **Signing Key** section → copy your signing key
4. Add both to your Render environment variables
5. Register your deployed endpoint in Inngest Cloud:
   ```
   https://your-backend.onrender.com/api/inngest
   ```

---

## 🧪 Embedding Modes

| Mode | `EMBED_PROVIDER` | Requires |
|---|---|---|
| Open-source (default) | `sentence-transformers` | Nothing — runs locally |
| OpenAI | `openai` | `OPENAI_API_KEY` with credits |
| Fake (testing only) | set `USE_FAKE_EMBEDDINGS=1` | Nothing |

> ⚠️ Always use the same embedding mode for ingestion and querying. Mixing modes produces invalid results.

---

## 📁 Project Structure

```
RAG-based-agent/
├── main.py              # FastAPI app + Inngest functions
├── data_loader.py       # PDF loading, chunking, embedding
├── vector_db.py         # Qdrant client wrapper
├── custom_types.py      # Shared type definitions
├── streamlit_app.py     # Streamlit frontend
├── .env.example         # Environment variable template
├── .gitignore
└── pyproject.toml       # uv/pip dependencies
```

---

## 🔒 Security Notes

- Never commit `.env` to Git — it is listed in `.gitignore`
- The `/runs/{event_id}` endpoint proxies Inngest polling server-side so your `INNGEST_SIGNING_KEY` is never exposed to the browser or Streamlit Cloud
- Rotate any API keys that were accidentally exposed

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgements

- [LlamaIndex](https://www.llamaindex.ai/) for PDF parsing and chunking
- [Qdrant](https://qdrant.tech/) for vector storage
- [Inngest](https://www.inngest.com/) for durable workflow orchestration
- [Sentence Transformers](https://www.sbert.net/) for open-source embeddings
