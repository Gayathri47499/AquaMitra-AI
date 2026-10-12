
import os
import json
import httpx
from dotenv import load_dotenv
from supabase import create_client

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=False)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")
SUPABASE_PUBLISHABLE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY")

TOP_K = 5


def get_supabase():
    """Create a Supabase client only when needed."""
    key = SUPABASE_SECRET_KEY or SUPABASE_PUBLISHABLE_KEY

    if not SUPABASE_URL or not key:
        raise RuntimeError("Supabase environment variables are missing.")

    return create_client(SUPABASE_URL, key)


def retrieve_passages(question: str, top_k: int = TOP_K):
    """
    Temporary memory-safe mode.
    Does not load SentenceTransformer or PyTorch on Render.
    RAG retrieval will be restored separately.
    """
    return []


def format_passages(passages) -> str:
    """Format retrieved passages as source-labelled context."""
    if not passages:
        return ""

    sections = []

    for passage in passages:
        source = passage.get(
            "source",
            "ICAR Handbook of Fisheries and Aquaculture"
        )
        page = passage.get("page", passage.get("page_number", "N/A"))
        content = passage.get("content", "").strip()

        if content:
            sections.append(
                f"[Source: {source}, Page {page}]\n{content}"
            )

    return "\n\n".join(sections)


def generate_hf_answer(question: str, context: str) -> str:
    """Send the question and retrieved context to the Hugging Face Space."""
    token = os.getenv("HF_TOKEN")

    if not token:
        raise RuntimeError("HF_TOKEN is not configured on the server.")

    endpoint = (
        "https://gayathri-sanjana-meenaai-api.hf.space/"
        "gradio_api/call/answer_question"
    )

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=120.0) as client:
        response = client.post(
            endpoint,
            json={"data": [question, context]},
            headers=headers,
        )
        response.raise_for_status()

        event_id = response.json().get("event_id")

        if not event_id:
            raise RuntimeError(
                "Hugging Face did not return an event ID."
            )

        result = client.get(
            f"{endpoint}/{event_id}",
            headers=headers,
        )
        result.raise_for_status()

    for line in result.text.splitlines():
        if line.startswith("data:"):
            payload = json.loads(line[len("data:"):].strip())

            if payload and isinstance(payload[0], str):
                return payload[0]

    raise RuntimeError("Hugging Face returned no answer.")
