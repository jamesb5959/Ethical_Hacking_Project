from functools import lru_cache
import os

MODEL_NAME = os.environ.get("MODEL_NAME", "google/gemma-2-2b")


@lru_cache(maxsize=1)
def load_model():
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    torch._dynamo.config.suppress_errors = True

    print(f"[inference] Loading model from {MODEL_NAME}", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    if torch.cuda.is_available():
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME,
            torch_dtype=torch.float16,
            device_map="auto",
        )
        device = next(model.parameters()).device
    else:
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME,
            torch_dtype=torch.float32,
            low_cpu_mem_usage=False,
        )
        device = torch.device("cpu")
        model.to(device)

    print(f"[inference] Model loaded on {device}", flush=True)
    return tokenizer, model, device


def generate_response(prompt: str, max_new_tokens: int = 150) -> str:
    tokenizer, model, device = load_model()
    inputs = tokenizer(prompt, return_tensors="pt").to(device)
    prompt_len = inputs.input_ids.shape[-1]
    outputs = model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        pad_token_id=tokenizer.eos_token_id,
        do_sample=False,
        top_p=1.0,
    )
    gen_ids = outputs[0][prompt_len:]
    raw = tokenizer.decode(gen_ids, skip_special_tokens=True).strip()

    cleaned = []
    for line in raw.splitlines():
        if line.startswith("System: "):
            cleaned.append(line[len("System: "):])
        elif line.startswith("User: "):
            continue
        else:
            cleaned.append(line)
    return "\n".join(cleaned).strip()
