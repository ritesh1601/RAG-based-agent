import logging
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
import inngest
import inngest.fast_api
from inngest.experimental import ai
from dotenv import load_dotenv
import uuid
import os
import datetime
from data_loader import load_and_chunk_pdf, embed_texts
from vector_db import QdrantStorage
from custom_types import RAQQueryResult, RAGSearchResult, RAGUpsertResult, RAGChunkAndSrc

load_dotenv()

UPLOADS_DIR = Path(os.getenv("UPLOADS_DIR", "uploads"))

inngest_dev = os.getenv("INNGEST_DEV", "").lower() in {"1", "true", "yes"}
inngest_event_key = os.getenv("INNGEST_EVENT_KEY")
inngest_signing_key = os.getenv("INNGEST_SIGNING_KEY")
inngest_is_production = bool(inngest_event_key and inngest_signing_key and not inngest_dev)

inngest_client = inngest.Inngest(
    app_id="rag_app",
    logger=logging.getLogger("uvicorn"),
    event_key=inngest_event_key,
    signing_key=inngest_signing_key,
    is_production=inngest_is_production,
    serializer=inngest.PydanticSerializer()
)

@inngest_client.create_function(
    fn_id="RAG: Ingest PDF",
    trigger=inngest.TriggerEvent(event="rag/ingest_pdf"),
    throttle=inngest.Throttle(
        limit=2, period=datetime.timedelta(minutes=1)
    ),
    rate_limit=inngest.RateLimit(
        limit=1,
        period=datetime.timedelta(hours=4),
        key="event.data.source_id",
  ),
)
async def rag_inngest_pdf(ctx: inngest.Context):
    def _load(ctx: inngest.Context) -> RAGChunkAndSrc:
        pdf_path = ctx.event.data["pdf_path"]
        source_id = ctx.event.data.get("source_id", pdf_path)
        chunks = load_and_chunk_pdf(pdf_path)
        return RAGChunkAndSrc(chunks=chunks, source_id=source_id)

    def _upsert(chunks_and_src: RAGChunkAndSrc) -> RAGUpsertResult:
        chunks = chunks_and_src.chunks
        source_id = chunks_and_src.source_id
        vecs = embed_texts(chunks)
        ids = [str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source_id}:{i}")) for i in range(len(chunks))]
        payloads = [{"source": source_id, "text": chunks[i]} for i in range(len(chunks))]
        QdrantStorage().upsert(ids, vecs, payloads)
        return RAGUpsertResult(ingested=len(chunks))

    chunks_and_src = await ctx.step.run("load-and-chunk", lambda: _load(ctx), output_type=RAGChunkAndSrc)
    ingested = await ctx.step.run("embed-and-upsert", lambda: _upsert(chunks_and_src), output_type=RAGUpsertResult)
    return ingested.model_dump()


@inngest_client.create_function(
    fn_id="RAG: Query PDF",
    trigger=inngest.TriggerEvent(event="rag/query_pdf_ai")
)
async def rag_query_pdf_ai(ctx: inngest.Context):
    def _search(question: str, top_k: int = 5) -> RAGSearchResult:
        query_vec = embed_texts([question])[0]
        store = QdrantStorage()
        found = store.search(query_vec, top_k)
        return RAGSearchResult(contexts=found["contexts"], sources=found["sources"])

    question = ctx.event.data["question"]
    top_k = int(ctx.event.data.get("top_k", 5))

    found = await ctx.step.run("embed-and-search", lambda: _search(question, top_k), output_type=RAGSearchResult)

    context_block = "\n\n".join(f"- {c}" for c in found.contexts)
    user_content = (
        "Use the following context to answer the question.\n\n"
        f"Context:\n{context_block}\n\n"
        f"Question: {question}\n"
        "Answer concisely using the context above."
    )

    adapter = ai.openai.Adapter(
        auth_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-4o-mini"
    )

    res = await ctx.step.ai.infer(
        "llm-answer",
        adapter=adapter,
        body={
            "max_tokens": 1024,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": "You answer questions using only the provided context."},
                {"role": "user", "content": user_content}
            ]
        }
    )

    answer = res["choices"][0]["message"]["content"].strip()
    return {"answer": answer, "sources": found.sources, "num_contexts": len(found.contexts)}

app = FastAPI()


@app.get("/health")
async def health():
    return {"ok": True, "app": "rag_app"}


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if file.content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported")

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename or "document.pdf").name
    if not safe_name.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Uploaded file must be a PDF")

    file_path = UPLOADS_DIR / f"{uuid.uuid4()}-{safe_name}"
    file_path.write_bytes(await file.read())

    event_ids = await inngest_client.send(
        inngest.Event(
            name="rag/ingest_pdf",
            data={
                "pdf_path": str(file_path.resolve()),
                "source_id": safe_name,
            },
        )
    )

    return {
        "status": "queued",
        "event_id": event_ids[0],
        "filename": safe_name,
    }


@app.post("/query")
async def query_pdf(payload: dict):
    question = str(payload.get("question", "")).strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is required")

    top_k = int(payload.get("top_k", 5))
    event_ids = await inngest_client.send(
        inngest.Event(
            name="rag/query_pdf_ai",
            data={
                "question": question,
                "top_k": top_k,
            },
        )
    )

    return {
        "status": "queued",
        "event_id": event_ids[0],
    }


inngest.fast_api.serve(app, inngest_client, [rag_inngest_pdf, rag_query_pdf_ai])
