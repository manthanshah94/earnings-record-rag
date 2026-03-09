"""
embedder.py
Converts text chunks into vector embeddings and stores them in ChromaDB.

What is an embedding?
A vector embedding is a list of numbers (e.g. 384 numbers) that represents
the semantic meaning of a piece of text. Text with similar meaning will have
similar vectors — this is what makes semantic search possible.

Example:
"Jensen Huang discussed Blackwell chip demand"  → [0.23, -0.14, 0.87, ...]
"NVIDIA CEO talked about GPU supply"            → [0.21, -0.12, 0.85, ...]
These two vectors are close together even though the words are different.

What is ChromaDB?
A vector database — it stores embeddings and lets you search for the
most similar ones to a query. Think of it as DuckDB but for vectors.
"""

import os
import chromadb
from chromadb.utils import embedding_functions
from rag.chunker import load_and_chunk_all, Chunk

# Where ChromaDB will persist its data on disk
# This means embeddings survive between sessions — we don't re-embed every run
CHROMA_DB_PATH = "chroma_db"

# The embedding model we're using
# all-MiniLM-L6-v2 is a lightweight but high quality open source model
# 384 dimensions, runs locally for free, no API key needed
# Downloads automatically on first run (~80MB)
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Name of our collection inside ChromaDB
# A collection is like a table — it holds all our chunks + their embeddings
COLLECTION_NAME = "earnings_transcripts"


def get_chroma_client() -> chromadb.PersistentClient:
    """
    Create a ChromaDB client that saves data to disk.
    PersistentClient means data survives between Python sessions.
    """
    return chromadb.PersistentClient(path=CHROMA_DB_PATH)


def get_or_create_collection(client: chromadb.PersistentClient):
    """
    Get existing collection or create a new one.

    We attach a SentenceTransformerEmbeddingFunction to the collection.
    This means ChromaDB will automatically embed any text we add or query
    using our chosen model — we never call the embedding model directly.
    """
    # This embedding function wraps sentence-transformers
    # ChromaDB calls it automatically whenever we add or query documents
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )

    # get_or_create means: return existing collection if it exists,
    # otherwise create a fresh one
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"}  # use cosine similarity for search
    )
    return collection


def embed_and_store(
    chunks: list[Chunk],
    collection,
    batch_size: int = 50
) -> None:
    """
    Embed all chunks and store them in ChromaDB.

    We process in batches of 50 to avoid memory issues with large corpora.
    ChromaDB handles deduplication — if a chunk_id already exists it skips it.

    chunks:     list of Chunk objects from chunker.py
    collection: ChromaDB collection to store into
    batch_size: how many chunks to embed at once
    """
    # Check how many chunks are already stored
    existing_count = collection.count()
    if existing_count > 0:
        print(f"  Collection already has {existing_count} chunks — skipping re-embedding")
        print(f"  Delete '{CHROMA_DB_PATH}' folder to force re-embed")
        return

    print(f"  Embedding {len(chunks)} chunks in batches of {batch_size}...")
    print(f"  Model: {EMBEDDING_MODEL}")
    print(f"  This may take a minute on first run (downloading model)...\n")

    total_stored = 0

    # Process chunks in batches
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i: i + batch_size]

        # ChromaDB expects three parallel lists:
        # documents — the actual text to embed
        # ids       — unique identifier for each chunk
        # metadatas — dict of metadata attached to each chunk (for filtering)
        documents = [c.text for c in batch]
        ids = [c.chunk_id for c in batch]
        metadatas = [
            {
                "source": c.source,         # e.g. "NVDA_Q4_2024"
                "strategy": c.strategy,     # e.g. "speaker"
                "char_start": c.char_start,
                "char_end": c.char_end,
                # Extract company ticker from source name e.g. "NVDA" from "NVDA_Q4_2024"
                "ticker": c.source.split("_")[0]
            }
            for c in batch
        ]

        # Add to ChromaDB — it automatically calls the embedding function
        # and stores both the text and its vector representation
        collection.add(
            documents=documents,
            ids=ids,
            metadatas=metadatas
        )

        total_stored += len(batch)
        print(f"  Stored {total_stored}/{len(chunks)} chunks...")

    print(f"\n✅ Successfully embedded and stored {total_stored} chunks")


def build_vector_store(strategy: str = "speaker") -> tuple:
    """
    Full pipeline: load transcripts → chunk → embed → store in ChromaDB.
    Returns the client and collection for immediate use.
    """
    print("Building vector store...\n")

    # Step 1: Load and chunk all transcripts
    chunks = load_and_chunk_all(strategy=strategy)

    # Step 2: Connect to ChromaDB
    client = get_chroma_client()
    collection = get_or_create_collection(client)

    # Step 3: Embed and store
    print(f"\nStoring in ChromaDB at '{CHROMA_DB_PATH}'...")
    embed_and_store(chunks, collection)

    print(f"\n📊 Collection stats:")
    print(f"  Total vectors stored: {collection.count()}")

    return client, collection


if __name__ == "__main__":
    client, collection = build_vector_store(strategy="speaker")

    # Quick sanity check — query the vector store with a test question
    print("\n🔍 Test query: 'What did management say about AI infrastructure spending?'")
    results = collection.query(
        query_texts=["What did management say about AI infrastructure spending?"],
        n_results=3  # return top 3 most similar chunks
    )

    print("\nTop 3 most relevant chunks:")
    for i, (doc, meta) in enumerate(zip(
        results["documents"][0],
        results["metadatas"][0]
    )):
        print(f"\n--- Result {i+1} [{meta['source']}] ---")
        print(doc[:300] + "...")