"""
fetch_transcripts.py
Downloads real earnings call transcripts from Motley Fool (free, public)
Covers Q4 2024 earnings for major companies
"""
import requests        # makes HTTP requests to fetch web pages
from bs4 import BeautifulSoup  # parses HTML and extracts text
import os              # file system operations (check if file exists, save files)
import time            # adds delays between requests so we don't overwhelm the server

# Dictionary mapping a friendly name to the URL of each transcript
# Key = what we'll call the file locally
# Value = the public URL on Motley Fool where the transcript lives
TRANSCRIPTS = {
    "NVDA_Q4_2024": "https://www.fool.com/earnings/call-transcripts/2025/02/26/nvidia-nvda-q4-2025-earnings-call-transcript/",
    "AAPL_Q4_2024": "https://www.fool.com/earnings/call-transcripts/2025/01/30/apple-aapl-q1-2025-earnings-call-transcript/",
    "MSFT_Q4_2024": "https://www.fool.com/earnings/call-transcripts/2025/01/29/microsoft-msft-q2-2025-earnings-call-transcript/",
    "AMZN_Q4_2024": "https://www.fool.com/earnings/call-transcripts/2025/02/06/amazoncom-amzn-q4-2024-earnings-call-transcript/",
    "META_Q4_2024": "https://www.fool.com/earnings/call-transcripts/2025/01/29/meta-platforms-meta-q4-2024-earnings-call-transcri/",
}

# Browser-style headers so the website doesn't block our request
# Some websites reject requests that don't look like they come from a real browser
# This header mimics a Chrome browser on a Mac
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

def fetch_transcript(name: str, url: str, save_dir: str = "data/transcripts") -> str:
    """
    Fetch and save a single transcript
    
    name     — friendly label e.g. "NVDA_Q4_2024"
    url      — the Motley Fool page to scrape
    save_dir — folder where transcript text files are saved
    returns  — the full transcript text as a string
    """

    # Build the full file path e.g. "data/transcripts/NVDA_Q4_2024.txt"
    filepath = os.path.join(save_dir, f"{name}.txt")

    # If we already downloaded this transcript before, just read it from disk
    # This avoids re-fetching every time you run the script
    if os.path.exists(filepath):
        print(f"  ✓ {name} already exists, skipping")
        with open(filepath) as f:
            return f.read()

    print(f"  Fetching {name}...")
    try:
        # Make the HTTP GET request to the URL
        # timeout=15 means give up if the server doesn't respond in 15 seconds
        response = requests.get(url, headers=HEADERS, timeout=15)

        # Raise an error if the server returned a bad status (404, 500 etc)
        response.raise_for_status()

        # Parse the raw HTML into a navigable tree structure
        soup = BeautifulSoup(response.text, "html.parser")

        # Try multiple CSS selectors to find the main article content
        # Motley Fool has changed their HTML structure over time
        # so we try three different approaches in order
        # Try Motley Fool's current HTML structure
        content = soup.find("div", class_="transcript-content")
        if not content:
            content = soup.find("div", class_="article-body")

        # If none of the selectors found anything, give up on this transcript
        if not content:
            print(f"  ✗ Could not parse {name}")
            return ""

        # Extract plain text from the HTML
        # separator="\n" puts each HTML element on its own line
        text = content.get_text(separator="\n")

        # Clean up the text:
        # 1. Split into individual lines
        # 2. Strip leading/trailing whitespace from each line
        # 3. Drop empty lines
        lines = [l.strip() for l in text.split("\n") if l.strip()]

        # Rejoin the cleaned lines back into one block of text
        clean_text = "\n".join(lines)

        # Add a metadata header at the top of the file
        # This helps Claude know which company and source each chunk came from
        full_text = f"COMPANY: {name}\nSOURCE: {url}\n\n{clean_text}"

        # Save to disk so we don't have to re-fetch next time
        with open(filepath, "w") as f:
            f.write(full_text)

        print(f"  ✓ {name} saved ({len(clean_text)} chars)")
        return full_text

    except Exception as e:
        # Catch any error (network failure, parse error, etc) and log it
        # We don't crash the whole script just because one transcript failed
        print(f"  ✗ {name}: {e}")
        return ""


def fetch_all_transcripts():
    """
    Loop through all transcripts in the TRANSCRIPTS dictionary
    and fetch each one
    """
    print(f"Fetching {len(TRANSCRIPTS)} earnings call transcripts...\n")

    results = {}  # stores name → transcript text for all companies

    for name, url in TRANSCRIPTS.items():
        results[name] = fetch_transcript(name, url)

        # Wait 1 second between requests
        # This is called "rate limiting" — being polite to the server
        # Sending too many requests too fast can get your IP blocked
        time.sleep(1)

    # Count how many succeeded (non-empty strings are truthy in Python)
    success = sum(1 for v in results.values() if v)
    print(f"\n✅ {success}/{len(TRANSCRIPTS)} transcripts fetched")
    return results


# Only run fetch_all_transcripts() when this file is executed directly
# If another file imports from this module, it won't auto-run
if __name__ == "__main__":
    fetch_all_transcripts()