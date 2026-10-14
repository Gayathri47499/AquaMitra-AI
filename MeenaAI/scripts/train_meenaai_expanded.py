import json
from pathlib import Path
import torch
from datasets import Dataset
from unsloth import FastLanguageModel
from trl import SFTTrainer, SFTConfig

DATA = Path("data/meenaai_expanded_provisional.jsonl")
OUTPUT = "models/meenaai-expanded-adapter"
MAX_SEQ_LENGTH = 1024

rows = []
with DATA.open(encoding="utf-8") as f:
    for line in f:
        r = json.loads(line)
        q = str(r.get("question", "")).strip()
        a = str(r.get("answer", "")).strip()
        if q and a:
            rows.append({"text": f"### Question:\n{q}\n\n### Answer:\n{a}"})

if not rows:
    raise RuntimeError("No training examples found.")

print(f"Training examples: {len(rows)}")
print(f"GPU: {torch.cuda.get_device_name(0)}")

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="Qwen/Qwen3-4B-Instruct-2507",
    max_seq_length=MAX_SEQ_LENGTH,
    load_in_4bit=True,
)

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

args = SFTConfig(
    output_dir="results/meenaai-expanded-training",
    max_length=MAX_SEQ_LENGTH,
    per_device_train_batch_size=1,
    gradient_accumulation_steps=4,
    num_train_epochs=2,
    learning_rate=2e-4,
    lr_scheduler_type="cosine",
    warmup_ratio=0.03,
    logging_steps=10,
    save_strategy="epoch",
    save_total_limit=2,
    optim="adamw_8bit",
    gradient_checkpointing=True,
    bf16=torch.cuda.is_bf16_supported(),
    fp16=not torch.cuda.is_bf16_supported(),
    report_to="none",
    seed=42,
    data_seed=42,
    dataset_num_proc=2,
)

trainer = SFTTrainer(
    model=model,
    train_dataset=Dataset.from_list(rows),
    processing_class=tokenizer,
    args=args,
)

print("Starting expanded QLoRA training...")
trainer.train()

Path(OUTPUT).mkdir(parents=True, exist_ok=True)
model.save_pretrained(OUTPUT)
tokenizer.save_pretrained(OUTPUT)

print("\nEXPANDED TRAINING COMPLETED")
print("Adapter:", OUTPUT)
print("Training examples:", len(rows))
print("Global steps:", trainer.state.global_step)
print("Training loss history:", [
    x["loss"] for x in trainer.state.log_history if "loss" in x
])
print("NOTE: Experimental model; verify answers before production use.")
