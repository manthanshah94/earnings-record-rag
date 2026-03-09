"""
retriever.py
Searches ChromaDB for the most relevant chunks given a user query.

This is the "R" in RAG — Retrieval.
The quality of retrieval directly determines the quality of Claude's answer.
Garbage in, garbage out — if we retrieve the wrong chunks, Claude will
either hallucinate or say it doesn't know, even if the answer exists.

Key retrieval decisions:
- n_results (top-k): how many chunks to retrieve
  Too few → might miss the answer
  Too many → dilutes context, increases token cost, confuses Claude
- Filtering: narrow by company/ticker before searching for higher precision
- Score threshold: ignore chunks below a minimum similarity score
"""

import chromadb
from rag.embedder import get_chroma_client, get_or_create_collection


def retrieve(
    query: str,
    n_results: int = 5,
    ticker_filter: str = None,
    min_score: float = 0.3
) -> list[dict]:
    """
    Search ChromaDB for the most relevant chunks to a query.

    query:         the user's plain English question
    n_results:     how many chunks to return (top-k)
                   we default to 5 — enough context without overwhelming Claude
    ticker_filter: optionally restrict search to one company e.g. "NVDA"
                   improves precision when the question is company-specific
    min_score:     minimum similarity score to include a result (0 to 1)
                   ChromaDB returns cosine distance, we convert to similarity
                   0.3 means "at least somewhat relevant"

    Returns a list of dicts, each containing:
      - text:       the chunk content
      - source:     which transcript it came from
      - ticker:     company ticker
      - score:      similarity score (higher = more relevant)
      - chunk_id:   unique identifier
    """
    # Connect to the existing ChromaDB collection
    client = get_chroma_client()
    collection = get_or_create_collection(client)

    if collection.count() == 0:
        raise ValueError("Vector store is empty. Run embedder.py first.")

    # Build optional metadata filter
    # ChromaDB uses a "where" clause similar to SQL WHERE
    where_filter = None
    if ticker_filter:
        # Only search chunks from this specific company
        where_filter = {"ticker": ticker_filter.upper()}

    # Query ChromaDB — it embeds the query using the same model
    # and finds the most similar chunk vectors
    results = collection.query(
        query_texts=[query],        # ChromaDB embeds this automatically
        n_results=n_results,
        where=where_filter,         # optional company filter
        include=["documents", "metadatas", "distances"]  # what to return
    )

    # ChromaDB returns results nested in lists (supports batch queries)
    # [0] because we only sent one query
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]  # cosine distance (lower = more similar)

    # Format results and filter by minimum similarity score
    formatted = []
    for doc, meta, distance in zip(documents, metadatas, distances):
        # Convert cosine distance to similarity score
        # Distance of 0 = identical, Distance of 1 = completely different
        # So similarity = 1 - distance
        similarity = round(1 - distance, 4)

        # Skip chunks below our minimum relevance threshold
        if similarity < min_score:
            continue

        formatted.append({
            "text": doc,
            "source": meta.get("source", "unknown"),
            "ticker": meta.get("ticker", "unknown"),
            "score": similarity,
            "chunk_id": meta.get("chunk_id", "unknown"),
            "char_start": meta.get("char_start", 0),
            "char_end": meta.get("char_end", 0)
        })

    # Sort by score descending — most relevant first
    formatted.sort(key=lambda x: x["score"], reverse=True)

    return formatted


def retrieve_with_context(
    query: str,
    n_results: int = 5,
    ticker_filter: str = None
) -> str:
    """
    Retrieve chunks and format them into a single context string
    ready to be injected into Claude's prompt.

    This is what gets passed to the generator — the retrieved chunks
    formatted with clear source attribution so Claude can cite them.
    """
    chunks = retrieve(query, n_results=n_results, ticker_filter=ticker_filter)

    if not chunks:
        return "No relevant information found in the transcripts."

    # Format each chunk with its source clearly labeled
    # This is critical — Claude needs to know WHERE each piece of info came from
    # so it can cite sources in its answer rather than blending them together
    context_parts = []
    for i, chunk in enumerate(chunks):
        context_parts.append(
            f"[Source {i+1}: {chunk['source']} | Relevance: {chunk['score']}]\n"
            f"{chunk['text']}"
        )

    return "\n\n---\n\n".join(context_parts)


if __name__ == "__main__":
    # Test 1: broad query across all companies
    print("=" * 50)
    print("Test 1: Broad query — all companies")
    print("=" * 50)
    query1 = "What are executives saying about AI capital expenditure?"
    chunks = retrieve(query1, n_results=3)
    print(f"Query: {query1}")
    print(f"Found {len(chunks)} relevant chunks\n")
    for chunk in chunks:
        print(f"  [{chunk['score']}] {chunk['source']}: {chunk['text'][:150]}...")

    # Test 2: company-specific query
    print("\n" + "=" * 50)
    print("Test 2: Company-specific query — NVDA only")
    print("=" * 50)
    query2 = "What did Jensen Huang say about Blackwell demand?"
    chunks = retrieve(query2, n_results=3, ticker_filter="NVDA")
    print(f"Query: {query2}")
    print(f"Found {len(chunks)} relevant chunks\n")
    for chunk in chunks:
        print(f"  [{chunk['score']}] {chunk['source']}: {chunk['text'][:150]}...")

    # Test 3: formatted context string
    print("\n" + "=" * 50)
    print("Test 3: Formatted context string for Claude")
    print("=" * 50)
    context = retrieve_with_context(
        "How is Microsoft growing its cloud business?",
        n_results=2,
        ticker_filter="MSFT"
    )
    print(context[:600] + "...")