import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from rag.generator import ask, compare_companies
from rag.retriever import retrieve

st.set_page_config(
    page_title="The Earnings Record",
    page_icon="📰",
    layout="wide"
)
st.markdown("""
<style>
    [data-testid="stSidebarCollapsedControl"] { display: none !important; }
    [data-testid="stSidebar"] { min-width: 260px !important; width: 260px !important; }
</style>
""", unsafe_allow_html=True)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;0,900;1,700&family=IBM+Plex+Mono:wght@300;400;500&family=Libre+Baskerville:ital@0;1&display=swap');

:root {
    --ink:     #1a1a1a;
    --paper:   #F5F0E8;
    --cream:   #EDE8DC;
    --rule:    #1a1a1a;
    --ghost:   #9a9080;
    --accent:  #C8102E;
}

html, body, [class*="css"] {
    background: var(--paper) !important;
    color: var(--ink);
}
.main, .block-container {
    background: var(--paper) !important;
    padding: 0 2rem 2rem 2rem !important;
    max-width: 1200px !important;
}
#MainMenu, footer, header { visibility: hidden; }

/* ── MASTHEAD ── */
.masthead-wrap {
    border-top: 6px double var(--ink);
    border-bottom: 6px double var(--ink);
    text-align: center;
    padding: 1rem 0 0.8rem;
    margin-bottom: 0.3rem;
}
.masthead-date {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.62rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--ghost);
    margin-bottom: 0.3rem;
}
.masthead-title {
    font-family: 'Playfair Display', serif;
    font-size: 3.8rem;
    font-weight: 900;
    line-height: 1;
    letter-spacing: -0.02em;
    color: var(--ink);
    margin: 0;
}
.masthead-title span { color: var(--accent); }
.masthead-sub {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.62rem;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--ghost);
    margin-top: 0.4rem;
    border-top: 1px solid var(--ghost);
    padding-top: 0.3rem;
}

/* ── SECTION RULES ── */
.section-rule {
    border: none;
    border-top: 2px solid var(--ink);
    margin: 1.2rem 0 0.4rem;
}
.section-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.6rem;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--ghost);
    margin-bottom: 0.8rem;
}

/* ── EXAMPLE BUTTONS ── */
.stButton > button {
    background: transparent !important;
    color: var(--ink) !important;
    border: 1px solid #bbb !important;
    border-radius: 0 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.7rem !important;
    padding: 0.35rem 0.7rem !important;
    transition: all 0.1s !important;
    text-align: left !important;
}
.stButton > button:hover {
    background: var(--ink) !important;
    color: var(--paper) !important;
    border-color: var(--ink) !important;
}

/* ── TEXT INPUT ── */
.stTextInput > div > div > input {
    border-radius: 0 !important;
    border: none !important;
    border-bottom: 2px solid var(--ink) !important;
    background: transparent !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.9rem !important;
    color: var(--ink) !important;
    padding: 0.5rem 0.2rem !important;
    box-shadow: none !important;
}

/* ── ANSWER BLOCK ── */
.answer-wrap {
    display: grid;
    grid-template-columns: 4px 1fr;
    gap: 0 1.2rem;
    margin: 1rem 0 1.5rem;
}
.answer-rule { background: var(--accent); }
.answer-text {
    font-family: 'Libre Baskerville', serif;
    font-size: 0.95rem;
    line-height: 2;
    color: var(--ink);
}
.answer-text b { font-style: italic; }

