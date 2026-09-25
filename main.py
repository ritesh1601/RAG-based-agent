from fastapi import FastAPI
import inngest.fast_api

from inngest_client import inngest_client
from tasks import rag_inngest_pdf, rag_query_pdf_ai
from api import router

app = FastAPI(title="RAG Application")

# Include HTTP endpoints
app.include_router(router)

# Mount Inngest handlers
inngest.fast_api.serve(
    app, 
    inngest_client, 
    [rag_inngest_pdf, rag_query_pdf_ai]
)