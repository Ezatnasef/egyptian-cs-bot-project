import os
from gtts import gTTS
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EgyptianDialectDetector:
    def __init__(self):
        self.dialect_keywords = {
            'cairo': ['بتاع', 'هقولك', 'إيه ده'],
            'alexandria': ['والله العظيم', 'يا جدع'],
            'upper_egypt': ['بتاع', 'مالك'],
            'delta': ['والله العظيم'],
            'suez_canal': ['هقولك'],
            'sinai': ['يا جدع']
        }
    
    def detect_dialect(self, text):
        scores = {d: sum(1 for kw in kws if kw in text) for d, kws in self.dialect_keywords.items()}
        detected = max(scores, key=scores.get)
        return detected

class EgyptianLLM:
    def __init__(self):
        self.dialect_responses = {
            'cairo': "هقولك إيه يا برنس، {resp}!",
            'alexandria': "يا جدع، {resp} يا وحش!",
            'upper_egypt': "بتاعك إيه، {resp}؟",
            'delta': "والله العظيم {resp}",
            'suez_canal': "هقولك، {resp}",
            'sinai': "يا وحش {resp}"
        }
        self.responses = {
            'المنتج': 'ريتو فوري',
            'الطلب': 'هيوصل ساعة',
            'الدفع': 'كاش أون ديليفري',
            'ألغي': 'تم الإلغاء',
            'مشكلة': 'هحلها دلوقتي'
        }
    
    def generate_response(self, text, dialect):
        base = 'هنحلها يا صاحبي'
        for key, resp in self.responses.items():
            if key in text:
                base = resp
                break
        
        template = self.dialect_responses.get(dialect, '{resp}')
        return template.format(resp=base)

class EgyptianBot:
    def __init__(self):
        self.detector = EgyptianDialectDetector()
        self.llm = EgyptianLLM()
        self.memory = []
    
    def chat(self):
        print("🤖 بوت خدمة عملاء مصري - اكتب شكواك:")
        while True:
            try:
                user_input = input("أنت: ")
                if user_input.lower() in ['خروج', 'exit', 'quit']:
                    break
                
                dialect = self.detector.detect_dialect(user_input)
                response = self.llm.generate_response(user_input, dialect)
                
                print(f"🌍 اللهجة: {dialect}")
                print(f"🤖 {response}")
                
                # TTS
                tts = gTTS(response, lang='ar')
                tts.save("response.mp3")
                print("💾 response.mp3 جاهز")
                
                self.memory.append({'user': user_input, 'bot': response, 'dialect': dialect})
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ خطأ: {e}")

if __name__ == "__main__":
    bot = EgyptianBot()
    bot.chat()
    
    print("\n📊 تقرير نهائي:")
    print(f"محادثات: {len(bot.memory)}")
    dialects = {}
    for m in bot.memory:
        d = m['dialect']
        dialects[d] = dialects.get(d, 0) + 1
    print("اللهجات:", dialects)
