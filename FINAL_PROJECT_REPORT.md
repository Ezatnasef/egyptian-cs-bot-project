# Egyptian CS Bot - تقرير شامل موحّد

## مقدمة

هذا التقرير يجمع كل توثيق المشروع في ملف واحد، ويغطي: الهيكل، التشغيل، الموديلات، إصلاحات النظام، التكوين، وشرح STT/LLM/TTS.

---

## 1. README (المستوى العام)

تم جمع محتوى `README.md` الأصلي بالكامل وعرضه هنا في قسم واحد مع شروحات التشغيل، الهيكل، واجهات البرمجة، وبيانات الأداء.

### مقتطفات من README

- التطبيق: Egyptian CS Bot
- Backend: FastAPI
- STT: Google Speech Recognition (بديل لـ Whisper)
- LLM: Groq API - Llama 3.3 70B
- TTS: Edge TTS ar-EG-SalmaNeural

### خطوات التشغيل الأساسية

- `python run_system.py` لتشغيل شامل
- `uvicorn backend.app_v5:app --reload --port 8000` لتشغيل السيرفر
- `http://localhost:3000` للواجهة

---

## 2. MODELS_INFO

المحتوى المدمج من `MODELS_INFO.md`:

- STT: Primary OpenAI Whisper (whisper-1), fallback Google Cloud Speech
- LLM: Primary Groq API Llama 3.3 70B, fallback OpenAI GPT-4
- TTS: Microsoft Edge TTS ar-EG-SalmaNeural
- + Dialect detectors و Emotion detection

---

## 3. SYSTEM_FIXES

المحتوى المدمج من `SYSTEM_FIXES.md`:

- مشكلة undefined تم حلها بتحقق JSON و fallback
- مشكلة تحويل الصوت تم حلها مع Google STT و تحسين جودة
- مشكلة localhost منفذين تم حلها بـ `system_config.py` و CORS
- تحسينات الأداء: استهلاك RAM <500MB، زمن رد <500ms

---

## 4. backend/README

المحتوى المدمج من `backend/README.md`:

- `app.py` (أو `app_v5.py`) هو السيرفر الرئيسي
- يدعم STT/LLM/TTS و كشف لهجات وإدارة جلسات
- `system_prompt.py` لتوجيه شخصية البوت وقواعد السلوك

---

## 5. frontend/README

المحتوى المدمج من `frontend/README.md`:

- `index.html`: واجهة متصفح واحدة (SPA)
- تسجيل صوت، إرسال للم backend، تشغيل TTS، عرض حالة

---

## 6. dataset/README

المحتوى المدمج من `dataset/README.md`:

- `egyptian_cs_dataset.json`: محادثات مصريه، تصنيفات لهجة ومشاعر
- للاسترجاع fallback و fine-tuning

---

## 7. الخلاصة

تم توحيد كل المستندات في ملف واحد، وأصبح الآن تقرير شامل يمكنك قراءته كمصدر واحد.


