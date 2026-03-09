"""
chunker.py
Splits transcript text into chunks for embedding and retrieval.

This is the most critical engineering decision in a RAG system.
Chunk too small → not enough context for Claude to answer well
Chunk too large → retrieval becomes imprecise, costs more tokens
We implement three strategies so you can compare their tradeoffs.
"""

import os
import re
from dataclasses import dataclass

@dataclass
class Chunk:
    """
    A single chunk of text with metadata attached.
    Dataclass auto-generates __init__, __repr__ etc for us.
    """
    text: str           # the actual text content of the chunk
    source: str         # which company transcript this came from e.g. "NVDA_Q4_2024"
    chunk_id: str       # unique identifier e.g. "NVDA_Q4_2024_0"
    strategy: str       # which chunking strategy was used
    char_start: int     # character position where this chunk starts in the original text
    char_end: int       # character position where this chunk ends


def chunk_by_fixed_size(
    text: str,
    source: str,
    chunk_size: int = 500,
    overlap: int = 50
) -> list[Chunk]:
    """
    STRATEGY 1: Fixed-size character chunking with overlap.

    Splits text into chunks of exactly chunk_size characters.
    Overlap means consecutive chunks share some text at their boundaries
    so context isn't lost at the seam between two chunks.

    Pros: Simple, predictable chunk sizes, easy to reason about token costs
    Cons: Cuts mid-sentence, mid-word — loses semantic meaning at boundaries

    chunk_size: how many characters per chunk (500 chars ≈ 100-125 tokens)
    overlap:    how many characters to repeat between consecutive chunks
    """
    chunks = []
    start = 0
    chunk_index = 0

    while start < len(text):
        # Calculate where this chunk ends
        end = min(start + chunk_size, len(text))

        # Extract the chunk text
        chunk_text = text[start:end].strip()

        # Only keep chunks that have meaningful content
        if chunk_text:
            chunks.append(Chunk(
                text=chunk_text,
                source=source,
                chunk_id=f"{source}_fixed_{chunk_index}",
                strategy="fixed_size",
                char_start=start,
                char_end=end
            ))
            chunk_index += 1

        # Move forward by chunk_size minus overlap
        # The overlap means we step back slightly so the next chunk
        # shares some context with the current one
        start += chunk_size - overlap

    return chunks


def chunk_by_paragraph(
    text: str,
    source: str,
    min_length: int = 100,
    max_length: int = 1500
) -> list[Chunk]:
    """
    STRATEGY 2: Paragraph-based chunking.

    Splits on double newlines (natural paragraph breaks in transcripts).
    Respects the natural structure of the document.

    Pros: Preserves semantic meaning, each chunk is a complete thought
    Cons: Uneven chunk sizes make token costs unpredictable

    min_length: discard chunks shorter than this (likely headers/noise)
    max_length: split chunks longer than this to avoid oversized chunks
    """
    chunks = []
    chunk_index = 0

    # Split on one or more blank lines — the natural paragraph separator
    paragraphs = re.split(r'\n\s*\n', text)

    for para in paragraphs:
        para = para.strip()

        # Skip paragraphs that are too short to be meaningful
        # (usually headers, speaker labels, page numbers)
        if len(para) < min_length:
            continue

        # If paragraph is too long, split it into sentences instead
        if len(para) > max_length:
            # Split on sentence boundaries
            sentences = re.split(r'(?<=[.!?])\s+', para)
            current = ""

            for sentence in sentences:
                # If adding this sentence would exceed max_length, save current chunk
                if len(current) + len(sentence) > max_length and current:
                    char_start = text.find(current)
                    chunks.append(Chunk(
                        text=current.strip(),
                        source=source,
                        chunk_id=f"{source}_para_{chunk_index}",
                        strategy="paragraph",
                        char_start=max(0, char_start),
                        char_end=max(0, char_start + len(current))
                    ))
                    chunk_index += 1
                    current = sentence
                else:
                    current += " " + sentence

            # Save any remaining text
            if current.strip():
                char_start = text.find(current)
                chunks.append(Chunk(
                    text=current.strip(),
                    source=source,
                    chunk_id=f"{source}_para_{chunk_index}",
                    strategy="paragraph",
                    char_start=max(0, char_start),
                    char_end=max(0, char_start + len(current))
                ))
                chunk_index += 1
        else:
            # Paragraph is a good size — use it as-is
            char_start = text.find(para)
            chunks.append(Chunk(
                text=para,
                source=source,
                chunk_id=f"{source}_para_{chunk_index}",
                strategy="paragraph",
                char_start=max(0, char_start),
                char_end=max(0, char_start + len(para))
            ))
            chunk_index += 1

    return chunks


