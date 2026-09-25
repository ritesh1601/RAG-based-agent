import logging
import inngest
from config import INNGEST_EVENT_KEY, INNGEST_SIGNING_KEY, INNGEST_IS_PRODUCTION

inngest_client = inngest.Inngest(
    app_id="rag_app",
    logger=logging.getLogger("uvicorn"),
    event_key=INNGEST_EVENT_KEY,
    signing_key=INNGEST_SIGNING_KEY,
    is_production=INNGEST_IS_PRODUCTION,
    serializer=inngest.PydanticSerializer()
)