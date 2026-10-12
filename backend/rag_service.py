import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv(override=False)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_PUBLISHABLE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY")

supabase = None
if SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY)

TOP_K = 5

def retrieve_passages(question: str, top_k: int = TOP_K):
    """
    Lightweight placeholder for retrieval on Render 
    to prevent memory/PyTorch crashes.
    """
    return []

def format_passages(passages) -> str:
    """
    Format retrieved passages into a context string for Gemini.
    """
    if not passages:
        return ""
    
    sections = []
    for p in passages:
        source_label = f"[Source: {p.get('source', 'Handbook')}, Page {p.get('page', 'N/A')}]"
        text_content = p.get('content', '').strip()
        sections.append(f"{source_label}\n{text_content}")
        
    return "\n\n".join(sections)