def chunk_by_speaker(
    text: str,
    source: str,
    max_length: int = 1000
) -> list[Chunk]:
    """
    STRATEGY 3: Speaker-turn chunking (best for earnings call transcripts).

    Earnings calls follow a specific format:
        Speaker Name -- Title, Company
        What they said...

    This strategy splits on speaker turns so each chunk is one person
    speaking. This is the most semantically meaningful split for Q&A
    because questions like "what did Jensen Huang say about..." map
    directly to speaker-level chunks.

    Pros: Best retrieval quality for earnings calls specifically
    Cons: Only works on well-formatted transcripts with speaker labels
    """
    chunks = []
    chunk_index = 0

    # Match patterns like:
    # "Jensen Huang -- Founder and CEO"
    # "Operator"
    # "Unknown Speaker"
    speaker_pattern = re.compile(
        r'^([A-Z][a-zA-Z\s\-\.]+(?:--|—)[^\n]+|Operator|Unknown Speaker)',
        re.MULTILINE
    )

    # Find all speaker turn positions in the text
    matches = list(speaker_pattern.finditer(text))

    if len(matches) < 3:
        # Not enough speaker turns found — fall back to paragraph chunking
        # This handles cases where the transcript format is different
        print(f"  ⚠️  {source}: few speaker turns found, falling back to paragraph chunking")
        return chunk_by_paragraph(text, source, max_length=max_length)

    # Extract each speaker's full turn as a chunk
    for i, match in enumerate(matches):
        # Start of this speaker's turn
        start = match.start()

        # End is where the next speaker starts (or end of document)
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)

        chunk_text = text[start:end].strip()

        # Skip very short turns (greetings, single sentences)
        if len(chunk_text) < 50:
            continue

        # If a single speaker turn is very long, split it further
        if len(chunk_text) > max_length:
            sub_chunks = chunk_by_fixed_size(
                chunk_text, source,
                chunk_size=max_length,
                overlap=100
            )
            for j, sub in enumerate(sub_chunks):
                chunks.append(Chunk(
                    text=sub.text,
                    source=source,
                    chunk_id=f"{source}_speaker_{chunk_index}_{j}",
                    strategy="speaker",
                    char_start=start + sub.char_start,
                    char_end=start + sub.char_end
                ))
            chunk_index += 1
        else:
            chunks.append(Chunk(
                text=chunk_text,
                source=source,
                chunk_id=f"{source}_speaker_{chunk_index}",
                strategy="speaker",
                char_start=start,
                char_end=end
            ))
            chunk_index += 1

    return chunks


def load_and_chunk_all(
    transcripts_dir: str = "data/transcripts",
    strategy: str = "speaker"
) -> list[Chunk]:
    """
    Load all transcript files from disk and chunk them.

    strategy: "fixed_size" | "paragraph" | "speaker"
    Returns a flat list of all chunks across all transcripts.
    """
    all_chunks = []

    # Get all .txt files in the transcripts directory
    files = [f for f in os.listdir(transcripts_dir) if f.endswith(".txt")]

    if not files:
        raise ValueError(f"No transcript files found in {transcripts_dir}")

    print(f"Chunking {len(files)} transcripts using '{strategy}' strategy...\n")

    for filename in files:
        # The source name is the filename without .txt extension
        source = filename.replace(".txt", "")
        filepath = os.path.join(transcripts_dir, filename)

        with open(filepath) as f:
            text = f.read()

        # Choose chunking strategy based on parameter
        if strategy == "fixed_size":
            chunks = chunk_by_fixed_size(text, source)
        elif strategy == "paragraph":
            chunks = chunk_by_paragraph(text, source)
        elif strategy == "speaker":
            chunks = chunk_by_speaker(text, source)
        else:
            raise ValueError(f"Unknown strategy: {strategy}. Choose fixed_size, paragraph, or speaker")

        all_chunks.extend(chunks)
        print(f"  ✓ {source}: {len(chunks)} chunks")

    print(f"\n✅ Total chunks: {len(all_chunks)}")
    return all_chunks


if __name__ == "__main__":
    # Test all three strategies and compare results
    for strategy in ["fixed_size", "paragraph", "speaker"]:
        print(f"\n{'='*50}")
        print(f"Strategy: {strategy.upper()}")
        print('='*50)
        chunks = load_and_chunk_all(strategy=strategy)

        # Show stats
        lengths = [len(c.text) for c in chunks]
        print(f"Min chunk size:  {min(lengths)} chars")
        print(f"Max chunk size:  {max(lengths)} chars")
        print(f"Avg chunk size:  {sum(lengths)//len(lengths)} chars")

        # Show a sample chunk
        print(f"\nSample chunk from {chunks[5].source}:")
        print("-" * 40)
        print(chunks[5].text[:300] + "...")