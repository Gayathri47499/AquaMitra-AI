
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

    return create_client(
        SUPABASE_URL,
        SUPABASE_SECRET_KEY
    )


@lru_cache(maxsize=1)
def get_embedding_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(
        "sentence-transformers/all-MiniLM-L6-v2",
        device="cpu"
    )


def retrieve_passages(question: str, top_k: int = TOP_K):
    if not question or not question.strip():
        return []

    model = get_embedding_model()
    embedding = model.encode(
        question.strip(),
        normalize_embeddings=True
    ).tolist()

    response = get_supabase().rpc(
        "match_knowledge_passages",
        {
            "query_embedding": embedding,
            "match_count": min(max(top_k, 1), 10),
            "filter_document_id": DOCUMENT_ID,
        },
    ).execute()

    passages = response.data or []

    relevant = [
        passage
        for passage in passages
        if float(passage.get("similarity", 0.0))
        >= MIN_SIMILARITY
    ]

    return relevant


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
            f"ICAR Handbook of Fisheries and Aquaculture, "
            f"page {page}"
            if page is not None
            else "ICAR Handbook of Fisheries and Aquaculture"
        )

        sections.append(
            f"[Source: {source}]\n{content}"
        )

    return "\n\n".join(sections)