/* ── CITATIONS ── */
.cit-table { width: 100%; border-collapse: collapse; margin-top: 0.5rem; }
.cit-table tr { border-bottom: 1px solid #ddd8cc; }
.cit-table td {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem;
    color: var(--ghost);
    padding: 0.45rem 0.5rem;
    vertical-align: top;
}
.cit-table td:first-child {
    color: var(--accent);
    font-weight: 500;
    width: 24px;
}
.cit-table td:nth-child(2) { color: var(--ink); font-weight: 500; width: 130px; }
.cit-table td:nth-child(3) { width: 50px; }

/* ── COMPANY BLOCK ── */
.co-block {
    border-top: 2px solid var(--ink);
    padding: 1rem 0 1.2rem;
    margin-bottom: 0.5rem;
    display: grid;
    grid-template-columns: 80px 1fr;
    gap: 0 1.5rem;
}
.co-ticker {
    font-family: 'Playfair Display', serif;
    font-size: 1.6rem;
    font-weight: 700;
    color: var(--ink);
    line-height: 1.1;
    padding-top: 0.15rem;
}
.co-answer {
    font-family: 'Libre Baskerville', serif;
    font-size: 0.88rem;
    line-height: 1.85;
    color: #2a2a2a;
}

/* ── CHUNK CARD ── */
.chunk-pill {
    display: inline-block;
    background: var(--ink);
    color: var(--paper);
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.65rem;
    padding: 2px 8px;
    margin-right: 6px;
    letter-spacing: 0.05em;
}

/* ── TABS ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0 !important;
    border-bottom: 2px solid var(--ink) !important;
    background: transparent !important;
}
.stTabs [data-baseweb="tab"] {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.65rem !important;
    letter-spacing: 0.18em !important;
    text-transform: uppercase !important;
    color: var(--ghost) !important;
    border-radius: 0 !important;
    padding: 0.5rem 1.4rem !important;
    background: transparent !important;
    border: none !important;
}
.stTabs [aria-selected="true"] {
    color: var(--ink) !important;
    border-bottom: 3px solid var(--accent) !important;
    font-weight: 500 !important;
}

/* ── SIDEBAR ── */
[data-testid="stSidebar"] {
    background: var(--cream) !important;
    border-right: 1px solid #ccc8bc !important;
}
[data-testid="stSidebar"] .section-label { margin-top: 0.5rem; }

/* ── SLIDER ── */
.stSlider [data-baseweb="slider"] div[role="slider"] {
    background: var(--ink) !important;
}

/* ── SELECTBOX ── */
.stSelectbox > div > div {
    border-radius: 0 !important;
    border-color: #bbb !important;
    background: transparent !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.78rem !important;
}
</style>
""", unsafe_allow_html=True)

# ── MASTHEAD ───────────────────────────────────────────────────────────────────
from datetime import date
today = date.today().strftime("%A, %B %-d, %Y").upper()

st.markdown(f"""
<div class="masthead-wrap">
    <div class="masthead-date">{today} &nbsp;·&nbsp; Vol. IV, No. 1 &nbsp;·&nbsp; Q4 2024 Earnings Edition</div>
    <div class="masthead-title">The Earnings <span>Record</span></div>
    <div class="masthead-sub">RAG · Claude API · ChromaDB · sentence-transformers · Streamlit &nbsp;|&nbsp; NVDA · AAPL · MSFT · AMZN · META</div>
</div>
""", unsafe_allow_html=True)

# ── SIDEBAR ────────────────────────────────────────────────────────────────────
with st.sidebar:
    # Pull live stats from the corpus
    from rag.retriever import retrieve
    from rag.embedder import get_chroma_client, get_or_create_collection

    client_db = get_chroma_client()
    col_db = get_or_create_collection(client_db)
    total_chunks = col_db.count()

    companies = {
        "NVDA": "Jensen Huang",
        "AAPL": "Tim Cook",
        "MSFT": "Satya Nadella",
        "AMZN": "Andy Jassy",
        "META": "Mark Zuckerberg"
    }

    st.markdown(f"""
    <style>
    .sidebar-masthead {{
        border-top: 3px double var(--ink);
        border-bottom: 1px solid #ccc8bc;
        text-align: center;
        padding: 0.8rem 0 0.6rem;
        margin-bottom: 1rem;
    }}
    .sidebar-title {{
        font-family: 'Playfair Display', serif;
        font-size: 1.1rem;
        font-weight: 700;
        color: var(--ink);
        letter-spacing: 0.02em;
    }}
    .sidebar-edition {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.55rem;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        color: var(--ghost);
        margin-top: 0.2rem;
    }}
    .stat-row {{
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        padding: 0.35rem 0;
        border-bottom: 1px dotted #ccc8bc;
        font-family: 'IBM Plex Mono', monospace;
    }}
    .stat-label {{
        font-size: 0.65rem;
        color: var(--ghost);
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }}
    .stat-value {{
        font-size: 0.85rem;
        font-weight: 500;
        color: var(--ink);
    }}
    .stat-accent {{
        color: var(--accent);
    }}
    .correspondent-block {{
        margin-top: 1rem;
        border-top: 2px solid var(--ink);
        padding-top: 0.6rem;
    }}
    .correspondent-head {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.55rem;
        letter-spacing: 0.2em;
        text-transform: uppercase;
        color: var(--ghost);
        margin-bottom: 0.5rem;
    }}
    .correspondent-row {{
        display: flex;
        justify-content: space-between;
        padding: 0.25rem 0;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.68rem;
        border-bottom: 1px dotted #ccc8bc;
    }}
    .correspondent-ticker {{
        font-weight: 500;
        color: var(--ink);
    }}
    .correspondent-name {{
        color: var(--ghost);
        font-style: italic;
        font-size: 0.62rem;
    }}
    .retrieval-block {{
        margin-top: 1rem;
        border-top: 2px solid var(--ink);
        padding-top: 0.6rem;
    }}
    </style>

    <div class="sidebar-masthead">
        <div class="sidebar-title">Desk Notes</div>
        <div class="sidebar-edition">Editor's briefing sheet</div>
    </div>
    """, unsafe_allow_html=True)

    # Live corpus stats
    st.markdown('<div class="section-label">Corpus at a glance</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="stat-row">
        <span class="stat-label">Transcripts</span>
        <span class="stat-value stat-accent">5</span>
    </div>
    <div class="stat-row">
        <span class="stat-label">Chunks indexed</span>
        <span class="stat-value">{total_chunks}</span>
    </div>
    <div class="stat-row">
        <span class="stat-label">Chunk strategy</span>
        <span class="stat-value">Speaker</span>
    </div>
    <div class="stat-row">
        <span class="stat-label">Embeddings</span>
        <span class="stat-value">MiniLM-L6</span>
    </div>
    <div class="stat-row">
        <span class="stat-label">Generator</span>
        <span class="stat-value">Claude Haiku</span>
    </div>
    <div class="stat-row">
        <span class="stat-label">Coverage</span>
        <span class="stat-value">Q4 2024</span>
    </div>
    """, unsafe_allow_html=True)

    # Correspondents on the ground
    st.markdown("""
    <div class="correspondent-block">
        <div class="correspondent-head">Our correspondents</div>
    """, unsafe_allow_html=True)

    for ticker, ceo in companies.items():
        st.markdown(f"""
        <div class="correspondent-row">
            <span class="correspondent-ticker">{ticker}</span>
            <span class="correspondent-name">{ceo}</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # Retrieval controls — tucked at the bottom
    st.markdown("""
    <div class="retrieval-block">
    """, unsafe_allow_html=True)
    st.markdown('<div class="section-label">Retrieval controls</div>', unsafe_allow_html=True)
    n_results = st.slider("Top-k chunks", 2, 10, 5)
    ticker_filter = st.selectbox("Company filter",
                                  ["All companies","NVDA","AAPL","MSFT","AMZN","META"])
    ticker = None if ticker_filter == "All companies" else ticker_filter
    st.markdown("</div>", unsafe_allow_html=True)

# ── TABS ───────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["ASK", "COMPARE", "EXPLORE"])

# ── TAB 1: ASK ────────────────────────────────────────────────────────────────
with tab1:
    st.markdown('<div class="section-label" style="margin-top:1rem">Every answer grounded in transcript text — sources cited inline</div>', unsafe_allow_html=True)

    examples = [
        "What risks and challenges were discussed?",
        "What did management say about AI investment?",
        "What was said about revenue guidance?",
        "How is the company thinking about margins?",
        "What did the CEO say about competition?",
        "What are the growth drivers for next year?"
    ]
    cols = st.columns(3)
    for i, ex in enumerate(examples):
        with cols[i % 3]:
            if st.button(ex, key=f"ex_{i}", use_container_width=True):
                st.session_state["question"] = ex
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    question = st.text_input("", value=st.session_state.get("question",""),
                              placeholder="Ask anything about these earnings calls...")

    if question:
        with st.spinner(""):
            result = ask(question, n_results=n_results, ticker_filter=ticker)

        st.markdown('<hr class="section-rule">', unsafe_allow_html=True)
        st.markdown('<div class="section-label">Answer</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="answer-wrap">
            <div class="answer-rule"></div>
            <div class="answer-text">{result['answer']}</div>
        </div>""", unsafe_allow_html=True)

        if result["citations"]:
            st.markdown('<hr class="section-rule">', unsafe_allow_html=True)
            st.markdown('<div class="section-label">Sources</div>', unsafe_allow_html=True)
            rows = "".join([
                f"<tr><td>{c['number']}</td><td>{c['source']}</td>"
                f"<td>{c['score']}</td><td>{c['preview']}</td></tr>"
                for c in result["citations"]
            ])
            st.markdown(f'<table class="cit-table">{rows}</table>', unsafe_allow_html=True)

