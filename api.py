import uuid
import logging
import requests
from pathlib import Path
from typing import Any
from fastapi import APIRouter, File, HTTPException, UploadFile
import inngest

from config import UPLOADS_DIR, INNGEST_SIGNING_KEY
from inngest_client import inngest_client

router = APIRouter()
logger = logging.getLogger("uvicorn")

async def send_inngest_event(name: str, data: dict[str, Any]) -> str:
    try:
        event_ids = await inngest_client.send(inngest.Event(name=name, data=data))
    except Exception as exc:
        logger.exception("Failed to send Inngest event %s", name)
        raise HTTPException(status_code=502, detail=f"Failed to send Inngest event: {exc}") from exc

    if not event_ids:
        raise HTTPException(status_code=502, detail="Inngest did not return an event ID")

    return event_ids[0]


@router.get("/health")
async def health():
    return {"ok": True, "app": "rag_app"}

@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if file.content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported")

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename or "document.pdf").name
    if not safe_name.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Uploaded file must be a PDF")

    file_path = UPLOADS_DIR / f"{uuid.uuid4()}-{safe_name}"
    file_path.write_bytes(await file.read())

    event_id = await send_inngest_event(
        "rag/ingest_pdf",
        {
            "pdf_path": str(file_path.resolve()),
            "source_id": safe_name,
        },
    )

    return {
        "status": "queued",
        "event_id": event_id,
        "filename": safe_name,
    }

@router.post("/query")
async def query_pdf(payload: dict):
    question = str(payload.get("question", "")).strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is required")

    top_k = int(payload.get("top_k", 5))
    event_id = await send_inngest_event(
        "rag/query_pdf_ai",
        {
            "question": question,
            "top_k": top_k,
        },
    )

    return {
        "status": "queued",
        "event_id": event_id,
    }

@router.get("/runs/{event_id}")
async def get_event_runs(event_id: str):
    from config import INNGEST_DEV, INNGEST_SIGNING_KEY
    import requests

    # 1. If in dev mode, query the local Inngest UI running on port 8288
    if INNGEST_DEV:
        url = f"http://127.0.0.1:8288/v1/events/{event_id}/runs"
        # The local dev server doesn't require real authentication
        headers = {} 
        
    # 2. If in production, query the real Inngest Cloud API
    else:
        if not INNGEST_SIGNING_KEY:
            raise HTTPException(status_code=500, detail="INNGEST_SIGNING_KEY is not configured")
        url = f"https://api.inngest.com/v1/events/{event_id}/runs"
        headers = {"Authorization": f"Bearer {INNGEST_SIGNING_KEY}"}

    # Fetch the status
    response = requests.get(url, headers=headers, timeout=10)

    # Relay any errors back to Streamlit
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    return response.json()