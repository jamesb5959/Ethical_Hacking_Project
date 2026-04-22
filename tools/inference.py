import torch
torch._dynamo.config.suppress_errors = True
from transformers import AutoTokenizer, AutoModelForCausalLM

tokenizer = AutoTokenizer.from_pretrained("google/gemma-2-2b")
model     = AutoModelForCausalLM.from_pretrained(
    "google/gemma-2-2b",
    torch_dtype=torch.float16,
    device_map="auto",
)
device = next(model.parameters()).device
print(f"[inference] Model loaded on {device}")

def generate_response(prompt: str, max_new_tokens: int = 150) -> str:
    inputs     = tokenizer(prompt, return_tensors="pt").to(device)
    prompt_len = inputs.input_ids.shape[-1]
    outputs    = model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        pad_token_id=tokenizer.eos_token_id,
        do_sample=False, top_p=1.0,
    )
    gen_ids = outputs[0][prompt_len:]
    raw     = tokenizer.decode(gen_ids, skip_special_tokens=True).strip()

    cleaned = []
    for line in raw.splitlines():
        if line.startswith("System: "):
            cleaned.append(line[len("System: "):])
        elif line.startswith("User: "):
            continue
        else:
            cleaned.append(line)
    return "\n".join(cleaned).strip()