# ── TAB 2: COMPARE ────────────────────────────────────────────────────────────
with tab2:
    st.markdown('<div class="section-label" style="margin-top:1rem">Same question · every company · side by side</div>', unsafe_allow_html=True)

    compare_examples = [
        "What AI investments did the company announce?",
        "What did management say about headcount?",
        "What were the key growth drivers this quarter?",
        "How is the company thinking about competition?"
    ]
    ccols = st.columns(2)
    for i, ex in enumerate(compare_examples):
        with ccols[i % 2]:
            if st.button(ex, key=f"cex_{i}", use_container_width=True):
                st.session_state["compare_question"] = ex
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    compare_q = st.text_input("", value=st.session_state.get("compare_question",""),
                               placeholder="e.g. What did management say about margins?",
                               key="compare_input")
    # Keep session state in sync if user edits the text input directly
    if compare_q != st.session_state.get("compare_question", ""):
        st.session_state["compare_question"] = compare_q
    selected_tickers = st.multiselect("Companies to compare",
                                       ["NVDA","AAPL","MSFT","AMZN","META"],
                                       default=["NVDA","MSFT","META"])

    if compare_q and selected_tickers:
        with st.spinner(""):
            comparisons = compare_companies(compare_q, tickers=selected_tickers)
        st.markdown("<br>", unsafe_allow_html=True)
        for t, res in comparisons.items():
            st.markdown(f"""
            <div class="co-block">
                <div class="co-ticker">{t}</div>
                <div class="co-answer">{res['answer']}</div>
            </div>""", unsafe_allow_html=True)

