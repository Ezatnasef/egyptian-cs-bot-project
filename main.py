import os
import speech_recognition as sr
import webbrowser
# import whisper
# import torch
# from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from gtts import gTTS
# import pygame  # Disabled for compatibility
import pandas as pd
import numpy as np
# from sklearn.ensemble import RandomForestClassifier
from dotenv import load_dotenv
import logging
from flask import Flask, request, jsonify, render_template_string
import threading
import queue
import time

load_dotenv()

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

cs_bot = None  # Global reference

class EgyptianDialectDetector:
    def __init__(self):
        self.dialect_keywords = {
            'cairo': ['بتاع', 'هقولك', 'إيه ده', 'مالك', 'عامل إيه'],
            'alexandria': ['والله العظيم', 'يا جدع', 'يا وحش', 'إزيك يا برنس'],
            'upper_egypt': ['بتاع', 'هقولك', 'إيه ده', 'مالك', 'عامل إيه'],
            'delta': ['والله العظيم', 'يا جدع', 'يا وحش'],
            'suez_canal': ['بتاع', 'هقولك', 'إيه ده'],
            'sinai': ['والله العظيم', 'يا جدع']
        }
        self.model = None
        self.load_model()
    
    def load_model(self):
        # Simulate dialect classifier with keyword matching
        logger.info("Dialect detector initialized")
    
    def detect_dialect(self, text):
        scores = {}
        for dialect, keywords in self.dialect_keywords.items():
            score = sum(1 for kw in keywords if kw in text)
            scores[dialect] = score
        
        detected = max(scores, key=scores.get)
        confidence = scores[detected] / len(self.dialect_keywords[detected])
        logger.info(f"Detected dialect: {detected} (confidence: {confidence:.2f})")
        return detected, confidence

class EgyptianLLM:
    def __init__(self):
        self.dialect_responses = {
            'cairo': "هقولك إيه يا برنس، {response} والله العظيم!",
            'alexandria': "يا جدع إزيك، {response} يا وحش!",
            'upper_egypt': "بتاعك إيه يا صاحبي، {response} مالك؟",
            'delta': "والله العظيم {response} يا برنس!",
            'suez_canal': "هقولك إيه، {response} عامل إيه؟",
            'sinai': "يا وحش {response} إزيك يا جدع!"
        }
        # Placeholder for real model pipeline
        self.pipe = None
    
    def generate_response(self, user_input, dialect):
        # Generate base response
        base_response = ""
        
        # Check if real model is loaded, otherwise use Rule-Based Fallback
        if self.pipe:
            prompt = f"Customer (Egyptian dialect): {user_input}\\nCS Bot:"
            response = self.pipe(prompt, max_length=100, num_return_sequences=1)[0]['generated_text']
            base_response = response.split("CS Bot:")[-1].strip()
        else:
            # Intelligent fallback for demo purposes
            if any(w in user_input for w in ['نت', 'باقة', 'سرعة']):
                base_response = "ولا يهمك، أنا شايف إن الخط محتاج تنشيط، ثواني وهعملك ريستارت"
            elif any(w in user_input for w in ['فلوس', 'رصيد', 'حساب']):
                base_response = "متقلقش، راجعنا الحساب والعملية هتسمع خلال 24 ساعة"
            else:
                base_response = "أنا معاك يا فندم، قول شكوتك بالتفصيل وأنا هحلها فوراً"
        
        # Adapt to dialect
        dialect_template = self.dialect_responses.get(dialect, "{response}")
        final_response = dialect_template.format(response=base_response)
        
        logger.info(f"Generated response in {dialect} dialect: {final_response}")
        return final_response

class EgyptianSTT:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        logger.info("✅ STT Audio mode active!")
    
    def transcribe_audio(self):
        try:
            print("🎤 اتكلم دلوقتي...")
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
            
            with open("input_audio.wav", "wb") as f:
                f.write(audio.get_wav_data())
            
            transcription = self.recognizer.recognize_google(audio, language='ar-EG')
            print(f"✅ سمع: {transcription}")
            return "input_audio.wav", transcription
        except sr.UnknownValueError:
            return None, None #"ما فهمتش الكلام"
        except sr.RequestError:
            return None, "مشكلة إنترنت"
        except Exception as e:
            logger.error(f"STT error: {e}")
            return None, "خطأ فني"

