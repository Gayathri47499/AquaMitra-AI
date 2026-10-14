import os
import re
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client as SupabaseClient

try:
    from backend.rag_service import (
        retrieve_passages,
        format_passages,
        generate_hf_answer,
    )
except ModuleNotFoundError:
    from rag_service import (
        retrieve_passages,
        format_passages,
        generate_hf_answer,
    )


load_dotenv(Path(__file__).resolve().parent / ".env")


# ==========================================================
# LOAD ENVIRONMENT VARIABLES
# ==========================================================

load_dotenv()


SUPABASE_URL = os.getenv("SUPABASE_URL")

SUPABASE_PUBLISHABLE_KEY = os.getenv(
    "SUPABASE_PUBLISHABLE_KEY"
)

# Name kept as configured on the hosting service.
MEENAMITRA_SPACE_ID = os.getenv(
    "MEENAMITRA_SPACE_ID"
)

HF_TOKEN = os.getenv("HF_TOKEN")


# ==========================================================
# VALIDATE ENVIRONMENT VARIABLES
# ==========================================================

if not SUPABASE_URL:
    raise RuntimeError(
        "SUPABASE_URL is missing"
    )


if not SUPABASE_PUBLISHABLE_KEY:
    raise RuntimeError(
        "SUPABASE_PUBLISHABLE_KEY is missing"
    )


if not MEENAMITRA_SPACE_ID:
    raise RuntimeError(
        "MEENAMITRA_SPACE_ID is missing"
    )


# ==========================================================
# SUPABASE CLIENT
# ==========================================================

supabase: SupabaseClient = create_client(
    SUPABASE_URL,
    SUPABASE_PUBLISHABLE_KEY
)


# ==========================================================
# SCOPE CHECK
# ==========================================================

def is_aquaculture_question(question: str) -> bool:
    text = question.lower()

    keywords = [
        "fish", "fishing", "aquaculture",
        "pond", "prawn", "shrimp", "hatchery", "fingerling",
        "fish farm", "fish farming", "stocking", "fish feed",
        "feeding", "dissolved oxygen", "water quality",
        "ammonia", "nitrite", "ph", "algae", "fish disease",
        "fish health", "tilapia", "rohu", "catla", "carp",
        "biofloc", "aquaponics", "gill", "fish pond",
        "fish growth", "fish mortality", "fish death",
    ]

    return any(keyword in text for keyword in keywords)


# ==========================================================
# FASTAPI APP
# ==========================================================

app = FastAPI(
    title="AquaMitra AI API",
    description="AI-powered aquaculture advisor",
    version="1.0.0"
)


# ==========================================================
# CORS
# ==========================================================

app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],

    allow_origin_regex=r"https://.*\.vercel\.app",

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)


# ==========================================================
# REQUEST MODELS
# ==========================================================

class AuthRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class ChatRequest(BaseModel):
    question: str
    access_token: str
    conversation_id: str | None = None


# ==========================================================
# LANGUAGE DETECTION
# ==========================================================

def contains_telugu(text: str) -> bool:
    """
    Detect Telugu Unicode characters.

    Telugu Unicode range:
    U+0C00 - U+0C7F
    """

    return any(
        "ఀ" <= char <= "౿"
        for char in text
    )


# ==========================================================
# MODEL OUTPUT CLEANER
# ==========================================================

# Follow-up lines the model sometimes adds at the end of an answer.
JUNK_LINE_STARTS = (
    "why should you check water quality",
    "what should i check first",
    "what else",
)


def clean_model_output(text: str) -> str:
    """
    Clean the model output but keep its structure:
    line breaks, numbered steps, bullets, and normal punctuation.
    Only removes chat-template leftovers, hidden reasoning,
    characters from scripts the model drifts into, and control characters.
    """

    if not text or not text.strip():
        return (
            "I could not generate a reliable answer. "
            "Please ask your fish-farming question again."
        )

    # Remove chat-template leftovers and hidden reasoning, if any
    text = re.sub(r"<\|im_start\|>|<\|im_end\|>|<\|endoftext\|>", "", text)
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)

    # Remove characters from scripts the model sometimes drifts into
    text = re.sub(
        r"[぀-ヿ㐀-䶿一-鿿"
        r"؀-ۿ가-힯ఀ-౿]",
        "",
        text,
    )

    # Remove control characters but keep line breaks and tabs
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    # Replace typographic characters with plain ASCII
    for old, new in {
        "‘": "'", "’": "'",
        "“": '"', "”": '"',
        "–": "-", "—": "-",
        "•": "-", " ": " ",
    }.items():
        text = text.replace(old, new)

    lines = []
    for raw in text.replace("\r", "\n").split("\n"):
        line = re.sub(r"[ \t]+", " ", raw).strip()

        if not line:
            # keep at most one blank line between blocks
            if lines and lines[-1] != "":
                lines.append("")
            continue

        # skip lines with no letters or numbers, such as a lone "-"
        if not re.search(r"[A-Za-z0-9]", line):
            continue

        # skip follow-up questions the model sometimes adds at the end
        if line.lower().lstrip("*#- ").startswith(JUNK_LINE_STARTS):
            continue

        lines.append(line)

    cleaned = "\n".join(lines).strip()

    if len(cleaned) < 20:
        return (
            "I could not produce a complete answer for that question. "
            "Please rephrase it, or ask a more specific aquaculture question."
        )

    return cleaned


