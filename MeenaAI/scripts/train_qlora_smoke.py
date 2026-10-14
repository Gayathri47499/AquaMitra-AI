import json
import torch
from pathlib import Path
from datasets import Dataset
from transformers import Trainer, TrainingArguments, DataCollatorForLanguageModeling
from unsloth import FastLanguageModel

BASE_MODEL = "Qwen/Qwen3-4B-Instruct-2507"
DATA_FILE = Path("data/qlora_smoke_test.jsonl")
OUTPUT_DIR = Path("results/qlora_smoke_test_adapter")

if not torch.cuda.is_available():
    raise RuntimeError("CUDA GPU is not available")

rows = [json.loads(line) for line in DATA_FILE.open(encoding="utf-8") if line.strip()]
if not rows:
    raise RuntimeError("Smoke-test dataset is empty")

print("Loading model...")
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=BASE_MODEL,
    max_seq_length=512,
    load_in_4bit=True,
    dtype=None,
)

if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

model = FastLanguageModel.get_peft_model(
    model,
    r=16,
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
    lora_alpha=32,
    lora_dropout=0,
    bias="none",
    use_gradient_checkpointing="unsloth",
    random_state=42,
)

texts = [
    "### Question:\n" + r["question"]
    + "\n\n### Answer:\n" + r["answer"] + tokenizer.eos_token
    for r in rows
]

def tokenize(batch):
    return tokenizer(
        batch["text"],
        truncation=True,
        max_length=512,
        padding=False,
    )

dataset = Dataset.from_dict({"text": texts}).map(
    tokenize,
    batched=True,
    remove_columns=["text"],
)

args = TrainingArguments(
    output_dir=str(OUTPUT_DIR),
    per_device_train_batch_size=1,
    gradient_accumulation_steps=1,
    max_steps=5,
    learning_rate=2e-4,
    logging_steps=1,
    save_strategy="no",
    report_to="none",
    bf16=torch.cuda.is_bf16_supported(),
    fp16=not torch.cuda.is_bf16_supported(),
    optim="adamw_torch",
    seed=42,
    dataloader_num_workers=0,
)

trainer = Trainer(
    model=model,
    args=args,
    train_dataset=dataset,
    data_collator=DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,
    ),
)

print("Starting 5-step QLoRA smoke test...")
trainer.train()

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
model.save_pretrained(str(OUTPUT_DIR))
tokenizer.save_pretrained(str(OUTPUT_DIR))

print("SMOKE TEST TRAINING COMPLETED")
print("Adapter saved to:", OUTPUT_DIR)
print("Training rows:", len(rows))
print("Steps:", trainer.state.global_step)
print("Peak GPU memory (GB):", round(torch.cuda.max_memory_allocated() / 1024**3, 2))
print("NOTE: Pipeline test only; dataset has not been approved for production training.")
