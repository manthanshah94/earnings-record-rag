"""
generator.py
Takes retrieved chunks and generates a grounded answer using Claude API.

This is the "G" in RAG — Generation.
The key principle: Claude only answers using the retrieved context.
It never uses its own training knowledge about these companies.
This eliminates hallucination and makes every answer verifiable.

The prompt engineering here is critical:
- Tell Claude exactly what it can and cannot do
- Force it to cite sources by chunk number
- Tell it to say "I don't know" if the answer isn't in the context
"""

import os
import anthropic
from rag.retriever import retrieve, retrieve_with_context

# Initialize Claude client
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
MODEL = "claude-haiku-4-5"


def generate_answer(
    query: str,
    context: str,
    chunks: list[dict]
) -> dict:
    """
    Generate a grounded answer from retrieved context using Claude.

    query:   the user's original question
    context: formatted string of retrieved chunks from retrieve_with_context()
    chunks:  raw list of chunk dicts for citation building

    Returns a dict with:
      - answer:    Claude's plain English answer
      - citations: list of sources used
      - query:     original question
    """

    # This is the core RAG prompt
    # Three rules force grounded, verifiable answers:
    # 1. Only use provided context — no training knowledge
    # 2. Always cite which source each claim comes from
    # 3. Admit uncertainty rather than guess
    prompt = f"""You are a financial analyst assistant with access to earnings call transcripts.

Answer the user's question using ONLY the information provided in the context below.
Do not use any outside knowledge. If the answer is not in the context, say "I couldn't find that in the available transcripts."

For each claim you make, cite the source using [Source N] notation.
Be specific with numbers, quotes, and names when they appear in the context.
Keep your answer concise — 3 to 5 sentences maximum.

Context from earnings call transcripts:
{context}

Question: {query}

Answer:"""

    message = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )

    answer = message.content[0].text.strip()

    # Build citation list from the chunks that were retrieved
    # This lets the UI show clickable source references
    citations = []
    for i, chunk in enumerate(chunks):
        citations.append({
            "number": i + 1,
            "source": chunk["source"],
            "ticker": chunk["ticker"],
            "score": chunk["score"],
            "preview": chunk["text"][:150] + "..."
        })

    return {
        "query": query,
        "answer": answer,
        "citations": citations
    }


def ask(
    query: str,
    n_results: int = 5,
    ticker_filter: str = None
) -> dict:
    """
    Full RAG pipeline in one function:
    query → retrieve → generate → return answer with citations

    This is the single function the Streamlit UI calls.

    query:         user's plain English question
    n_results:     how many chunks to retrieve (top-k)
    ticker_filter: optionally restrict to one company
    """
    # Step 1 — Retrieve relevant chunks from ChromaDB
    chunks = retrieve(
        query,
        n_results=n_results,
        ticker_filter=ticker_filter
    )

    # If nothing was retrieved, return early with a clear message
    if not chunks:
        return {
            "query": query,
            "answer": "I couldn't find relevant information in the transcripts for that question.",
            "citations": []
        }

    # Step 2 — Format chunks into a context string for Claude
    context = retrieve_with_context(
        query,
        n_results=n_results,
        ticker_filter=ticker_filter
    )

    # Step 3 — Generate grounded answer using Claude
    result = generate_answer(query, context, chunks)

    return result


def compare_companies(query: str, tickers: list[str] = None) -> dict:
    """
    Ask the same question across multiple companies and compare answers.
    Useful for cross-company analysis e.g.
    "How is each company thinking about AI investment?"

    tickers: list of tickers to compare e.g. ["NVDA", "MSFT", "META"]
             defaults to all 5 companies if not specified
    """
    if tickers is None:
        tickers = ["NVDA", "AAPL", "MSFT", "AMZN", "META"]

    results = {}
    for ticker in tickers:
        result = ask(query, n_results=3, ticker_filter=ticker)
        results[ticker] = result

    return results


if __name__ == "__main__":
    # Test 1: single question, all companies
    print("=" * 60)
    print("Test 1: Single question across all companies")
    print("=" * 60)
    result = ask("What risks and challenges did management discuss?", n_results=8)
    print(f"Q: {result['query']}")
    print(f"\nA: {result['answer']}")
    print(f"\nSources used:")
    for c in result["citations"]:
        print(f"  [{c['number']}] {c['source']} (relevance: {c['score']})")

    # Test 2: company-specific question
    print("\n" + "=" * 60)
    print("Test 2: Company-specific question")
    print("=" * 60)
    result = ask(
        "What did management say about revenue guidance?",
        n_results=3,
        ticker_filter="MSFT"
    )
    print(f"Q: {result['query']} [MSFT only]")
    print(f"\nA: {result['answer']}")

    # Test 3: cross-company comparison
    print("\n" + "=" * 60)
    print("Test 3: Cross-company AI investment comparison")
    print("=" * 60)
    comparison = compare_companies(
    "What AI investments and capital expenditure did the company announce?",
    tickers=["NVDA", "MSFT", "META"]
    )
    for ticker, result in comparison.items():
        print(f"\n{ticker}:")
        print(f"  {result['answer'][:200]}...")