import torch
from unsloth import FastLanguageModel

model_name = "Qwen/Qwen3-4B-Instruct-2507"

print("Loading Qwen model in 4-bit mode...")
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=model_name,
    max_seq_length=1024,
    load_in_4bit=True,
    dtype=None,
)

print("MODEL LOADED SUCCESSFULLY")
print("GPU:", torch.cuda.get_device_name(0))
print("VRAM allocated:", round(torch.cuda.memory_allocated(0) / 1024**3, 2), "GB")

messages = [{"role": "user", "content": "What is aquaculture?"}]
inputs = tokenizer.apply_chat_template(
    messages,
    tokenize=True,
    add_generation_prompt=True,
    return_tensors="pt",
).to("cuda")

with torch.no_grad():
    output = model.generate(inputs, max_new_tokens=60)

print("MODEL RESPONSE:")
print(tokenizer.decode(output[0][inputs.shape[-1]:], skip_special_tokens=True))
