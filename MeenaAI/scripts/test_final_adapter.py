import torch
from unsloth import FastLanguageModel

ADAPTER = "models/meenaai-12000-adapter"

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=ADAPTER,
    max_seq_length=1024,
    load_in_4bit=True,
)
FastLanguageModel.for_inference(model)

questions = [
    "What is aquaculture?",
    "Why is dissolved oxygen important in a fish pond?",
    "What water quality factors should a fish farmer monitor?",
]

results = []
for i, question in enumerate(questions, 1):
    prompt = f"### Question:\n{question}\n\n### Answer:\n"
    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")

    with torch.inference_mode():
        output = model.generate(
            **inputs,
            max_new_tokens=120,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )

    answer = tokenizer.decode(
        output[0][inputs["input_ids"].shape[1]:],
        skip_special_tokens=True,
    ).strip()

    results.append({"question": question, "answer": answer})
    print(f"\nTEST {i}: {question}\nANSWER: {answer}\n")

import json
from pathlib import Path
Path("results").mkdir(exist_ok=True)
Path("results/final_adapter_smoke_test.json").write_text(
    json.dumps(results, indent=2, ensure_ascii=False),
    encoding="utf-8",
)
print("Test results saved to results/final_adapter_smoke_test.json")
