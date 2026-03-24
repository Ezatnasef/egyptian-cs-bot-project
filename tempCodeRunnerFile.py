"""
Professional LLM Fine-Tuning Script using Unsloth & Llama 3 8B
==============================================================
هذا السكريبت مصمم لتدريب موديل قوي جداً (Llama 3) على البيانات المصرية
بحيث يعمل بكفاءة على الأجهزة المنزلية بكرت شاشة واحد (يتطلب بطاقة Nvidia).

متطلبات التشغيل:
pip install unsloth trl peft transformers datasets bitsandbytes
"""

import json
from pathlib import Path
from datasets import Dataset
from unsloth import FastLanguageModel
from trl import SFTTrainer
from transformers import TrainingArguments

# 1. إعدادات الموديل (Llama 3 8B Instruct - 4bit Quantized)
max_seq_length = 2048
dtype = None # Auto detect
load_in_4bit = True # For consumer GPUs (e.g. RTX 3060/4060)

model_name = "unsloth/llama-3-8b-Instruct-bnb-4bit"
print(f"Loading Base Model: {model_name}...")

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name = model_name,
    max_seq_length = max_seq_length,
    dtype = dtype,
    load_in_4bit = load_in_4bit,
)

# 2. إضافة LoRA Adapters للتدريب السريع بدون تعديل الموديل بالكامل
model = FastLanguageModel.get_peft_model(
    model,
    r = 16, # Choose any number > 0 ! Suggested 8, 16, 32, 64, 128
    target_modules = ["q_proj", "k_proj", "v_proj", "o_proj",
                      "gate_proj", "up_proj", "down_proj",],
    lora_alpha = 16,
    lora_dropout = 0, # Supports any, but = 0 is optimized
    bias = "none",    # Supports any, but = "none" is optimized
    use_gradient_checkpointing = "unsloth", # True or "unsloth" for very long context
    random_state = 3407,
    use_rslora = False,
    loftq_config = None,
)

# 3. تحضير البيانات
DATASET_PATH = Path(__file__).parent / "dataset" / "egyptian_cs_dataset.json"

def format_prompts(examples):
    instructions = []
    
    # تحويل البيانات إلى صيغة (Instruction, Input, Output) أو Llama-3 Chat Format
    llama3_prompt = """<|begin_of_text|><|start_header_id|>system<|end_header_id|>

أنت موظف خدمة عملاء مصري محترف. أجب باختصار وبلهجة العميل بناءً على السياق الآتي.
المجال: {}
اللهجة: {}<|eot_id|><|start_header_id|>user<|end_header_id|>

{}<|eot_id|><|start_header_id|>assistant<|end_header_id|>

{}<|eot_id|>"""

    for domain, dialect, conv in zip(examples["domain"], examples["dialect"], examples["conversation"]):
        # استخراج دور العميل ودور الوكيل
        customer_text = ""
        agent_text = ""
        for turn in conv:
            if turn["role"] == "customer":
                customer_text = turn["text"]
            elif turn["role"] == "agent":
                agent_text = turn["text"]
                break # نأخذ أول دور للتدريب الأساسي
                
        text = llama3_prompt.format(domain, dialect, customer_text, agent_text)
        instructions.append(text)
        
    return {"text": instructions}

print("Loading Dataset...")
with open(DATASET_PATH, "r", encoding="utf-8") as f:
    raw_data = json.load(f)

# Convert to HuggingFace Dataset
ds = Dataset.from_list(raw_data)
ds = ds.map(format_prompts, batched = True)

# 4. بدء التدريب (SFT)
print("Starting Training...")
trainer = SFTTrainer(
    model = model,
    tokenizer = tokenizer,
    train_dataset = ds,
    dataset_text_field = "text",
    max_seq_length = max_seq_length,
    dataset_num_proc = 2,
    packing = False, # Can make training 5x faster for short sequences.
    args = TrainingArguments(
        per_device_train_batch_size = 2,
        gradient_accumulation_steps = 4,
        warmup_steps = 5,
        max_steps = 60, # Increase this to e.g., 300-500 for actual training
        learning_rate = 2e-4,
        fp16 = not torch.cuda.is_bf16_supported(),
        bf16 = torch.cuda.is_bf16_supported(),
        logging_steps = 1,
        optim = "adamw_8bit",
        weight_decay = 0.01,
        lr_scheduler_type = "linear",
        seed = 3407,
        output_dir = "outputs",
    ),
)

trainer_stats = trainer.train()

# 5. حفظ الموديل النهائي
output_model_dir = "models/egyptian_cs_llama3_lora"
print(f"Saving Fine-Tuned Model to {output_model_dir}...")
model.save_pretrained(output_model_dir) # Local saving
tokenizer.save_pretrained(output_model_dir)

print("✅ Training Complete! You can now use the fine-tuned LoRA weights in your app.")
