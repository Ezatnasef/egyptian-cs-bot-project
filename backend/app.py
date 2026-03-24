"""
Egyptian Dialect Customer Service Bot - Local Models Version
Enhanced with: Local STT (Whisper), Local LLM, Multi-turn Memory, Analytics
"""

import os
import json
import time
import uuid
import tempfile
import traceback
from pathlib import Path
import base64
import io
from collections import defaultdict
from datetime import datetime
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict
import asyncio
import edge_tts
from dotenv import load_dotenv
import speech_recognition as sr
from openai import AsyncOpenAI

# Load .env from project root
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)
print(f"Loading .env from: {env_path.absolute()} (exists: {env_path.exists()})")

# Try GROQ first, then OpenAI fallback
api_key = os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY")
if not api_key:
    print("❌ ERROR: No API key found! Set GROQ_API_KEY or OPENAI_API_KEY in .env file")
    raise ValueError("API key required. Please set GROQ_API_KEY or OPENAI_API_KEY in .env file")
else:
    print(f"✅ API Key found (starts with: {api_key[:10]}...)")

is_groq = api_key.startswith("gsk_")

if is_groq:
    print("🚀 Using Groq API Configuration")
    client = AsyncOpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
else:
    print("🤖 Using OpenAI API Configuration")
    client = AsyncOpenAI(api_key=api_key)
# --- Cleaned for V4 (API Driven) ---

app = FastAPI(title="Egyptian CS Bot - V4.0 API Edition", version="4.0.0")

# --- Startup Logging ---
@app.on_event("startup")
async def startup_event():
    print(f"Server starting up V4.0...")
    print(f"Dataset Path: {DATASET_PATH.absolute()}")
    print(f"Dataset exists: {DATASET_PATH.exists()}")
    frontend_path = Path(__file__).parent.parent / "frontend" / "index.html"
    print(f"Frontend index path: {frontend_path.absolute()}")
    print(f"Frontend exists: {frontend_path.exists()}")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Config ---
DATASET_PATH = Path(__file__).parent.parent / "dataset" / "egyptian_cs_dataset.json"

# --- Models Setup ---
# Check for FFmpeg for fallback only, but we will mostly rely on API APIs which don't strictly crash the app if missing for basic webm

# Local AI setup is removed in V4.0 to prioritize stability and speed via APIs.
# 1. Local STT (Speech-to-Text) -> Replaced with SpeechRecognition / Whisper API
recognizer = sr.Recognizer()

# 2. Local LLM -> Replaced with OpenAI API (GPT-4o-mini)
llm_pipeline = None


# --- In-Memory Storage ---
sessions: Dict[str, dict] = {}  # session_id -> {history, dialect, summary, created_at}
analytics_data = {
    "total_messages": 0,
    "dialect_counts": defaultdict(int),
    "emotion_counts": defaultdict(int),
    "domain_counts": defaultdict(int),
    "hourly_activity": defaultdict(int),
    "avg_response_time": [],
    "satisfaction_scores": [],
    "conversations_by_day": defaultdict(int),
}

# --- Prompt System ---
try:
    from system_prompt import SYSTEM_PROMPT
except ImportError:
    print("⚠️ Warning: system_prompt.py not found. Using default prompt.")
    SYSTEM_PROMPT = "You are a helpful Egyptian customer service assistant."


# --- Models ---
class Message(BaseModel):
    role: str
    text: str

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = ""
    history: Optional[List[Message]] = []
    domain: Optional[str] = "general"

class ChatResponse(BaseModel):
    reply: str
    detected_dialect: str
    emotion: str
    session_id: str
    message_count: int
    audio_base64: Optional[str] = None

class FeedbackRequest(BaseModel):
    session_id: str
    rating: int  # 1-5


