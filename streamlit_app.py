import os
import time

from dotenv import load_dotenv
import requests
import streamlit as st


load_dotenv()

INNGEST_UI_URL = os.getenv("INNGEST_UI_URL", "http://127.0.0.1:8288")
FASTAPI_URL = os.getenv("FASTAPI_URL", "http://127.0.0.1:8000").rstrip("/")


st.set_page_config(
    page_title="RAG Document Assistant",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown(
    """
    <style>
    :root {
        --bg: #0b0f17;
        --panel: #111827;
        --panel-soft: #151f2f;
        --border: rgba(148, 163, 184, 0.22);
        --muted: #94a3b8;
        --text: #e5eefb;
        --accent: #38bdf8;
        --accent-2: #22c55e;
        --warn: #f59e0b;
    }

    .stApp {
        background:
            radial-gradient(circle at top left, rgba(56, 189, 248, 0.12), transparent 30rem),
            linear-gradient(135deg, #090d14 0%, #101826 52%, #0a1019 100%);
        color: var(--text);
    }

    [data-testid="stSidebar"] {
        background: #080c13;
        border-right: 1px solid var(--border);
    }

    [data-testid="stHeader"] {
        background: rgba(8, 12, 19, 0.72);
        backdrop-filter: blur(14px);
    }

    .block-container {
        max-width: 1240px;
        padding-top: 2.5rem;
        padding-bottom: 3rem;
    }

    h1, h2, h3 {
        letter-spacing: 0;
    }

    .hero {
        padding: 1.1rem 0 1.4rem 0;
    }

    .eyebrow {
        color: var(--accent);
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin-bottom: 0.4rem;
    }

    .hero-title {
        color: var(--text);
        font-size: 2.65rem;
        font-weight: 800;
        line-height: 1.05;
        margin-bottom: 0.55rem;
    }

    .hero-copy {
        color: var(--muted);
        font-size: 1.02rem;
        max-width: 760px;
        line-height: 1.7;
    }

    .metric-row {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 0.8rem;
        margin: 1.1rem 0 1.4rem;
    }

    .metric {
        border: 1px solid var(--border);
        background: linear-gradient(180deg, rgba(17, 24, 39, 0.94), rgba(15, 23, 42, 0.9));
        border-radius: 8px;
        padding: 1rem;
    }

    .metric-label {
        color: var(--muted);
        font-size: 0.78rem;
        margin-bottom: 0.35rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    .metric-value {
        color: var(--text);
        font-size: 1.05rem;
        font-weight: 700;
    }

    .card {
        border: 1px solid var(--border);
        background: linear-gradient(180deg, rgba(17, 24, 39, 0.94), rgba(15, 23, 42, 0.9));
        border-radius: 8px;
        padding: 1.2rem;
        box-shadow: 0 18px 50px rgba(0, 0, 0, 0.28);
        min-height: 100%;
    }

    .card-title {
        color: var(--text);
        font-size: 1.05rem;
        font-weight: 800;
        margin-bottom: 0.25rem;
    }

    .card-copy {
        color: var(--muted);
        font-size: 0.9rem;
        line-height: 1.55;
        margin-bottom: 1rem;
    }

    .pipeline {
        display: grid;
        grid-template-columns: repeat(6, minmax(0, 1fr));
        gap: 0.7rem;
        margin: 0.75rem 0 1.4rem;
    }

    .pipeline-step {
        border: 1px solid var(--border);
        background: rgba(15, 23, 42, 0.74);
        border-radius: 8px;
        padding: 0.85rem;
        min-height: 112px;
    }

    .pipeline-index {
        color: var(--accent);
        font-weight: 800;
        font-size: 0.78rem;
        margin-bottom: 0.55rem;
    }

    .pipeline-title {
        color: var(--text);
        font-size: 0.9rem;
        font-weight: 800;
        line-height: 1.28;
        margin-bottom: 0.35rem;
    }

    .pipeline-copy {
        color: var(--muted);
        font-size: 0.78rem;
        line-height: 1.42;
    }

    .status-pill {
        display: inline-flex;
        align-items: center;
        border: 1px solid rgba(34, 197, 94, 0.32);
        color: #bbf7d0;
        background: rgba(34, 197, 94, 0.12);
        border-radius: 999px;
        padding: 0.28rem 0.65rem;
        font-size: 0.78rem;
        font-weight: 700;
    }

    .chat-answer {
        border-left: 3px solid var(--accent);
        background: rgba(14, 165, 233, 0.09);
        border-radius: 8px;
        padding: 1rem 1.1rem;
        color: var(--text);
        line-height: 1.62;
    }

    .source-item {
        border: 1px solid var(--border);
        background: rgba(15, 23, 42, 0.62);
        border-radius: 8px;
        padding: 0.65rem 0.8rem;
        color: var(--muted);
        margin-top: 0.45rem;
        font-size: 0.88rem;
    }

    .stButton > button, .stDownloadButton > button {
        border-radius: 8px;
        border: 1px solid rgba(56, 189, 248, 0.4);
        background: linear-gradient(135deg, #0284c7 0%, #0ea5e9 100%);
        color: white;
        font-weight: 800;
        min-height: 2.75rem;
    }

    .stButton > button:hover, .stDownloadButton > button:hover {
        border-color: rgba(125, 211, 252, 0.8);
        box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.14);
    }

    .stTextInput input, .stNumberInput input, textarea {
        border-radius: 8px !important;
        border-color: var(--border) !important;
        background: rgba(15, 23, 42, 0.8) !important;
        color: var(--text) !important;
    }

    [data-testid="stFileUploader"] {
        border: 1px dashed rgba(148, 163, 184, 0.32);
        background: rgba(15, 23, 42, 0.48);
        border-radius: 8px;
        padding: 0.8rem;
    }

    @media (max-width: 980px) {
        .pipeline, .metric-row {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }

        .hero-title {
            font-size: 2.1rem;
        }
    }

    @media (max-width: 640px) {
        .pipeline, .metric-row {
            grid-template-columns: 1fr;
        }

        .hero-title {
            font-size: 1.8rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def upload_pdf_to_backend(file) -> dict:
    files = {"file": (file.name, file.getvalue(), "application/pdf")}
    response = requests.post(f"{FASTAPI_URL}/upload", files=files, timeout=60)
    response.raise_for_status()
    return response.json()


def send_query_to_backend(question: str, top_k: int) -> dict:
    response = requests.post(
        f"{FASTAPI_URL}/query",
        json={"question": question, "top_k": top_k},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def fetch_runs(event_id: str) -> list[dict]:
    response = requests.get(f"{FASTAPI_URL}/runs/{event_id}", timeout=10)
    response.raise_for_status()
    return response.json().get("data", [])


def wait_for_run_output(event_id: str, timeout_s: float = 420.0, poll_interval_s: float = 2.0) -> dict:
    started_at = time.time()
    last_status = "Queued"

    while time.time() - started_at <= timeout_s:
        runs = fetch_runs(event_id)
        if runs:
            run = runs[0]
            last_status = run.get("status") or last_status
            if last_status in {"Completed", "Succeeded", "Success", "Finished"}:
                return run.get("output") or {}
            if last_status in {"Failed", "Cancelled"}:
                raise RuntimeError(f"Function run {last_status}")
        time.sleep(poll_interval_s)

    raise TimeoutError(f"Timed out waiting for run output. Last status: {last_status}")


def render_pipeline() -> None:
    steps = [
        ("01", "Upload PDF", "A local document is saved for ingestion."),
        ("02", "Read & Chunk", "Pages are split into retrievable text units."),
        ("03", "Embed", "Chunks become vectors with the configured embedding mode."),
        ("04", "Store", "Vectors and source text are written to Qdrant."),
        ("05", "Retrieve", "Questions are embedded and matched against Qdrant."),
        ("06", "Answer", "The model responds using retrieved context."),
    ]
    html = '<div class="pipeline">'
    for index, title, copy in steps:
        html += (
            '<div class="pipeline-step">'
            f'<div class="pipeline-index">{index}</div>'
            f'<div class="pipeline-title">{title}</div>'
            f'<div class="pipeline-copy">{copy}</div>'
            '</div>'
        )
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def render_metric(label: str, value: str) -> str:
    return (
        '<div class="metric">'
        f'<div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div>'
        '</div>'
    )


if os.getenv("USE_FAKE_EMBEDDINGS", "").lower() in {"1", "true", "yes"}:
    embedding_mode = "Fake local vectors"
else:
    embedding_mode = os.getenv("EMBED_PROVIDER", "openai")

with st.sidebar:
    st.markdown("### RAG Control Plane")
    st.caption("Local development workspace")
    st.markdown(f'<span class="status-pill">{embedding_mode}</span>', unsafe_allow_html=True)
    st.divider()
    st.markdown("**Services**")
    st.caption(f"FastAPI: `{FASTAPI_URL}`")
    st.caption(f"Inngest: `{INNGEST_UI_URL}`")
    st.caption("Qdrant: `http://localhost:6333`")
    st.divider()
    st.markdown("**Events**")
    st.caption("`rag/ingest_pdf`")
    st.caption("`rag/query_pdf_ai`")


st.markdown(
    """
    <section class="hero">
        <div class="eyebrow">Private Knowledge Workflow</div>
        <div class="hero-title">RAG-Powered Document Intelligence</div>
        <div class="hero-copy">
            Upload source PDFs, index them through an observable Inngest workflow, and query your Qdrant-backed knowledge base from one focused dashboard.
        </div>
    </section>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="metric-row">'
    + render_metric("Ingestion", "Inngest + Qdrant")
    + render_metric("Retrieval", "Vector search")
    + render_metric("Answering", "Context-grounded")
    + "</div>",
    unsafe_allow_html=True,
)

render_pipeline()

left, right = st.columns([0.95, 1.05], gap="large")

with left:
    st.markdown(
        """
        <div class="card">
            <div class="card-title">Build Knowledge Base</div>
            <div class="card-copy">Index a PDF into the local vector store through the ingestion workflow.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    uploaded = st.file_uploader("PDF document", type=["pdf"], accept_multiple_files=False)

    ingest_disabled = uploaded is None
    if st.button("Start Ingestion", disabled=ingest_disabled, use_container_width=True):
        with st.spinner("Starting ingestion workflow..."):
            try:
                result = upload_pdf_to_backend(uploaded)
                event_id = result["event_id"]
                st.session_state["last_ingest_event_id"] = event_id
                st.success(f"Ingestion started for {result['filename']}")
                st.caption(f"Event ID: {event_id}")
            except Exception as exc:
                st.error(f"Could not start ingestion: {exc}")

    if "last_ingest_event_id" in st.session_state:
        st.info(f"Last ingest event: {st.session_state['last_ingest_event_id']}")

with right:
    st.markdown(
        """
        <div class="card">
            <div class="card-title">Ask Your Documents</div>
            <div class="card-copy">Send a question through retrieval and answer generation, then inspect the response and sources.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("rag_query_form"):
        question = st.text_area(
            "Question",
            placeholder="Ask a question about the indexed PDFs...",
            height=120,
        )
        top_k = st.slider("Retrieved chunks", min_value=1, max_value=12, value=5)
        submitted = st.form_submit_button("Generate Answer", use_container_width=True)

    if submitted:
        if not question.strip():
            st.warning("Enter a question before generating an answer.")
        else:
            with st.spinner("Retrieving context and generating answer..."):
                try:
                    result = send_query_to_backend(question.strip(), int(top_k))
                    event_id = result["event_id"]
                    output = wait_for_run_output(event_id)
                    st.session_state["last_answer"] = output.get("answer", "")
                    st.session_state["last_sources"] = output.get("sources", [])
                    st.session_state["last_query_event_id"] = event_id
                except Exception as exc:
                    st.error(f"Query failed: {exc}")

    if st.session_state.get("last_answer"):
        st.markdown("#### AI Response")
        st.markdown(
            f'<div class="chat-answer">{st.session_state["last_answer"]}</div>',
            unsafe_allow_html=True,
        )

        sources = st.session_state.get("last_sources", [])
        if sources:
            st.markdown("#### Sources")
            for source in sources:
                st.markdown(f'<div class="source-item">{source}</div>', unsafe_allow_html=True)

        if st.session_state.get("last_query_event_id"):
            st.caption(f"Query event ID: {st.session_state['last_query_event_id']}")
