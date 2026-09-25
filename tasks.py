import time
import uuid
import datetime
import logging
import inngest
from openai import AsyncOpenAI

from inngest_client import inngest_client
from config import ANSWER_PROVIDER, AI_BASE_URL, AI_API_KEY, LLM_MODEL
from data_loader import load_and_chunk_pdf, embed_texts
from vector_db import QdrantStorage
from custom_types import RAQQueryResult, RAGSearchResult, RAGUpsertResult, RAGChunkAndSrc

logger = logging.getLogger("uvicorn")

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
        started_at = time.time()
        logger.info("Starting RAG search with top_k=%s", top_k)
        
        # embed_texts now uses your NVIDIA/Mistral client setup in data_loader.py
        query_vec = embed_texts([question], input_type="query")[0]
        
        store = QdrantStorage()
        found = store.search(query_vec, top_k)
        logger.info(
            "Finished RAG search in %.2fs with %s contexts",
            time.time() - started_at,
            len(found["contexts"]),
        )
        return RAGSearchResult(contexts=found["contexts"], sources=found["sources"])

    question = ctx.event.data["question"]
    top_k = int(ctx.event.data.get("top_k", 5))

    found = await ctx.step.run("embed-and-search", lambda: _search(question, top_k), output_type=RAGSearchResult)

    context_block = "\n\n".join(f"- {c}" for c in found.contexts)
    if ANSWER_PROVIDER == "extractive":
        answer = (
            "I found the most relevant context below:\n\n"
            f"{context_block or 'No matching context was found.'}"
        )
        return {"answer": answer, "sources": found.sources, "num_contexts": len(found.contexts)}

    user_content = (
        "Use the following context to answer the question.\n\n"
        f"Context:\n{context_block}\n\n"
        f"Question: {question}\n"
        "Answer concisely using the context above."
    )

    # Initialize AsyncOpenAI client with your custom base URL (NVIDIA/Mistral)
    ai_client = AsyncOpenAI(
        base_url=AI_BASE_URL,
        api_key=AI_API_KEY
    )

    async def _generate_answer():
        res = await ai_client.chat.completions.create(
            model=LLM_MODEL,
            temperature=0.2,
            max_tokens=1024,
            messages=[
                {"role": "system", "content": "You answer questions using only the provided context."},
                {"role": "user", "content": user_content}
            ]
        )
        return res.choices[0].message.content.strip()

    # Run the LLM generation as a durable Inngest step
    answer = await ctx.step.run("llm-answer", _generate_answer)
    
    return {"answer": answer, "sources": found.sources, "num_contexts": len(found.contexts)}