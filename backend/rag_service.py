
import os
from functools import lru_cache

from dotenv import load_dotenv
from supabase import create_client
from sentence_transformers import SentenceTransformer

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=False)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")

DOCUMENT_ID = 1
TOP_K = 5
MIN_SIMILARITY = 0.45


@lru_cache(maxsize=1)
def get_supabase():
    if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
        raise RuntimeError(
            "Supabase URL or server secret is not configured."
        )
    return create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)


@lru_cache(maxsize=1)
def get_embedding_model():
    return SentenceTransformer(
        "sentence-transformers/all-MiniLM-L6-v2",
        device="cpu"
    )


def retrieve_passages(question: str, top_k: int = TOP_K):
    if not question or not question.strip():
        return []

    model = get_embedding_model()
    query_embedding = model.encode(
        question.strip(),
        normalize_embeddings=True
    ).tolist()

    response = get_supabase().rpc(
        "match_knowledge_passages",
        {
            "query_embedding": query_embedding,
            "match_count": min(max(int(top_k), 1), 10),
            "filter_document_id": DOCUMENT_ID
        }
    ).execute()

    passages = response.data or []

    return [
        passage
        for passage in passages
        if float(passage.get("similarity") or 0) >= MIN_SIMILARITY
    ]


def format_passages(passages):
    if not passages:
        return ""

    sections = []

    for passage in passages:
        page = passage.get("page_number")
        content = (passage.get("content") or "").strip()

        if not content:
            continue

        source = (
            f"ICAR Handbook of Fisheries and Aquaculture, page {page}"
            if page is not None
            else "ICAR Handbook of Fisheries and Aquaculture"
        )

        sections.append(f"[Source: {source}]\n{content}")

    return "\n\n".join(sections)

def generate_hf_answer(question: str, context: str) -> str:
    import os
    import httpx

    token = os.getenv("HF_TOKEN")
    if not token:
        raise RuntimeError("HF_TOKEN is not configured.")

    url = (
        "https://gayathri-sanjana-meenaai-api.hf.space/"
        "gradio_api/call/answer_question"
    )

    response = httpx.post(
        url,
        json={
            "data": [question, context],
        },
        headers={"Authorization": f"Bearer {token}"},
        timeout=120.0,
    )
    response.raise_for_status()
    event_id = response.json()["event_id"]

    result = httpx.get(
        f"{url}/{event_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=120.0,
    )
    result.raise_for_status()

    for line in result.text.splitlines():
        if line.startswith("data:"):
            import json
            payload = json.loads(line[5:].strip())
            if payload and isinstance(payload[0], str):
                return payload[0]

    raise RuntimeError("Hugging Face returned no answer.")
