
import os
from functools import lru_cache

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

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


def retrieve_passages(question: str, top_k: int = TOP_K):
    """Temporarily skip vector retrieval until a compatible remote
    embedding service is configured. Do not query MiniLM vectors
    with embeddings from a different model.
    """
    if not question or not question.strip():
        return []

    # Safe fallback: Gemini can still answer without retrieved context.
    return []


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