# --- Enhanced Dialect Detection ---
DIALECT_MARKERS = {
    "saidi": {
        "markers": ["يا ولدي", "يا حاج", "والنبي", "جال", "جه", "يا عم", "شايل همك"],
        "patterns": ["والنبي يا", "يا حاج"],
        "name_ar": "صعيدي",
        "weight": 1.2
    },
    "alexandrian": {
        "markers": ["يا صاحبي", "يا وحش", "بتاع إيه", "يا معلم"],
        "patterns": ["يا صاحبي", "يا وحش"],
        "name_ar": "إسكندراني",
        "weight": 1.3
    },
    "delta": {
        "markers": ["يا جدع", "يا ابني", "ياخي", "يا ابني"],
        "patterns": ["يا جدع", "يا ابني"],
        "name_ar": "دلتاوي",
        "weight": 1.1
    },
    "canal_zone": {
        "markers": ["يا معلم"],
        "patterns": ["يا معلم"],
        "name_ar": "قناوي",
        "weight": 1.0
    },
    "sinai_bedouin": {
        "markers": ["يا شيخ", "يا أخوي", "يا رجال", "ما أعرف"],
        "patterns": ["يا شيخ", "يا أخوي"],
        "name_ar": "سيناوي/بدوي",
        "weight": 1.3
    },
    "cairene": {
        "markers": ["يا باشا", "باشا", "يا فندم", "يا ريس", "خلاص", "ماشي", "دلوقتي", "أوي", "إزاي"],
        "patterns": ["يا باشا", "يا فندم"],
        "name_ar": "قاهري",
        "weight": 0.9
    }
}

def detect_dialect(text: str, session_id: str = "") -> tuple[str, str]:
    scores = {}
    for dialect, info in DIALECT_MARKERS.items():
        score = 0
        for m in info["markers"]:
            if m in text:
                score += 1
        for p in info["patterns"]:
            if p in text:
                score += 0.5
        score *= info["weight"]
        if score > 0:
            scores[dialect] = score

    if scores:
        best = max(scores, key=scores.get)
        return best, DIALECT_MARKERS[best]["name_ar"]

    if session_id and session_id in sessions:
        prev_dialect = sessions[session_id].get("dialect", "cairene")
        return prev_dialect, DIALECT_MARKERS.get(prev_dialect, {}).get("name_ar", "قاهري")

    return "cairene", "قاهري"


EMOTION_RULES = {
    "angry": {"words": ["زهقت", "مش هينفع", "عايز مدير", "زعلان", "غضبان", "حرام", "بايظ", "حرام عليكم"], "name_ar": "غاضب"},
    "worried": {"words": ["خايف", "قلقان", "مش عارف", "ضروري", "محتاج"], "name_ar": "قلق"},
    "frustrated": {"words": ["اتأخر", "مجاش", "مش شغال", "بطيء", "مقطوعة", "وقف", "مكسور"], "name_ar": "محبط"},
    "confused": {"words": ["مش فاهم", "إزاي", "نسيت", "مش عارف أعمل"], "name_ar": "محتار"}
}

def detect_emotion(text: str) -> str:
    best_emotion = "neutral"
    best_score = 0
    for emotion, info in EMOTION_RULES.items():
        score = sum(1 for w in info["words"] if w in text)
        if score > best_score:
            best_score = score
            best_emotion = emotion
    return best_emotion


# --- Session Management ---
def get_or_create_session(session_id: str) -> str:
    if not session_id or session_id not in sessions:
        session_id = str(uuid.uuid4())[:8]
        sessions[session_id] = {
            "history": [],
            "dialect": "cairene",
            "summary": "",
            "created_at": datetime.now().isoformat(),
            "message_count": 0,
        }
    return session_id

def summarize_history(history: List[dict]) -> str:
    """Simple summarization to avoid exceeding token limits."""
    if len(history) < 6:
        return ""
    
    # In a real app, this would use the LLM to generate a summary.
    # For now, we manually extract a brief overview of the context.
    summary = "السياق السابق: العميل كان يتحدث عن "
    topics = []
    
    recent_text = " ".join([m["content"] for m in history[:-4]]) # exclude the latest turns
    
    if any(w in recent_text for w in ["نت", "باقة", "سرعة", "فصل"]):
        topics.append("مشكلة في الإنترنت")
    if any(w in recent_text for w in ["فلوس", "رصيد", "حساب", "دفع"]):
        topics.append("استفسار مالي")
    if any(w in recent_text for w in ["طلب", "توصيل", "أوردر", "شحن"]):
        topics.append("حالة أوردر")
        
    if topics:
        summary += " و ".join(topics)
    else:
        summary += "موضوع عام"
        
    return summary