# ── TAB 3: EXPLORE ────────────────────────────────────────────────────────────
with tab3:
    st.markdown('<div class="section-label" style="margin-top:1rem">Raw retrieval — what Claude sees before generation</div>', unsafe_allow_html=True)

    explore_q = st.text_input("", placeholder="e.g. cloud revenue growth", key="explore_input")
    ecols = st.columns(2)
    with ecols[0]:
        explore_k = st.slider("Chunks", 1, 10, 5, key="ek")
    with ecols[1]:
        explore_ticker = st.selectbox("Company", ["All","NVDA","AAPL","MSFT","AMZN","META"], key="et")
    explore_filter = None if explore_ticker == "All" else explore_ticker

    if explore_q:
        chunks = retrieve(explore_q, n_results=explore_k, ticker_filter=explore_filter)
        if not chunks:
            st.warning("No chunks found above relevance threshold.")
        else:
            st.markdown(f'<div class="section-label">{len(chunks)} chunks retrieved</div>', unsafe_allow_html=True)
            for chunk in chunks:
                with st.expander(f"{chunk['source']}  ·  {chunk['score']}  ·  {chunk['text'][:75]}..."):
                    st.markdown(
                        f'<span class="chunk-pill">{chunk["score"]}</span>'
                        f'<span class="chunk-pill">{chunk["source"]}</span>'
                        f'<span class="chunk-pill">{chunk["chunk_id"]}</span>',
                        unsafe_allow_html=True
                    )
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.write(chunk["text"])