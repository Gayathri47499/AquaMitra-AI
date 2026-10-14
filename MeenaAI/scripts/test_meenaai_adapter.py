import torch
from unsloth import FastLanguageModel

ADAPTER = "models/meenaai-expanded-adapter"

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=ADAPTER,
    max_seq_length=1024,
    load_in_4bit=True,
)

FastLanguageModel.for_inference(model)

questions = [
    "What is aquaculture?",
    "Why is dissolved oxygen important in fish farming?",
    "What should a fish farmer do if fish are suddenly dying in a pond?",
]

for i, question in enumerate(questions, 1):
    prompt = f"### Question:\n{question}\n\n### Answer:\n"
    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")

    with torch.inference_mode():
        output = model.generate(
            **inputs,
            max_new_tokens=160,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )

    new_tokens = output[0][inputs["input_ids"].shape[1]:]
    answer = tokenizer.decode(new_tokens, skip_special_tokens=True)

    print(f"\n{'=' * 60}")
    print(f"TEST {i}: {question}")
    print(f"ANSWER: {answer.strip()}")

print("\nADAPTER INFERENCE TEST COMPLETED")