class EgyptianTTS:
    def __init__(self):
        pass
    
    def speak(self, text, lang='ar'):
        try:
            print(f"🔊 [TTS] {text}")
            tts = gTTS(text=text, lang=lang, slow=False)
            tts.save(os.path.join(os.getcwd(), "response.mp3"))
            print("💾 response.mp3 محفوظ - شغله في أي media player")
            logger.info("TTS completed - MP3 saved")
        except Exception as e:
            logger.error(f"TTS error: {e}")

class CustomerServiceMemory:
    def __init__(self, max_turns=20):
        self.memory = []
        self.max_turns = max_turns
    
    def add_turn(self, user_input, bot_response, dialect):
        self.memory.append({
            "user": user_input,
            "bot": bot_response,
            "dialect": dialect,
            "timestamp": time.time()
        })
        if len(self.memory) > self.max_turns:
            self.memory.pop(0)
    
    def get_context(self):
        return self.memory[-5:]  # Last 5 turns

class EgyptianCSBot:
    def __init__(self):
        self.dialect_detector = EgyptianDialectDetector()
        self.llm = EgyptianLLM()
        self.stt = EgyptianSTT()
        self.tts = EgyptianTTS()
        self.memory = CustomerServiceMemory()
        self.is_running = False
    
    def process_conversation(self):
        if self.is_running:
            print("⚠️ البوت يعمل بالفعل!")
            return

        self.is_running = True
        print("🎤 ابدأ تتكلم... (اضغط Ctrl+C للخروج)")
        while True:
            try:
                # STT
                audio_file, transcription = self.stt.transcribe_audio()
                if not transcription:
                    print("❌ ما سمعش الكلام")
                    continue
                
                print(f"🗣️ العميل قال: {transcription}")
                
                # Dialect detection
                dialect, confidence = self.dialect_detector.detect_dialect(transcription)
                print(f"🌍 اللهجة: {dialect} (ثقة: {confidence:.2f})")
                
                # Context from memory
                context = self.memory.get_context()
                context_text = "\\n".join([f"User: {turn['user']}\\nBot: {turn['bot']}" for turn in context])
                full_input = f"{context_text}\\nUser: {transcription}"
                
                # LLM response
                response = self.llm.generate_response(full_input, dialect)
                print(f"🤖 الرد: {response}")
                
                # Memory
                self.memory.add_turn(transcription, response, dialect)
                
                # TTS
                self.tts.speak(response)
                
                print("-" * 50)
                
            except KeyboardInterrupt:
                print("\\n👋 تم إنهاء المحادثة")
                self.is_running = False
                break
            except Exception as e:
                logger.error(f"Error: {e}")
                print("❌ حصل خطأ، جرب تاني")

# Dataset generation for training
def generate_egyptian_dataset(num_conversations=500):
    dialects = ['cairo', 'alexandria', 'upper_egypt', 'delta', 'suez_canal', 'sinai']
    customer_queries = [
        "المنتج اتلف، عايز ريتو",
        "الطلب اتأخر أوي، إيه السبب؟",
        "مش عارف أدفع، الموقع مش شغال",
        "المنتج غلط، مش اللي طلبته",
        "عايز ألغي الطلب"
    ]
    
    dataset = []
    for i in range(num_conversations):
        dialect = np.random.choice(dialects)
        query = np.random.choice(customer_queries)
        dataset.append({
            "id": i,
            "dialect": dialect,
            "customer": query,
            "timestamp": time.time()
        })
    
    df = pd.DataFrame(dataset)
    df.to_csv("egyptian_cs_dataset.csv", index=False, encoding='utf-8')
    print(f"✅ تم إنشاء dataset بـ {num_conversations} محادثة")
    return df

