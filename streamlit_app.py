import os
import time
import json
from typing import Any, Optional

from dotenv import load_dotenv
import requests
import streamlit as st


load_dotenv()

INNGEST_UI_URL = os.getenv("INNGEST_UI_URL", "http://127.0.0.1:8288")
FASTAPI_URL = os.getenv("FASTAPI_URL", "http://127.0.0.1:8000").rstrip("/")

STAGE_COPY = {
    "Queued": "Queued for processing",
    "Running": "Reading your documents",
    "Step Running": "Working through the passage",
}

st.set_page_config(
    page_title="Document Assistant",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600&family=Inter:wght@400;500;600;700&display=swap');

    :root {
        --bg: #0f1216;
        --bg-glow: rgba(232, 163, 61, 0.08);
        --surface: #171b21;
        --surface-2: #1d232c;
        --border: rgba(255, 255, 255, 0.08);
        --border-strong: rgba(255, 255, 255, 0.16);
        --text: #edf0f4;
        --text-muted: #8b93a3;
        --text-faint: #5c6577;
        --accent: #e8a33d;
        --accent-strong: #f4b959;
        --accent-soft: rgba(232, 163, 61, 0.12);
        --accent-border: rgba(232, 163, 61, 0.35);
        --danger: #e5484d;
        --danger-soft: rgba(229, 72, 77, 0.12);
        --success: #4ade80;
        --radius: 14px;
        --radius-sm: 10px;
    }

    html, body, [class*="css"] { font-family: 'Inter', -apple-system, sans-serif; }

    .stApp {
        background:
            radial-gradient(circle at 12% 6%, var(--bg-glow), transparent 34rem),
            var(--bg);
        color: var(--text);
    }

    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header[data-testid="stHeader"] { background: transparent; }

    .main .block-container {
        max-width: 46rem;
        padding-top: 1.5rem;
        padding-bottom: 7rem;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: var(--surface);
        border-right: 1px solid var(--border);
    }
    section[data-testid="stSidebar"] .block-container { padding-top: 1.75rem; }
    section[data-testid="stSidebar"] h3, section[data-testid="stSidebar"] strong { color: var(--text); }

    .brand { margin-bottom: 1.5rem; }
    .brand-mark {
        font-family: 'Newsreader', serif;
        font-size: 1.55rem;
        font-weight: 500;
        color: var(--text);
        line-height: 1.2;
    }
    .brand-sub { font-size: 0.78rem; color: var(--text-muted); margin-top: 0.15rem; }

    .pill {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        border: 1px solid var(--border-strong);
        background: var(--surface-2);
        color: var(--text-muted);
        border-radius: 999px;
        padding: 0.28rem 0.75rem;
        font-size: 0.74rem;
    }
    .pill .dot { width: 6px; height: 6px; border-radius: 50%; background: var(--success); flex: none; }

    /* Empty state */
    .empty-wrap { text-align: center; padding: 4rem 1rem 2rem; }
    .empty-title {
        font-family: 'Newsreader', serif;
        font-size: 2.15rem;
        font-weight: 500;
        color: var(--text);
        margin-bottom: 0.65rem;
    }
    .empty-copy {
        color: var(--text-muted);
        font-size: 0.98rem;
        max-width: 32rem;
        margin: 0 auto;
        line-height: 1.6;
    }

    /* Buttons */
    .stButton > button {
        background: var(--surface-2);
        color: var(--text);
        border: 1px solid var(--border-strong);
        border-radius: var(--radius-sm);
        font-weight: 500;
        transition: border-color .15s ease, background .15s ease, color .15s ease;
    }
    .stButton > button:hover {
        border-color: var(--accent-border);
        background: var(--accent-soft);
        color: var(--accent-strong);
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, var(--accent), var(--accent-strong));
        color: #17130a;
        border: none;
        font-weight: 600;
    }
    .stButton > button[kind="primary"]:hover { filter: brightness(1.06); }
    .stButton > button:disabled { opacity: 0.4; }

    /* Chat messages */
    div[data-testid="stChatMessage"] {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--radius);
        padding: 0.95rem 1.15rem;
        margin-bottom: 0.9rem;
    }
    div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-user"]),
    div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarUser"]) {
        background: var(--accent-soft);
        border-color: var(--accent-border);
    }

    /* Chat input */
    div[data-testid="stChatInput"] {
        background: var(--surface-2);
        border: 1px solid var(--border-strong);
        border-radius: 999px;
    }
    div[data-testid="stChatInput"] textarea { color: var(--text); }

    /* Source excerpt card */
    .source-card {
        border-left: 3px solid var(--accent);
        background: var(--surface-2);
        padding: 0.55rem 0.85rem;
        margin-bottom: 0.5rem;
        border-radius: 0 8px 8px 0;
        font-family: 'Newsreader', serif;
        font-style: italic;
        color: var(--text-muted);
        font-size: 0.88rem;
        line-height: 1.55;
    }

    /* Thinking indicator */
    .thinking { color: var(--text-muted); font-size: 0.92rem; display: flex; align-items: center; gap: 0.35rem; }
    .thinking .dots span { animation: blink 1.4s infinite; opacity: 0.2; }
    .thinking .dots span:nth-child(2) { animation-delay: 0.2s; }
    .thinking .dots span:nth-child(3) { animation-delay: 0.4s; }
    @keyframes blink { 0%, 80%, 100% { opacity: 0.2; } 40% { opacity: 1; } }

    /* Error card */
    .error-card {
        border-left: 3px solid var(--danger);
        background: var(--danger-soft);
        padding: 0.7rem 0.9rem;
        border-radius: 0 8px 8px 0;
        color: #ffb4b6;
        font-size: 0.9rem;
    }

    .stFileUploader section { background: var(--surface-2); border: 1px dashed var(--border-strong); border-radius: var(--radius-sm); }
    </style>
    """,
    unsafe_allow_html=True,
)


# ----------------------------------------------------------------------------
# Backend helpers
# ----------------------------------------------------------------------------
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


def thinking_html(label: str) -> str:
    return (
        f'<div class="thinking">{label}'
        f'<span class="dots"><span>.</span><span>.</span><span>.</span></span></div>'
    )


def wait_for_run_output(
    event_id: str,
    status_placeholder: Optional[Any] = None,
    timeout_s: float = 600.0,
    poll_interval_s: float = 2.0,
) -> dict:
    started_at = time.time()
    owns_placeholder = status_placeholder is None
    placeholder = status_placeholder or st.empty()
    last_status = "Queued"

    while time.time() - started_at <= timeout_s:
        runs = fetch_runs(event_id)
        if runs:
            run = runs[0]
            last_status = run.get("status") or last_status
            label = STAGE_COPY.get(last_status, last_status)

            if last_status in {"Completed", "Succeeded", "Success", "Finished"}:
                output = run.get("output")
                
                # CRITICAL FIX: If output is None, the dev server hasn't committed the JSON yet.
                # Keep polling instead of immediately returning!
                if output is None:
                    placeholder.markdown(thinking_html("Finalizing answer"), unsafe_allow_html=True)
                    time.sleep(poll_interval_s)
                    continue 
                
                # Safely parse JSON if Inngest returns it as a string
                if isinstance(output, str):
                    try:
                        output = json.loads(output)
                    except json.JSONDecodeError:
                        pass
                
                if owns_placeholder:
                    placeholder.empty()
                
                # Wrap it if it's somehow completely empty to avoid .get() crashes
                if not isinstance(output, dict):
                    output = {"raw_output": output, "run_id": run.get("id")}
                return output

            elif last_status in {"Failed", "Cancelled"}:
                if owns_placeholder:
                    placeholder.empty()
                raise RuntimeError(f"Function run {last_status}: {run}")
            else:
                placeholder.markdown(thinking_html(label), unsafe_allow_html=True)
        else:
            placeholder.markdown(thinking_html("Initializing"), unsafe_allow_html=True)

        time.sleep(poll_interval_s)

    if owns_placeholder:
        placeholder.empty()
    raise TimeoutError(f"Timed out waiting for run output. Last status: {last_status}")


def render_history_message(msg: dict) -> None:
    with st.chat_message(msg["role"]):
        if msg.get("error"):
            st.markdown(
                f'<div class="error-card">Something went wrong: {msg["error"]}</div>',
                unsafe_allow_html=True,
            )
            return
        st.markdown(msg["content"])
        sources = msg.get("sources") or []
        if sources:
            with st.expander(f"Sources ({len(sources)})", expanded=False):
                for source in sources:
                    st.markdown(f'<div class="source-card">{source}</div>', unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Session state
# ----------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "ingest_history" not in st.session_state:
    st.session_state.ingest_history = []

queued_prompt = st.session_state.pop("queued_prompt", None)

if os.getenv("USE_FAKE_EMBEDDINGS", "").lower() in {"1", "true", "yes"}:
    embedding_mode = "Fake local vectors"
else:
    embedding_mode = os.getenv("EMBED_PROVIDER", "NVIDIA NIM")


# ----------------------------------------------------------------------------
# Sidebar
# ----------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        '<div class="brand">'
        '<div class="brand-mark">Document Assistant</div>'
        '<div class="brand-sub">Ask questions, get answers grounded in your PDFs</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    if st.button("＋ New chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.markdown("**Add documents**")
    uploaded = st.file_uploader(
        "Select PDF",
        type=["pdf"],
        accept_multiple_files=False,
        label_visibility="collapsed",
    )
    if st.button("Index document", disabled=(uploaded is None), type="primary", use_container_width=True):
        with st.spinner("Uploading…"):
            try:
                result = upload_pdf_to_backend(uploaded)
                st.session_state.ingest_history.insert(
                    0, {"event_id": result["event_id"], "filename": result["filename"], "status": "Queued"}
                )
                st.toast(f"Indexing {result['filename']}", icon="✅")
            except Exception as exc:
                st.error(f"Could not start ingestion: {exc}")

    if st.session_state.ingest_history:
        with st.expander(f"Indexing activity ({len(st.session_state.ingest_history)})"):
            for item in st.session_state.ingest_history[:6]:
                st.caption(f"`{item['filename']}` — {item['status']}")
            if st.button("Refresh status", use_container_width=True):
                for item in st.session_state.ingest_history:
                    try:
                        runs = fetch_runs(item["event_id"])
                        if runs:
                            item["status"] = runs[0].get("status", item["status"])
                    except Exception:
                        pass
                st.rerun()

    st.divider()
    with st.expander("Answer settings"):
        top_k = st.slider("Context depth (retrieved chunks)", min_value=1, max_value=10, value=5, key="top_k_slider")

    with st.expander("System status"):
        st.markdown(f'<span class="pill"><span class="dot"></span>{embedding_mode}</span>', unsafe_allow_html=True)
        st.caption(f"FastAPI · `{FASTAPI_URL}`")
        st.caption(f"Inngest · `{INNGEST_UI_URL}`")
        st.caption("Qdrant · `http://localhost:6333`")
        st.code("rag/ingest_pdf", language="text")
        st.code("rag/query_pdf_ai", language="text")


# ----------------------------------------------------------------------------
# Main chat
# ----------------------------------------------------------------------------
if not st.session_state.messages and not queued_prompt:
    st.markdown(
        """
        <div class="empty-wrap">
            <div class="empty-title">What's in your documents?</div>
            <div class="empty-copy">
                Upload a PDF from the sidebar, then ask anything — a summary, a specific
                figure, or a clause buried on page 40. Answers come with the passages
                they're drawn from.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    suggestions = [
        "Summarize this document in a few sentences",
        "What are the key takeaways?",
        "List any dates or deadlines mentioned",
    ]
    cols = st.columns(3)
    for col, suggestion in zip(cols, suggestions):
        with col:
            if st.button(suggestion, use_container_width=True, key=f"suggest_{suggestion}"):
                st.session_state.queued_prompt = suggestion
                st.rerun()
