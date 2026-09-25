import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

UPLOADS_DIR = Path(os.getenv("UPLOADS_DIR", "uploads"))

# Inngest settings
INNGEST_DEV = os.getenv("INNGEST_DEV", "").lower() in {"1", "true", "yes"}
INNGEST_EVENT_KEY = os.getenv("INNGEST_EVENT_KEY")
INNGEST_SIGNING_KEY = os.getenv("INNGEST_SIGNING_KEY")
INNGEST_IS_PRODUCTION = bool(INNGEST_EVENT_KEY and INNGEST_SIGNING_KEY and not INNGEST_DEV)

# AI Settings
ANSWER_PROVIDER = os.getenv("ANSWER_PROVIDER", "openai").lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# config.py additions
AI_BASE_URL = os.getenv("AI_BASE_URL", "https://integrate.api.nvidia.com/v1")
AI_API_KEY = os.getenv("AI_API_KEY")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nvidia/nemotron-3-embed-1b")
LLM_MODEL = os.getenv("LLM_MODEL", "nvidia/nemotron-3.5-lightning-30b-a3b")