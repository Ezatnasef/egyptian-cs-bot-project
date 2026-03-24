"""
Professional LLM Fine-Tuning Script using Unsloth & Llama 3 8B
"""
import torch
import json
from pathlib import Path
from datasets import Dataset
from unsloth import FastLanguageModel
from trl import SFTTrainer
from transformers import TrainingArguments

# ========================= 
# 1. Model Config
# =========================
max_seq_length = 2048
dtype = None        # Auto detect
load_in_4bit = True # For RTX 3060/4060

# ✅ Option A: Llama 3 via Unsloth mirror (no HF gating needed)
model_name = "unsloth/Meta-Llama-3-8B-Instruct-bnb-4bit" 

# ✅ Option B: Smaller/faster for testing
# model_name = "unsloth/Llama-3.2-3B-Instruct-bnb-4bit"

# ✅ Option C: Best Arabic support, fully open
# model_name = "unsloth/Qwen2.5-7B-Instruct-bnb-4bit"

print(f"Loading Base Model: {model_name}...")

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=model_name,
    max_seq_length=max_seq_length,
    dtype=dtype,
    load_in_4bit=load_in_4bit,
)

# =========================
# 2. LoRA Adapters
# =========================
model = FastLanguageModel.get_peft_model(
    model,
    r=16,
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
    lora_alpha=16,
    lora_dropout=0,
    bias="none",
    use_gradient_checkpointing="unsloth",
    random_state=3407,
    use_rslora=False,
    loftq_config=None,
)

# =========================
# 3. Dataset
# =========================
DATASET_PATH = Path(__file__).parent / "dataset" / "egyptian_cs_dataset.json"

# ✅ Llama 3 uses different chat tokens than Llama 2
LLAMA3_PROMPT = """<|begin_of_text|><|start_header_id|>system<|end_header_id|>

أنت موظف خدمة عملاء مصري محترف. أجب باختصار وبلهجة العميل بناءً على السياق الآتي.
المجال: {}
اللهجة: {}<|eot_id|><|start_header_id|>user<|end_header_id|>

{}<|eot_id|><|start_header_id|>assistant<|end_header_id|>

{}<|eot_id|>"""

def format_prompts(examples):
    instructions = []

    for domain, dialect, conv in zip(
        examples["domain"],
        examples["dialect"],
        examples["conversation"]
    ):
        customer_text = ""
        agent_text = ""

        for turn in conv:
            if turn["role"] == "customer":
                customer_text = turn["text"]
            elif turn["role"] == "agent":
                agent_text = turn["text"]
                break

        # ✅ Skip incomplete examples to avoid training on empty strings
        if not customer_text or not agent_text:
            continue

        text = LLAMA3_PROMPT.format(domain, dialect, customer_text, agent_text)
        instructions.append(text)

    return {"text": instructions}

print("Loading Dataset...")

with open(DATASET_PATH, "r", encoding="utf-8") as f:
    raw_data = json.load(f)

ds = Dataset.from_list(raw_data)

ds = ds.map(
    format_prompts,
    batched=True,
    # ✅ Windows fix: multiprocessing causes deadlocks on Windows
    num_proc=1,
    remove_columns=ds.column_names,  # ✅ Clean up old columns
)

# ✅ Sanity check
print(f"Dataset size: {len(ds)} examples")
print("Sample:\n", ds[0]["text"][:300])

# =========================
# 4. Training
# =========================
print("Starting Training...")

trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=ds,
    dataset_text_field="text",
    max_seq_length=max_seq_length,
    dataset_num_proc=1,   # ✅ Windows-safe
    packing=False,
    args=TrainingArguments(
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,

        warmup_steps=5,

        # ✅ For a real run use num_train_epochs=3 instead of max_steps
        # num_train_epochs=3,
        max_steps=60,  # Quick test run — increase to 300-500 for real training

        learning_rate=2e-4,

        # ✅ Fixed: was crashing because torch wasn't imported
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),

        logging_steps=1,
        optim="adamw_8bit",
        weight_decay=0.01,
        lr_scheduler_type="linear",
        seed=3407,
        output_dir="outputs",

        # ✅ Windows fix: disable parallel tokenizers warning
        dataloader_num_workers=0,
    ),
)

trainer_stats = trainer.train()

# ✅ Log final training stats
print(f"\n✅ Training done in {trainer_stats.metrics['train_runtime']:.1f}s")
print(f"   Loss: {trainer_stats.metrics['train_loss']:.4f}")

# =========================
# 5. Save Model
# =========================
output_model_dir = "models/egyptian_cs_llama3_lora"
print(f"\nSaving model to {output_model_dir}...")

model.save_pretrained(output_model_dir)
tokenizer.save_pretrained(output_model_dir)

print("✅ Done! LoRA weights saved and ready to use.")