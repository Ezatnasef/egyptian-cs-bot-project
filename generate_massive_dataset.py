import json
import random
from pathlib import Path

# مجالات خدمة العملاء
domains = [
    "الاتصالات (باقات، إنترنت، رصيد)",
    "البنوك (بطاقات، قروض، حسابات)",
    "التجارة الإلكترونية (أوردر، توصيل، استرجاع)",
    "الدعم الفني (أجهزة، أعطال، تطبيقات)",
    "الرعاية الصحية (حجز، صيدلية، تحاليل)",
    "الخدمات الحكومية (مرور، سجل مدني، ضرائب)"
]

# اللهجات
dialects = ["saidi", "cairene", "alexandrian", "delta", "canal_zone", "sinai_bedouin"]

# المشاعر
emotions = ["neutral", "angry", "worried", "frustrated", "confused"]

# قوالب الأسئلة للعملاء
customer_templates = {
    "الاتصالات (باقات، إنترنت، رصيد)": [
        "النت فاصل عندي من الصبح ومش عارف أشتغل",
        "الباقة خلصت قبل معادها بأسبوع ده إزاي؟",
        "عايز أجدد باقة المكالمات ضروري",
        "خط التليفون مشتغلش من ساعة ما اشتريته",
        "اتسحب مني رصيد ومكلّمتش حد!"
    ],
    "البنوك (بطاقات، قروض، حسابات)": [
        "الفيزا متسحوبة جوه المكنة أعمل إيه؟",
        "عايز أستعلم عن القرض الشخصي شروطه إيه",
        "في عملية سحب تمت من حسابي وأنا معملتهاش!",
        "نسيت الباسورد بتاع الأبلكيشن",
        "ممكن أعرف رصيدي كام لو سمحت"
    ],
    "التجارة الإلكترونية (أوردر، توصيل، استرجاع)": [
        "الأوردر اتأخر جداً ومندوب التوصيل مابيردش",
        "المنتج جالي مكسور وعايز أرجعه",
        "القميص طلع مقاسه صغير ينفع أبدله؟",
        "طلبت حاجة وجاتلي حاجة تانية خالص",
        "فلوسي لسه مرجعتش على الفيزا من مرتجع الأسبوع اللي فات"
    ],
    "الدعم الفني (أجهزة، أعطال، تطبيقات)": [
        "الشاشة مبتفتحش بتجيب خطوط وبتقفل",
        "اللاب توب بيسخن جداً وبيهنج",
        "الأبلكيشن بتاعكم بيقفل لوحده كل ما أفتحه",
        "التكييف بينقط ميه ومش بيسقع",
        "الراوتر لمبته حمرا مبتنورش أخضر خالص"
    ],
    "الرعاية الصحية (حجز، صيدلية، تحاليل)": [
        "عايز أحجز ميعاد مع دكتور باطنة بكرا",
        "نتيجة التحليل هتطلع إمتى؟",
        "الدوا ده ناقص في الصيدليات عندكم منه؟",
        "إيه الأوراق المطلوبة لعملية اللوز؟",
        "في دكتور أطفال فاتح دلوقتي؟"
    ],
    "الخدمات الحكومية (مرور، سجل مدني، ضرائب)": [
        "عايز أجدد رخصة العربية إيه المطلوب؟",
        "مواعيد السجل المدني إمتى؟",
        "إزاي أطلع شهادة ميلاد كمبيوتر مستعجل؟",
        "عايز أستعلم عن مخالفات المرور",
        "إيه شروط البطاقة الضريبية؟"
    ]
}

# اللهجات - تعديلات العميل (أمثلة للكلمات)
dialect_modifiers = {
    "saidi": ["يا ولدي", "يا حاج", "جال", "إيه ده", "والنبي"],
    "cairene": ["يا باشا", "يا فندم", "ماشي", "دلوقتي", "أوي", "إزاي"],
    "alexandrian": ["يا صاحبي", "يا جدع", "إزيك", "بتاع ده"],
    "delta": ["يا ابني", "ياخي", "يا جدع"],
    "canal_zone": ["يا معلم", "هقولك"],
    "sinai_bedouin": ["يا شيخ", "يا أخوي", "إيش"]
}


def add_dialect_flavor(text, dialect):
    # مجرد إضافة بسيطة لنكهة اللهجة (في الحقيقة الموديل هيتولى الباقي)
    words = text.split()
    flavor = random.choice(dialect_modifiers[dialect])
    
    if random.random() > 0.5:
       return f"{flavor}، {text}"
    else:
       return f"{text} {flavor}"


# توليد الداتا
dataset = []
NUM_RECORDS = 500

for i in range(NUM_RECORDS):
    domain = random.choice(domains)
    dialect = random.choice(dialects)
    emotion = random.choice(emotions)
    
    base_query = random.choice(customer_templates[domain])
    customer_text = add_dialect_flavor(base_query, dialect)
    
    # محاكاة لرد وكيل خدمة العملاء (ممكن يبقى Response بسيط والموديل بيحسنه بعدين)
    agent_text = "أهلاً بك يا فندم، ثواني وهحللك المشكلة دي فوراً."
    
    conversation = [
        {"role": "customer", "text": customer_text},
        {"role": "agent", "text": agent_text}
    ]
    
    record = {
        "id": f"conv_{i:04d}",
        "dialect": dialect,
        "domain": domain,
        "emotion": emotion,
        "conversation": conversation
    }
    dataset.append(record)

# الحفظ في ملف JSON
output_dir = Path(__file__).parent / "dataset"
output_dir.mkdir(exist_ok=True)
output_path = output_dir / "egyptian_cs_dataset.json"

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(dataset, f, ensure_ascii=False, indent=4)

print(f"✅ تم توليد {NUM_RECORDS} محادثة بنجاح!")
print(f"📁 تم الحفظ في: {output_path}")
