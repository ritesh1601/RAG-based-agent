import os
import time
import hashlib
from dotenv import load_dotenv
from openai import OpenAI, APITimeoutError, APIConnectionError, RateLimitError
from llama_index.readers.file import PDFReader
from llama_index.core.node_parser import SentenceSplitter

load_dotenv()

AI_BASE_URL = os.getenv("AI_BASE_URL", "https://integrate.api.nvidia.com/v1")
AI_API_KEY = os.getenv("AI_API_KEY")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nvidia/nv-embedqa-e5-v5")
EMBED_DIM = int(os.getenv("EMBED_DIM", "1024"))
EMBED_BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", "32"))
USE_FAKE_EMBEDDINGS = os.getenv("USE_FAKE_EMBEDDINGS", "").lower() in {"1", "true", "yes"}

ai_client = None
splitter = SentenceSplitter(chunk_size=1000, chunk_overlap=200)

def load_and_chunk_pdf(path: str):
    docs = PDFReader().load_data(file=path)
    texts = [d.text for d in docs if getattr(d, "text", None)]
    chunks = []
    for t in texts:
        chunks.extend(splitter.split_text(t))
    return chunks

def get_ai_client() -> OpenAI:
    global ai_client
    if ai_client is None:
        ai_client = OpenAI(
            base_url=AI_BASE_URL,
            api_key=AI_API_KEY,
            timeout=float(os.getenv("OPENAI_TIMEOUT_SECONDS", "60")),
            max_retries=int(os.getenv("OPENAI_MAX_RETRIES", "2")),
        )
    return ai_client

def fake_embedding(text: str) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values = []
    for i in range(EMBED_DIM):
        byte = digest[i % len(digest)]
        values.append((byte / 127.5) - 1.0)
    return values

# Notice the new 'input_type' parameter!
def embed_texts(texts: list[str], input_type: str = "passage") -> list[list[float]]:
    if USE_FAKE_EMBEDDINGS:
        return [fake_embedding(text) for text in texts]

    embeddings = []
    client = get_ai_client()

    for start in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[start:start + EMBED_BATCH_SIZE]

        for attempt in range(3):
            try:
                response = client.embeddings.create(
                    model=EMBEDDING_MODEL,
                    input=batch,
                    encoding_format="float",
                    # NVIDIA strictly requires these extra body parameters
                    extra_body={
                        "input_type": input_type,
                        "truncate": "END" 
                    }
                )
                embeddings.extend(item.embedding for item in response.data)
                break
            except (APITimeoutError, APIConnectionError, RateLimitError):
                if attempt == 2:
                    raise  
                time.sleep(2 ** attempt)  

    return embeddings