# ==========================================================
# ROOT
# ==========================================================

@app.get("/")
def root():

    return {
        "message": "AquaMitra AI API is running",
        "model": "Qwen3-4B-Instruct-2507 with LoRA adapter (Hugging Face Space)",
        "language": "English"
    }


# ==========================================================
# HEALTH
# ==========================================================

@app.get("/health")
def health():

    return {
        "status": "ok"
    }


@app.head("/health")
def health_head():

    return None


# ==========================================================
# SIGNUP
# ==========================================================

@app.post("/signup")
def signup(data: AuthRequest):

    try:

        result = supabase.auth.sign_up(
            {
                "email": data.email,
                "password": data.password
            }
        )

        session = result.session
        user = result.user

        if not user:

            raise HTTPException(
                status_code=400,
                detail="Signup failed"
            )

        response = {
            "message": "Signup successful",
            "email": user.email
        }

        if session:

            response["access_token"] = (
                session.access_token
            )

            response["refresh_token"] = (
                session.refresh_token
            )

        return response

    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )


# ==========================================================
# LOGIN
# ==========================================================

@app.post("/login")
def login(data: AuthRequest):

    try:

        result = supabase.auth.sign_in_with_password(
            {
                "email": data.email,
                "password": data.password
            }
        )

        if not result.session:

            raise HTTPException(
                status_code=401,
                detail="Login failed"
            )

        return {
            "message": "Login successful",

            "access_token":
                result.session.access_token,

            "refresh_token":
                result.session.refresh_token,

            "email":
                result.user.email
                if result.user
                else data.email
        }

    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=401,
            detail=str(e)
        )


# ==========================================================
# REFRESH ACCESS TOKEN
# ==========================================================

@app.post("/refresh")
def refresh_token(
    data: RefreshRequest
):

    try:

        result = supabase.auth.refresh_session(
            data.refresh_token
        )

        if not result.session:

            raise HTTPException(
                status_code=401,
                detail="Could not refresh session"
            )

        return {
            "message": "Token refreshed",

            "access_token":
                result.session.access_token,

            "refresh_token":
                result.session.refresh_token,

            "email":
                result.user.email
                if result.user
                else None
        }

    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=401,
            detail=str(e)
        )


# ==========================================================
# CHAT
# ==========================================================

@app.post("/chat")
async def chat(data: ChatRequest):

    question = data.question.strip()

    if not question:

        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty"
        )


    # ======================================================
    # 1. VERIFY USER
    # ======================================================

    try:

        user_result = supabase.auth.get_user(
            data.access_token
        )

        if (
            not user_result
            or not user_result.user
        ):

            raise HTTPException(
                status_code=401,
                detail="Invalid authentication token"
            )

        user_id = user_result.user.id

    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed: {str(e)}"
        )


    # ======================================================
    # 2. GET OR CREATE CONVERSATION ID
    # ======================================================

    if data.conversation_id:

        conversation_id = data.conversation_id

        try:

            existing = (
                supabase
                .table("chat_history")
                .select("id")
                .eq(
                    "conversation_id",
                    conversation_id
                )
                .eq(
                    "user_id",
                    user_id
                )
                .limit(1)
                .execute()
            )

            if not existing.data:

                raise HTTPException(
                    status_code=403,
                    detail="Conversation does not belong to this user"
                )

        except HTTPException:
            raise

        except Exception as e:

            raise HTTPException(
                status_code=500,
                detail=(
                    "Could not verify conversation: "
                    f"{str(e)}"
                )
            )

    else:

        conversation_id = str(
            uuid.uuid4()
        )


    # ======================================================
    # 3. ENGLISH-ONLY MODE CHECK
    # ======================================================

    if contains_telugu(question):

        answer = (
            "AquaMitra AI currently supports English-language "
            "aquaculture guidance. Telugu support is planned "
            "for a future model improvement. Please ask your "
            "fish-farming question in English."
        )

        try:

            save_result = (
                supabase
                .table("chat_history")
                .insert(
                    {
                        "user_id": user_id,
                        "conversation_id": conversation_id,
                        "question": question,
                        "answer": answer
                    }
                )
                .execute()
            )

            if not save_result.data:
                raise Exception("Supabase did not return saved record")

        except Exception as e:
            print("HISTORY SAVE ERROR:", str(e))
            raise HTTPException(
                status_code=500,
                detail=(
                    "The request was processed, but "
                    "the conversation could not be saved: "
                    f"{str(e)}"
                )
            )

        return {
            "conversation_id": conversation_id,
            "question": question,
            "answer": answer
        }

    # AQUACULTURE SCOPE CHECK
    if not is_aquaculture_question(question):
        answer = (
            "I'm AquaMitra AI, an assistant specializing in "
            "fish farming and aquaculture. I can help with pond "
            "management, water quality, fish feeding, fish health, "
            "breeding, and farm practices. Please ask an "
            "aquaculture-related question."
        )

        try:
            supabase.table("chat_history").insert({
                "user_id": user_id,
                "conversation_id": conversation_id,
                "question": question,
                "answer": answer
            }).execute()
        except Exception as e:
            print("HISTORY SAVE ERROR:", repr(e))

        return {
            "conversation_id": conversation_id,
            "question": question,
            "answer": answer
        }


    # ======================================================
    # 4. RETRIEVE REFERENCE PASSAGES AND GENERATE ANSWER
    # ======================================================

    try:
        passages = retrieve_passages(question, top_k=5)
        context = format_passages(passages)

        answer = generate_hf_answer(question, context)

    except Exception as e:
        print("RAG OR HF ERROR:", repr(e))
        raise HTTPException(
            status_code=502,
            detail=(
                "AquaMitra AI is temporarily unable to generate an answer. "
                "Please try again shortly."
            )
        )


    # ======================================================
    # 5. CLEAN MODEL OUTPUT
    # ======================================================

    answer = clean_model_output(answer)


    # ======================================================
    # 6. SAVE TO SUPABASE
    # ======================================================

    try:

        save_result = (
            supabase
            .table("chat_history")
            .insert(
                {
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                    "question": question,
                    "answer": answer
                }
            )
            .execute()
        )

        if not save_result.data:
            raise Exception("Supabase did not return saved record")

    except Exception as e:

        print("HISTORY SAVE ERROR:", str(e))

        raise HTTPException(
            status_code=500,
            detail=(
                "AI answered successfully, but "
                "the conversation could not be saved: "
                f"{str(e)}"
            )
        )


    # ======================================================
    # 7. RETURN RESPONSE
    # ======================================================

    return {
        "conversation_id": conversation_id,
        "question": question,
        "answer": answer
    }


