import os
import re
import uuid
from google import genai
from functools import lru_cache

import httpx
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

from pathlib import Path

load_dotenv(Path(__file__).resolve().parent / ".env")


# ==========================================================
# LOAD ENVIRONMENT VARIABLES
# ==========================================================

load_dotenv()


SUPABASE_URL = os.getenv("SUPABASE_URL")

SUPABASE_PUBLISHABLE_KEY = os.getenv(
    "SUPABASE_PUBLISHABLE_KEY"
)

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
# GEMINI CLIENT HELPERS FOR ANSWER GENERATION
# ==========================================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-3.5-flash-lite"


@lru_cache(maxsize=1)
def get_gemini_client():
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured.")
    return genai.Client(api_key=GEMINI_API_KEY)

def is_aquaculture_question(question: str) -> bool:
    text = question.lower()

    keywords = [
        "fish", "fishing", "aquaculture", "aquaculture",
        "pond", "prawn", "shrimp", "hatchery", "fingerling",
        "fish farm", "fish farming", "stocking", "fish feed",
        "feeding", "dissolved oxygen", "water quality",
        "ammonia", "nitrite", "ph", "algae", "fish disease",
        "fish health", "tilapia", "rohu", "catla", "carp",
        "biofloc", "aquaponics", "gill", "fish pond",
        "fish growth", "fish mortality", "fish death",
    ]

    return any(keyword in text for keyword in keywords)


def ask_meena(question: str, context: str) -> str:
    client = get_gemini_client()

    if context and context.strip():
        reference_section = (
            "Use the following retrieved aquaculture information "
            "as supporting evidence where relevant. The passages "
            "may not answer every part of the question.\n\n"
            + context.strip()
        )
    else:
        reference_section = (
            "No relevant reference passages were retrieved. "
            "Use your general knowledge of aquaculture cautiously. "
            "Do not invent citations, precise facts, or dosages."
        )

    prompt = f"""
You are MeenaMitra, a friendly, practical AI assistant for fish
farmers. Your goal is to help farmers make better-informed
decisions, not to summarize documents.

HOW TO RESPOND
1. Understand what the farmer actually wants to know.
2. Start with a direct, useful answer in natural, conversational
   English.
3. Give practical suggestions and explain briefly why they help.
4. Adapt your advice to the fish species, size, pond conditions,
   and symptoms when that information is available.
5. If important details are missing, ask one or two relevant
   follow-up questions after giving safe general guidance.
6. Use short paragraphs and bullets when they improve readability.
7. Avoid repetitive introductions, robotic wording, and unnecessary
   disclaimers.


HOW TO USE REFERENCE INFORMATION
- Use relevant reference passages internally to improve the accuracy
  and usefulness of your answer.
- Your primary job is to help the farmer, not to describe your sources.
- Do not mention the handbook, documents, retrieved passages, RAG,
  or knowledge base in ordinary answers.
- Do not include citations, page numbers, or source labels by default.
- Explain recommendations directly in your own natural, conversational
  style, as a knowledgeable aquaculture assistant would.
- Only discuss a source if the farmer explicitly asks where information
  came from or requests references.
- Never invent facts or pretend unsupported claims are verified.
- If information is uncertain, explain the uncertainty naturally.
- If reference information is insufficient, use cautious general
  aquaculture knowledge where appropriate, or ask a useful follow-up.


SAFETY
- Never invent medicine, chemical, or treatment dosages.
- For sudden fish deaths, severe illness, or widespread distress,
  recommend urgent help from a fisheries officer or aquatic animal
  health professional.
- You may suggest safe observations and water-quality checks.
- Do not claim a diagnosis without enough information.

SCOPE
- You specialize in fish farming and aquaculture.
- For unrelated questions, politely explain your specialization
  and invite the user to ask an aquaculture question.

{reference_section}

FARMER'S QUESTION:
{question}

Now answer the farmer directly as MeenaMitra.
"""

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )

    answer = response.text

    if not answer or not answer.strip():
        raise RuntimeError("Gemini returned an empty response.")

    return answer.strip()


# ==========================================================
# FASTAPI APP
# ==========================================================

app = FastAPI(
    title="MeenaMitra API",
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
        "\u0c00" <= char <= "\u0c7f"
        for char in text
    )


# ==========================================================
# MODEL OUTPUT CLEANER
# ==========================================================

def clean_model_output(text: str) -> str:
    """
    Clean unwanted multilingual/random characters from
    the small language model output.
    """

    if not text:
        return (
            "I could not generate a reliable answer. "
            "Please ask your fish-farming question again."
        )

    lines = text.splitlines()

    cleaned_lines = []

    for line in lines:

        line = line.strip()

        if not line:
            continue

        # Remove CJK characters
        if re.search(
            r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]",
            line
        ):
            line = re.sub(
                r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]",
                " ",
                line
            )

        # Remove Arabic characters
        line = re.sub(
            r"[\u0600-\u06ff]",
            " ",
            line
        )

        # Remove Korean characters
        line = re.sub(
            r"[\uac00-\ud7af]",
            " ",
            line
        )

        # Remove Telugu characters
        line = re.sub(
            r"[\u0c00-\u0c7f]",
            " ",
            line
        )

        # Remove any remaining non-ASCII characters
        line = re.sub(
            r"[^\x00-\x7F]",
            " ",
            line
        )

        line = re.sub(
            r"\s+",
            " ",
            line
        ).strip()

        if not line:
            continue

        english_letters = len(
            re.findall(
                r"[A-Za-z]",
                line
            )
        )

        if english_letters >= 4:
            cleaned_lines.append(line)

    cleaned = " ".join(cleaned_lines).strip()

    cleaned = re.sub(
        r"\bWhy should you check water quality.*$",
        "",
        cleaned,
        flags=re.IGNORECASE
    ).strip()

    cleaned = re.sub(
        r"\bWhat should I check first.*$",
        "",
        cleaned,
        flags=re.IGNORECASE
    ).strip()

    cleaned = re.sub(
        r"\bWhat else.*\?$",
        "",
        cleaned,
        flags=re.IGNORECASE
    ).strip()

    cleaned = re.sub(
        r"\s+",
        " ",
        cleaned
    ).strip()

    if len(cleaned) < 20:

        return (
            "If fish are coming to the surface and gasping for air, "
            "check the dissolved oxygen level and water quality immediately. "
            "Increase aeration and check whether the pond is overcrowded. "
            "Avoid overfeeding until the water condition is stable."
        )

    return cleaned


# ==========================================================
# ROOT
# ==========================================================

@app.get("/")
def root():

    return {
        "message": "MeenaMitra API is running",
        "model": "Gemini 3.5 Flash Lite",
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
            "MeenaMitra currently supports English-language "
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
            "I'm MeenaMitra, an AI assistant specializing in "
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
                "MeenaMitra is temporarily unable to generate an answer. "
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