else:
    for msg in st.session_state.messages:
        render_history_message(msg)

typed_prompt = st.chat_input("Message your documents…")
prompt = queued_prompt or typed_prompt

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    render_history_message(st.session_state.messages[-1])

    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown(thinking_html("Sending your question"), unsafe_allow_html=True)
        try:
            result = send_query_to_backend(prompt, int(top_k))
            event_id = result["event_id"]
            output = wait_for_run_output(event_id, status_placeholder=placeholder)
            
            answer = output.get("answer")
            if not answer:
                answer = (
                    "I couldn't find an answer in your documents.\n\n"
                    f"*(Debug context: Output received from Inngest was: `{output}`)*"
                )
                
            sources = output.get("sources", [])

            placeholder.markdown(answer)
            if sources:
                with st.expander(f"Sources ({len(sources)})", expanded=False):
                    for source in sources:
                        st.markdown(f'<div class="source-card">{source}</div>', unsafe_allow_html=True)

            st.session_state.messages.append(
                {"role": "assistant", "content": answer, "sources": sources, "event_id": event_id}
            )
        except Exception as exc:
            placeholder.markdown(
                f'<div class="error-card">Something went wrong: {exc}</div>', unsafe_allow_html=True
            )
            st.session_state.messages.append({"role": "assistant", "content": None, "error": str(exc)})