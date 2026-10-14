import os
import torch
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from unsloth import FastLanguageModel

ADAPTER_PATH = os.getenv(
    "MEENAAI_ADAPTER",
    "models/meenaai-12000-adapter"
)

app = FastAPI(
    title="MeenaAI API",
    description="Aquaculture question-answering assistant",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict this before public deployment
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

model = None
tokenizer = None

class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)

class ChatResponse(BaseModel):
    answer: str
    model: str = "MeenaAI QLoRA 12000"

@app.on_event("startup")
def load_model():
    global model, tokenizer
    if not Path(ADAPTER_PATH).exists():
        raise RuntimeError(f"Adapter directory not found: {ADAPTER_PATH}")

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=ADAPTER_PATH,
        max_seq_length=1024,
        load_in_4bit=True,
    )
    FastLanguageModel.for_inference(model)

@app.get("/health")
def health():
    return {
        "status": "ok" if model is not None else "loading",
        "model": "MeenaAI QLoRA 12000",
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU",
    }

@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    if model is None or tokenizer is None:
        raise HTTPException(status_code=503, detail="Model is not loaded")

    prompt = (
        "You are MeenaAI, an aquaculture information assistant. "
        "Give clear, cautious answers. Do not invent facts. "
        "For fish deaths, disease outbreaks, or suspected toxins, "
        "recommend promptly contacting a fisheries officer or aquatic veterinarian.\n\n"
        f"### Question:\n{request.question.strip()}\n\n### Answer:\n"
    )

    inputs = tokenizer(
        prompt, return_tensors="pt", truncation=True, max_length=900
    ).to("cuda" if torch.cuda.is_available() else "cpu")

    with torch.inference_mode():
        output = model.generate(
            **inputs,
            max_new_tokens=220,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )

    answer = tokenizer.decode(
        output[0][inputs["input_ids"].shape[1]:],
        skip_special_tokens=True,
    ).strip()

    return ChatResponse(answer=answer or "I couldn't generate an answer. Please try again.")
