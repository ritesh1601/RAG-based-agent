from openai import OpenAI
from openai import APITimeoutError, APIConnectionError, RateLimitError
from llama_index.readers.file import PDFReader
from llama_index.core.node_parser import SentenceSplitter
from dotenv import load_dotenv
import hashlib
import os
import time

load_dotenv()

openai_client = None
sentence_transformer_model = None

EMBED_PROVIDER = os.getenv("EMBED_PROVIDER", "openai").lower()
OPENAI_EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-large")
SENTENCE_TRANSFORMER_MODEL = os.getenv("SENTENCE_TRANSFORMER_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
EMBED_DIMENSIONS = {
    "openai": 3072,
    "sentence-transformers": 384,
}
EMBED_DIM = int(os.getenv("EMBED_DIM", str(EMBED_DIMENSIONS.get(EMBED_PROVIDER, 3072))))
EMBED_BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", "32"))
USE_FAKE_EMBEDDINGS = os.getenv("USE_FAKE_EMBEDDINGS", "").lower() in {"1", "true", "yes"}


splitter = SentenceSplitter(chunk_size=1000, chunk_overlap=200)

def load_and_chunk_pdf(path: str):
    docs = PDFReader().load_data(file=path)
    texts = [d.text for d in docs if getattr(d, "text", None)]
    chunks = []
    for t in texts:
        chunks.extend(splitter.split_text(t))
    return chunks


def get_openai_client() -> OpenAI:
    global openai_client
    if openai_client is None:
        openai_client = OpenAI(
            timeout=float(os.getenv("OPENAI_TIMEOUT_SECONDS", "60")),
            max_retries=int(os.getenv("OPENAI_MAX_RETRIES", "2")),
        )
    return openai_client


def get_sentence_transformer_model():
    global sentence_transformer_model
    if sentence_transformer_model is None:
        from sentence_transformers import SentenceTransformer

        sentence_transformer_model = SentenceTransformer(SENTENCE_TRANSFORMER_MODEL)
    return sentence_transformer_model


def fake_embedding(text: str) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values = []
    for i in range(EMBED_DIM):
        byte = digest[i % len(digest)]
        values.append((byte / 127.5) - 1.0)
    return values


def embed_texts(texts: list[str]) -> list[list[float]]:
    if USE_FAKE_EMBEDDINGS:
        return [fake_embedding(text) for text in texts]
    if EMBED_PROVIDER == "sentence-transformers":
        model = get_sentence_transformer_model()
        return model.encode(texts, normalize_embeddings=True).tolist()

    embeddings = []
    openai_client = get_openai_client()

    for start in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[start:start + EMBED_BATCH_SIZE]

        for attempt in range(3):
            try:
                response = openai_client.embeddings.create(
                    model=OPENAI_EMBED_MODEL,
                    input=batch,
                )
                embeddings.extend(item.embedding for item in response.data)
                break
            except (APITimeoutError, APIConnectionError, RateLimitError):
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)

    return embeddings
