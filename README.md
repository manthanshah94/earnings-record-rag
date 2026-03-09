# The Earnings Record

A RAG (Retrieval-Augmented Generation) application for querying Q4 2024 earnings call transcripts from five major tech companies. Styled as a broadsheet newspaper.

## What it does

Ask natural language questions about earnings calls and get grounded answers with cited sources. Every answer is backed by exact transcript text — Claude never uses outside knowledge.

**Companies covered:** NVDA · AAPL · MSFT · AMZN · META (Q4 2024)

## Features

- **Ask** — ask any question across all transcripts, get a cited answer
- **Compare** — ask the same question across multiple companies side by side
- **Explore** — inspect raw retrieved chunks to see exactly what Claude sees before generation

## Tech stack

| Layer | Technology |
|---|---|
| UI | Streamlit (newspaper theme) |
| Chunking | Speaker-turn (with fixed-size and paragraph fallbacks) |
| Embeddings | `all-MiniLM-L6-v2` via sentence-transformers (local, free) |
| Vector DB | ChromaDB (persistent on disk) |
| Generator | Claude Haiku (`claude-haiku-4-5`) via Anthropic API |

## Project structure

```
├── app.py                  # Streamlit UI
├── rag/
│   ├── chunker.py          # 3 chunking strategies: fixed_size, paragraph, speaker
│   ├── embedder.py         # Embed chunks into ChromaDB
│   ├── retriever.py        # Semantic search with score threshold + ticker filtering
│   └── generator.py        # RAG pipeline: retrieve → generate → cite
├── data/
│   ├── fetch_transcripts.py
│   └── transcripts/        # Raw .txt earnings call transcripts
├── chroma_db/              # Persistent vector store (auto-created)
└── .streamlit/config.toml  # Theme config
```

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/manthanshah94/earnings-record-rag.git
cd earnings-record-rag
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate      # macOS/Linux
venv\Scripts\activate         # Windows
```

### 3. Install dependencies

```bash
pip install streamlit anthropic chromadb sentence-transformers
```

### 4. Set your Anthropic API key

```bash
export ANTHROPIC_API_KEY=your_key_here
```

### 5. Build the vector store (first run only)

```bash
python -m rag.embedder
```

This downloads the MiniLM model (~80MB) and embeds all transcripts into ChromaDB. Only needs to run once.

### 6. Launch the app

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501).

## How RAG works here

```
User question
     │
     ▼
Embed query with MiniLM-L6-v2
     │
     ▼
ChromaDB cosine similarity search (top-k chunks)
     │
     ▼
Filter by score threshold (≥ 0.3) + optional ticker filter
     │
     ▼
Format chunks as numbered sources → inject into Claude prompt
     │
     ▼
Claude Haiku generates grounded answer with [Source N] citations
```

## Chunking strategies

The app uses **speaker-turn chunking** by default — each chunk is one person's full statement during the call. This maps naturally to questions like "what did the CEO say about margins?"

Two fallback strategies are also implemented:
- **Paragraph** — splits on double newlines, respects document structure
- **Fixed-size** — 500-character windows with 50-character overlap

## License

MIT