# --- Endpoints ---
@app.get("/")
async def serve_frontend():
    frontend_path = (Path(__file__).parent.parent / "frontend" / "index.html").absolute()
    print(f"Serving frontend from: {frontend_path}")
    if not frontend_path.exists():
        return JSONResponse({"error": f"File not found at {frontend_path}"}, status_code=404)
    return FileResponse(frontend_path)

@app.get("/test")
async def test_route():
    return {"message": "Server is UP and running!"}

@app.get("/analytics")
async def serve_analytics():
    analytics_path = Path(__file__).parent.parent / "frontend" / "analytics.html"
    return FileResponse(analytics_path)

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "llm_loaded": "OpenAI API",
        "stt_loaded": "API Ready",
        "version": "4.0.0 (API Driven)"
    }

def get_dataset_size() -> int:
    try:
        with open(DATASET_PATH, "r", encoding="utf-8") as f:
            return len(json.load(f))
    except:
        return 0


async def generate_tts_base64_async(text: str, voice: str = "ar-EG-SalmaNeural", rate: str = "-10%", pitch: str = "+0Hz") -> str:
    """Generate TTS using Microsoft Edge TTS with SSML support for realism"""
    try:
        communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
        
        return base64.b64encode(audio_data).decode()
    except Exception as e:
        print(f"Edge TTS Generation Error: {e}")
        return ""

