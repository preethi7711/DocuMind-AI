# DocuMind AI

DocuMind AI is a local-first document understanding platform for uploading PDFs, extracting document structure with OCR, indexing content into a vector database, and asking grounded questions through a RAG chat interface.

The system is designed for private document workflows: PDFs stay on the local machine, embeddings are stored in local ChromaDB, and generation runs through a local Ollama model.

## Features

- PDF upload and document tracking with FastAPI.
- OCR extraction using PaddleOCR with OpenCV preprocessing.
- Optional handwriting OCR fallback through TrOCR when explicitly enabled.
- Layout-aware chunking for downstream retrieval.
- Local embeddings through Ollama.
- Persistent vector search with ChromaDB.
- Conversational RAG answers with citations.
- React + Vite frontend for upload, document viewing, chat, citations, and debug inspection.
- SQLite persistence with SQLAlchemy.
- Structured application logging with Loguru.

## Architecture

```text
PDF upload
  -> FastAPI document API
  -> PDF rendering and image preprocessing
  -> OCR extraction
  -> Layout analysis
  -> Semantic chunking
  -> Ollama embeddings
  -> ChromaDB vector index
  -> RAG retrieval
  -> Ollama chat response with citations
  -> React frontend
```

## Tech Stack

| Layer | Technology |
| --- | --- |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS, Zustand, Axios |
| Backend | Python 3.11, FastAPI, Uvicorn |
| OCR | PaddleOCR, OpenCV, PyMuPDF |
| Embeddings | Ollama embeddings API |
| LLM | Ollama local chat model |
| Vector Store | ChromaDB |
| Database | SQLite, SQLAlchemy, aiosqlite |
| Logging | Loguru |
| Tests | Pytest |

## Project Structure

```text
DocMind-AI/
|-- backend/
|   |-- api/
|   |   |-- routes/          # FastAPI route modules
|   |   `-- schemas/         # Pydantic request and response models
|   |-- config/              # Centralized settings
|   |-- database/            # SQLAlchemy models, sessions, ChromaDB wrapper
|   |-- embeddings/          # Chunking and embedding engine
|   |-- extraction/          # Layout analysis
|   |-- ocr/                 # PaddleOCR and optional handwriting OCR
|   |-- preprocessing/       # PDF and image preprocessing
|   |-- rag/                 # Retrieval, prompts, reranking, Ollama client
|   |-- services/            # Application service layer
|   `-- utils/               # Logging and file utilities
|-- frontend/
|   |-- src/
|   |   |-- components/      # React UI components
|   |   |-- services/        # API client
|   |   |-- store/           # Zustand UI state
|   |   `-- types/           # TypeScript API types
|   `-- package.json
|-- tests/                   # Backend tests
|-- uploads/                 # Runtime PDF uploads
|-- processed/               # Runtime OCR and structured outputs
|-- chromadb/                # Runtime vector index
|-- logs/                    # Runtime logs
|-- main.py                  # ASGI application entrypoint
|-- requirements.txt         # Python dependencies
`-- .env                     # Local environment configuration
```

## Prerequisites

- Python 3.11
- Node.js and npm
- Ollama installed and running locally
- An Ollama model available for both chat and embeddings

The current local configuration uses:

```text
OLLAMA_MODEL=llama3.2:1b
EMBEDDING_MODEL=llama3.2:1b
OLLAMA_BASE_URL=http://localhost:11434
```

Start or pull the model with:

```powershell
ollama run llama3.2:1b
```

## Backend Setup

From the repository root:

```powershell
cd C:\Users\Preet\Documents\Projects\DocMind-AI
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Run the backend on port `8010`:

```powershell
.\.venv\Scripts\uvicorn.exe main:app --host 127.0.0.1 --port 8010
```

Health check:

```text
http://127.0.0.1:8010/api/v1/health
```

API docs:

```text
http://127.0.0.1:8010/docs
```

The frontend API client is currently configured to call `http://localhost:8010/api/v1`.

## Frontend Setup

Open a second terminal:

```powershell
cd C:\Users\Preet\Documents\Projects\DocMind-AI\frontend
npm install
npm run dev
```

Open the Vite URL printed in the terminal, usually one of:

```text
http://localhost:5173
http://localhost:5174
```

Both origins are allowed in `.env` for local CORS.

## Running Tests

Backend tests:

```powershell
cd C:\Users\Preet\Documents\Projects\DocMind-AI
.\.venv\Scripts\python.exe -m pytest tests -v
```

Frontend production build:

```powershell
cd C:\Users\Preet\Documents\Projects\DocMind-AI\frontend
npm run build
```

## API Overview

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/api/v1/health` | Service health check |
| GET | `/api/v1/documents` | List uploaded documents |
| POST | `/api/v1/documents/upload` | Upload a PDF and start ingestion |
| GET | `/api/v1/documents/{document_id}` | Get document metadata and status |
| GET | `/api/v1/documents/{document_id}/pdf` | Serve the uploaded PDF inline |
| POST | `/api/v1/ocr/process/{document_id}` | Run OCR manually for a document |
| POST | `/api/v1/chat` | Ask a grounded RAG question |

## Configuration

Settings are loaded from `.env` through `backend/config/settings.py`.

Important settings:

| Setting | Purpose |
| --- | --- |
| `HOST`, `PORT` | Backend host and default app port |
| `CORS_ORIGINS` | Allowed frontend development origins |
| `DATABASE_URL` | SQLite database URL |
| `CHROMADB_DIR` | ChromaDB persistence directory |
| `CHROMA_COLLECTION_NAME` | Active vector collection name |
| `OLLAMA_BASE_URL` | Local Ollama API URL |
| `OLLAMA_MODEL` | Chat model |
| `EMBEDDING_MODEL` | Embedding model |
| `ENABLE_HANDWRITING_OCR` | Optional TrOCR handwriting fallback |
| `OCR_USE_GPU` | PaddleOCR GPU toggle |

## Operational Notes

- ChromaDB collections are tied to the embedding vector dimension. If the embedding model changes, the application recreates the active collection when it detects a dimension mismatch.
- Handwriting OCR is disabled by default to avoid slow model downloads during local document ingestion. Enable it only after the TrOCR model is available locally.
- If port `8000` is occupied, use `8010` for the backend and keep the frontend API base URL aligned with that port.
- Uploaded documents and generated runtime files are stored locally under `uploads/`, `processed/`, `chromadb/`, and `logs/`.

## Development Standards

- Keep API responses wrapped in the standard envelope: `success`, `message`, and `data`.
- Keep backend routes versioned under `/api/v1`.
- Load configuration through the centralized settings module.
- Prefer local-first behavior and avoid sending document content to external services.
- Run backend tests and the frontend build before handing off user-facing changes.
"# DocuMind-AI" 