# ==========================================================
# HISTORY
# ==========================================================

@app.get("/history")
def history(
    authorization: str | None = Header(default=None)
):

    if not authorization:

        raise HTTPException(
            status_code=401,
            detail="Authorization header is missing"
        )

    if not authorization.startswith("Bearer "):

        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header"
        )

    access_token = authorization[
        len("Bearer "):
    ].strip()

    if not access_token:

        raise HTTPException(
            status_code=401,
            detail="Access token is missing"
        )

    try:

        user_result = supabase.auth.get_user(
            access_token
        )

        if (
            not user_result
            or not user_result.user
        ):

            raise HTTPException(
                status_code=401,
                detail="Invalid authentication token"
            )

        user_id = user_result.user.id

    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed: {str(e)}"
        )

    try:

        result = (
            supabase
            .table("chat_history")
            .select(
                "id, conversation_id, question, answer, created_at"
            )
            .eq(
                "user_id",
                user_id
            )
            .order(
                "created_at",
                desc=True
            )
            .execute()
        )

        rows = result.data or []

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to load chat history: "
                f"{str(e)}"
            )
        )

    conversations = {}

    for row in rows:

        conversation_id = row[
            "conversation_id"
        ]

        if conversation_id not in conversations:

            conversations[
                conversation_id
            ] = {

                "conversation_id":
                    conversation_id,

                "title":
                    row["question"],

                "created_at":
                    row["created_at"],

                "messages":
                    []
            }

        conversations[
            conversation_id
        ]["messages"].append(

            {
                "id":
                    row["id"],

                "question":
                    row["question"],

                "answer":
                    row["answer"],

                "created_at":
                    row["created_at"]
            }
        )

    return {

        "history":
            list(
                conversations.values()
            )
    }


@app.delete("/history/{conversation_id}")
def delete_conversation(
    conversation_id: str,
    authorization: str | None = Header(default=None),
):
    """Delete a conversation belonging to the authenticated user."""

    # Validate the authorization header.
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Valid authorization header is required",
        )

    access_token = authorization[len("Bearer "):].strip()

    if not access_token:
        raise HTTPException(
            status_code=401,
            detail="Access token is missing",
        )

    # Verify the logged-in user.
    try:
        user_result = supabase.auth.get_user(access_token)

        if not user_result or not user_result.user:
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication token",
            )

        user_id = user_result.user.id

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Authentication failed",
        )

    # Delete only this user's selected conversation.
    try:
        result = (
            supabase.table("chat_history")
            .delete()
            .eq("user_id", user_id)
            .eq("conversation_id", conversation_id)
            .execute()
        )

        if not result.data:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found",
            )

        return {
            "message": "Conversation deleted successfully",
            "conversation_id": conversation_id,
        }

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to delete conversation",
        )