# --- AUDIO / STT ENDPOINT ---
@app.post("/api/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    """Convert spoken Egyptian Arabic to text using APIs (Whisper API or Google)"""
    try:
        ext = os.path.splitext(audio.filename)[1] or ".webm"
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            content = await audio.read()
            tmp.write(content)
            tmp_path = tmp.name

        transcription = ""
        # Try OpenAI Whisper API first if key exists
        if os.getenv("OPENAI_API_KEY"):
            try:
                with open(tmp_path, "rb") as audio_file:
                    transcript_resp = await client.audio.transcriptions.create(
                        model="whisper-large-v3-turbo" if is_groq else "whisper-1", 
                        file=audio_file,
                        language="ar",
                        prompt="محادثة خدمة عملاء مصرية احترافية. العميل يسأل عن باقات الإنترنت، الرصيد، الطلبات، أو المساعدة التقنية. اللهجات: قاهري، إسكندراني، صعيدي."
                    )
                transcription = transcript_resp.text.strip()
                print(f"✅ OpenAI STT Success: {transcription}")
            except Exception as e:
                print(f"⚠️ OpenAI STT failed, falling back to Google: {e}")
                
        # Fallback to SpeechRecognition (Google Free API) if OpenAI fails or no key
        if not transcription:
            import speech_recognition as sr
            r = sr.Recognizer()
            try:
                # convert to wav using pydub if it's webm
                from pydub import AudioSegment
                wav_path = tmp_path + ".wav"
                AudioSegment.from_file(tmp_path).export(wav_path, format="wav")
                
                with sr.AudioFile(wav_path) as source:
                    audio_data = r.record(source)
                    transcription = r.recognize_google(audio_data, language="ar-EG")
                print(f"✅ Google STT Success: {transcription}")
                os.unlink(wav_path)
            except Exception as e:
                print(f"❌ Google STT Failed: {e}")
                raise HTTPException(status_code=500, detail="فشل في تحويل الصوت. حاول تحدث بوضوح أكبر.")

        # Filter known Whisper hallucinations (YouTube tropes in Arabic)
        hallucinations = ["اشترك في القنا", "اشتركوا في القناة", "شكراً للمشاهدة", "لا تنسوا الاشتراك", "قدّم لكم هذا الفيديو", "متابعينا الأعزاء"]
        for h in hallucinations:
            if h in transcription:
                print(f"🛑 Filtered Whisper hallucination: {h}")
                transcription = transcription.replace(h, "").strip()

        # If transcription is empty or just generic hallucination residuals, use fallback or original audio context
        if not transcription or len(transcription) < 2:
             # If it was very short, maybe it literally just said 'hi' but got filtered? 
             # For now, let's keep it empty to trigger 'try again' if it's truly silent
             pass

        os.unlink(tmp_path)
        return {"text": transcription}
        
    except Exception as e:
        print(f"❌ STT CRITICAL ERROR: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="مشكلة في معالجة الملف الصوتي")


# --- LOCAL LLM CHAT ENDPOINT ---
@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    start_time = time.time()

    session_id = get_or_create_session(request.session_id)
    session = sessions[session_id]

    dialect_id, dialect_name = detect_dialect(request.message, session_id)
    emotion = detect_emotion(request.message)

    session["dialect"] = dialect_id
    session["message_count"] += 1

    reply = ""

    # Memory Check & Summarization
    if len(session["history"]) > 10:
        session["summary"] = summarize_history(session["history"])
        # Keep only the last 4 messages plus the summary context
        session["history"] = session["history"][-4:]

    # Generate response using API only
    try:
        system_msg = f"""أنت موظف خدمة عملاء مصري محترف جداً وودود.
التعليمات الصارمة:
1. رد دائماً بلهجة مصرية عامية طبيعية جداً (مثل كلام الناس في الشارع) تتناسب مع لهجة العميل: {dialect_name}.
2. كن "بني آدم" في ردودك؛ استخدم عبارات ودودة مثل "من عيوني"، "تحت أمرك يا فندم"، "متشغلش بالك خالص".
3. لا تخمن اسم العميل أبداً ولا تناديه باسم (مثل عثمان أو عتمان) إلا إذا أخبرك هو باسمه. استخدم "يا فندم" أو "يا باشا".
4. إذا قال العميل "عامل ايه" أو "اخبارك"، رد بطريقة بشرية ودودة: "الحمد لله زي الفل، طمني أنت عامل إيه؟ إيه الأخبار؟"
5. حافظ على نبرة تتناسب مع مشاعره: {emotion}.
6. كن مختصراً، عملياً، ومفيداً جداً وبدون تكلف."""
        
        messages = [{"role": "system", "content": system_msg}]
        # Add context
        for m in session["history"][-4:]:
            messages.append(m)
        # Add current
        messages.append({"role": "user", "content": request.message})

        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile" if is_groq else "gpt-4o-mini",
            messages=messages,
            max_tokens=200,
            temperature=0.3
        )
        reply = response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ LLM API Error: {e}")
        raise HTTPException(status_code=500, detail="فشل في الاتصال بخدمة الذكاء الاصطناعي. حاول لاحقاً.")

    # Save to session history
    session["history"].append({"role": "user", "content": request.message})
    session["history"].append({"role": "assistant", "content": reply})

    # Update analytics
    response_time = time.time() - start_time
    analytics_data["total_messages"] += 1
    analytics_data["dialect_counts"][dialect_name] += 1
    analytics_data["emotion_counts"][emotion] += 1
    analytics_data["domain_counts"][request.domain] += 1
    analytics_data["hourly_activity"][datetime.now().hour] += 1
    analytics_data["avg_response_time"].append(response_time)
    analytics_data["conversations_by_day"][datetime.now().strftime("%Y-%m-%d")] += 1

    # Clean text for TTS (remove emojis and extra symbols)
    import re
    clean_reply = re.sub(r'[^\w\s\u0621-\u064A.؟،!]', '', reply)
    # Add slight pauses for better human-like rhythm
    clean_reply = clean_reply.replace('،', '... ').replace('؟', '؟ ... ').replace('.', '. ... ')
    
    # Map emotions to voice parameters (SSML Tuning)
    voice_params = {
        "neutral": {"rate": "-5%", "pitch": "+0Hz"},
        "angry": {"rate": "-15%", "pitch": "-3Hz"},  # Lower, slower, firmer
        "worried": {"rate": "-12%", "pitch": "+2Hz"}, # Shaky, slightly higher
        "frustrated": {"rate": "-20%", "pitch": "-2Hz"}, # Very slow, annoyed
        "confused": {"rate": "-8%", "pitch": "+3Hz"}, # Questioning tone
        "happy": {"rate": "+0%", "pitch": "+5Hz"}, # Fast, cheerful
    }
    params = voice_params.get(emotion, voice_params["neutral"])

    # Generate Audio (TTS)
    audio_b64 = await generate_tts_base64_async(clean_reply, rate=params["rate"], pitch=params["pitch"])

    return ChatResponse(
        reply=reply,
        detected_dialect=dialect_name,
        emotion=emotion,
        session_id=session_id,
        message_count=session["message_count"],
        audio_base64=audio_b64
    )


def get_demo_reply(message: str, dialect: str) -> str:
    """Demo mode: return matching response from dataset"""
    dataset = []
    try:
        with open(DATASET_PATH, "r", encoding="utf-8") as f:
            dataset = json.load(f)
    except Exception as e:
        print(f"⚠️ Warning: Could not load or parse dataset JSON: {e}")

    if dataset:
        best_match = None
        best_score = 0
        for conv in dataset:
            for turn in conv["conversation"]:
                if turn["role"] == "customer":
                    score = len(set(turn["text"].split()) & set(message.split()))
                    if score > best_score:
                        best_score = score
                        idx = conv["conversation"].index(turn)
                        if idx + 1 < len(conv["conversation"]):
                            best_match = conv["conversation"][idx + 1]["text"]

        if best_match and best_score >= 2:
            return best_match

    defaults = {
        "saidi": "والنبي يا حاج أنا هنا علشان أساعدك، قولي إيه اللي محتاجه وأنا شايل همك",
        "alexandrian": "يا صاحبي أنا تحت أمرك، قولي إيه المشكلة وأنا هحلها دلوقتي",
        "cairene": "يا فندم أنا هنا علشان أساعدك، قولي إيه اللي محتاجه بالظبط",
        "delta": "يا ابني أنا معاك، قولي إيه اللي محتاجه وأنا هساعدك على طول",
        "canal_zone": "يا معلم أنا تحت أمرك، قولي المشكلة وأنا هشوفلك الحل",
        "sinai_bedouin": "يا أخوي أنا هنا علشان أساعدك، قولي اللي تحتاجه إن شاء الله"
    }
    default_reply = defaults.get(dialect, defaults["cairene"])
    # Add a note that this is a fallback
    return f"{default_reply} (ملاحظة: أنا أعمل الآن في الوضع التجريبي بدون تحميل الموديل الكامل)"


@app.get("/api/dataset")
async def get_dataset():
    try:
        with open(DATASET_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

@app.get("/api/dialects")
async def get_dialects():
    return {k: v["name_ar"] for k, v in DIALECT_MARKERS.items()}

@app.get("/api/analytics")
async def get_analytics():
    avg_time = (sum(analytics_data["avg_response_time"][-100:]) / len(analytics_data["avg_response_time"][-100:]) if analytics_data["avg_response_time"] else 0)
    return {
        "total_messages": analytics_data["total_messages"],
        "active_sessions": len(sessions),
        "dialect_distribution": dict(analytics_data["dialect_counts"]),
        "emotion_distribution": dict(analytics_data["emotion_counts"]),
        "domain_distribution": dict(analytics_data["domain_counts"]),
        "hourly_activity": dict(analytics_data["hourly_activity"]),
        "avg_response_time_ms": round(avg_time * 1000, 2),
        "conversations_by_day": dict(analytics_data["conversations_by_day"]),
        "dataset_size": get_dataset_size(),
    }

@app.post("/api/session/clear")
async def clear_session(data: dict):
    sid = data.get("session_id", "")
    if sid in sessions:
        sessions[sid]["history"] = []
        sessions[sid]["message_count"] = 0
        return {"status": "cleared"}
    return {"status": "not_found"}

# Serve static files
frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Server on http://0.0.0.0:8001")
    uvicorn.run(app, host="0.0.0.0", port=8001)