# Flask Dashboard
app = Flask(__name__)

@app.route('/')
def dashboard():
    global cs_bot
    print("✅ تم استلام طلب فتح الداشبورد بنجاح!")
    memory_data = cs_bot.memory.memory if cs_bot else []
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Egyptian CS Bot Dashboard</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial; margin: 40px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: auto; }
        .stats { display: flex; gap: 20px; margin: 20px 0; }
        .stat-card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); flex: 1; text-align: center; }
        .conversation { background: white; margin: 10px 0; padding: 15px; border-radius: 10px; box-shadow: 0 1px 5px rgba(0,0,0,0.1); }
        .user { color: #e74c3c; font-weight: bold; }
        .bot { color: #3498db; }
        .dialect { color: #27ae60; font-size: 0.9em; }
        .refresh { display: block; margin: 20px auto; padding: 10px 20px; background: #333; color: white; border: none; cursor: pointer; }
    </style>
    </head>
    <body>
        <div class="container">
            <h1>🏛️ لوحة تحكم بوت خدمة العملاء المصري</h1>
            <div class="stats">
                <div class="stat-card">
                    <h2>{{ total_conversations }}</h2>
                    <p>إجمالي المحادثات</p>
                </div>
                <div class="stat-card">
                    <h2>{{ dialect_stats }}</h2>
                    <p>توزيع اللهجات</p>
                </div>
            </div>
            <h3>آخر المحادثات:</h3>
            {% for conv in conversations %}
            <div class="conversation">
                <p><span class="user">العميل:</span> {{ conv.user }}</p>
                <p><span class="bot">البوت:</span> {{ conv.bot }}</p>
                <span class="dialect">🌍 {{ conv.dialect }}</span>
            </div>
            {% endfor %}
            <button onclick="startBot()">🎤 ابدأ المحادثة الصوتية</button>
            <button class="refresh" onclick="location.reload()">🔄 تحديث الحالة</button>
        </div>
        <script>
            function startBot() {
                window.open('/start-bot', '_blank');
            }
        </script>
    </body>
    </html>
    """
    total_conversations = len(memory_data)
    dialect_stats = dict(pd.Series([c['dialect'] for c in memory_data]).value_counts())
    
    return render_template_string(html, 
                                total_conversations=total_conversations,
                                conversations=memory_data[-10:],
                                dialect_stats=dialect_stats)

@app.route('/start-bot')
def start_bot():
    global cs_bot
    if not cs_bot:
        cs_bot = EgyptianCSBot()

    if cs_bot.is_running:
        return '<h1>⚠️ البوت يعمل بالفعل!</h1><p>هو شغال في الخلفية دلوقتي، جرب تتكلم.</p><a href="/">العودة للداشبورد</a>'

    # Run bot loop in background thread
    t = threading.Thread(target=cs_bot.process_conversation)
    t.daemon = True
    t.start()
    return '<h1>🚀 البوت يعمل الآن في الخلفية!</h1><p>اتكلم في المايك وارجع للداشبورد واعمل Refresh عشان تشوف المحادثة.</p><a href="/">العودة للداشبورد</a>'

if __name__ == "__main__":
    print("🚀 Egyptian CS Bot - نظام خدمة عملاء مصري ذكي")
    print("1. إنشاء Dataset")
    print("2. تشغيل البوت الصوتي")
    print("3. Dashboard")
    
    choice = input("اختار رقم: ")
    
    if choice == "1":
        generate_egyptian_dataset(500)
    elif choice == "2":
        cs_bot = EgyptianCSBot()
        cs_bot.process_conversation()
    elif choice == "3":
        cs_bot = EgyptianCSBot()
        print("⏳ السيرفر جاهز... جاري فتح المتصفح الآن...")
        print("👉 لو المتصفح مفتحش لوحده، اضغط هنا: http://localhost:5000")
        threading.Timer(1.5, lambda: webbrowser.open("http://localhost:5000")).start()
        app.run(debug=True, port=5000, use_reloader=False)
