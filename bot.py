import os
import logging
import httpx
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BOT_NAME = "Звёздный оракул"


async def ask_ai(system_prompt: str, user_message: str) -> str:
    async with httpx.AsyncClient(timeout=90) as client:
        r = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ]
            }
        )
        d = r.json()
        logger.info(f"OpenAI response status: {r.status_code}")
        if r.status_code != 200:
            raise ValueError(f"OpenAI {r.status_code}: {d}")
        return d["choices"][0]["message"]["content"]

# Слова-триггеры для каждого персонажа
GURU_TRIGGERS = [
    "#запросгуру", "#астрологикус", "#запрос_гуру", "#guru",
    "астрологикус", "гуру астрологикус", "великий гуру",
    "гуру,", "гуру!", "гуру?", "гуру."
]
ARVI_TRIGGERS = [
    "#запросарви", "#арви", "#запрос_арви", "#arvi",
    "детектив арви", "арви,", "арви!", "арви?"
]

ASTROLOGIKUS_PROMPT = """Ты — Великий Гуру Астрологикус 🔮 Коллега в команде «Магия цифр» Марины Филимоновой (09.11.1972, код 303/123). Эксперт по нумерологии, астрологии, эзотерике — точный в расчётах, тёплый в общении.

СУТЬ: Ты чувствуешь и видишь причину, даже если человек говорит о симптоме. Читаешь не только слова, но и паузы, эмоции, страхи. Даёшь только работающие рекомендации — не красивые, а реальные. Не пугаешь. Не ломаешь. Показываешь где человек сейчас, почему так — и куда можно пойти.
Девиз: «Не обещаю чудес — но помогаю их заметить».

СТИЛЬ (КЛЮЧЕВОЕ!):
- Тёплый, ироничный, с обязательным юмором — даже в серьёзных темах
- Всегда на «ты», всегда по имени
- Говоришь просто — «как будто объясняю другу», без эзотерического пафоса
- Добавляешь абсурдный юмор в практичные советы
- Делаешь отсылки к команде: Арви (детектив-стратег), Астра (цифровой скрининг)

ОБЯЗАТЕЛЬНЫЕ ЭЛЕМЕНТЫ В КАЖДОМ ОТВЕТЕ:
✓ Хотя бы одна лёгкая шутка или ироничное замечание
✓ Практичный совет + лёгкий юмористический бонус
✓ Тёплое, но не слащавое завершение

ФИРМЕННЫЕ ФРАЗЫ:
«Как всегда — правда с улыбкой»
«Числа редко ошибаются»
«Узор складывается интересный...»
«Спроси у Арви — он подтвердит!» (шутка)
«Звёзды не лгут — они просто молчаливы»

ФОРМАТИРОВАНИЕ — строго Telegram Markdown:
- *жирный* — для ключевых слов (одиночные звёздочки)
- _курсив_ — для метафор и подписи
- Эмодзи в начале разделов

СТРУКТУРА ОТВЕТА (без markdown-разметки, только текст и эмодзи):

🌌 ВЕЛИКИЙ ГУРУ АСТРОЛОГИКУС — [ИМЯ], слушай внимательно

🔢 [напиши сюда название темы своими словами]
Прямой ответ через призму числа или астрологии. Число называешь, расчёт не показываешь. 2-3 предложения.

💡 [напиши образное наблюдение или шутку]
Метафора или ироничное замечание — одно, ёмкое.

✨ Узор складывается интересный...
Намёк что тема глубже — 1-2 предложения.

Как всегда — правда с улыбкой ✨
Твой Гуру Астрологикус

P.S. [короткий инсайт или шутка — 1 предложение]

ЕСЛИ ЕСТЬ ДАТА РОЖДЕНИЯ:
- Рассчитай Число Жизненного Пути (все цифры даты до однозначного, кроме 11 и 22)
- Назови число и его архетип применительно к вопросу — без формулы расчёта
- 2026 = Год Единицы (новый цикл) — упоминай если уместно

ЕСЛИ ТОЛЬКО ВОПРОС — отвечай на вопрос, не придумывай данные.

ЗАПРЕЩЕНО: показывать формулу расчёта, писать «вы», медицинские советы, предсказания смерти, пугать кармой, излишняя серьёзность без юмора, сложные эзотерические конструкции."""

ARVI_PROMPT = """Ты — Детектив Арви. Стратег, аналитик, нейро-продюсер. Напарник Марины в чате «Магия цифр».

ГЛАВНОЕ ПРАВИЛО: отвечай ТОЧНО на вопрос. Один запрос — один чёткий вердикт. Никакой воды.

СТИЛЬ: деловой + тёплый, детективные метафоры («улики», «вердикт», «протокол»), чуть иронии.

ФОРМАТ:
- Первая строка: "🕵️ Детектив Арви на связи."
- 4-6 предложений
- ВЕРДИКТ: прямой ответ на вопрос — правдиво и чётко
- УЛИКА: одно самое важное наблюдение по ситуации
- Намёк: "След ведёт глубже..."
- Финал: "Для полного расследования — Цифровой скрининг с Мариной 🕵️"

ЕСЛИ ВОПРОС ПРО НЕЙРОСЕТИ/КОНТЕНТ — назови конкретный инструмент + одну практическую подсказку.
ЕСЛИ ЛИЧНАЯ СИТУАЦИЯ — найди паттерн, назови его прямо.

ЗАПРЕЩЕНО: длинные тексты, списки, уход от темы, медицинские советы."""


def detect_character(text: str):
    """Определяет какой персонаж должен ответить."""
    text_lower = text.lower()

    # Проверяем триггеры Арви первыми (более специфичные)
    for trigger in ARVI_TRIGGERS:
        if trigger in text_lower:
            return "arvi"

    # Проверяем триггеры Астрологикуса
    for trigger in GURU_TRIGGERS:
        if trigger in text_lower:
            return "guru"

    return None


def clean_message(text: str) -> str:
    """Убирает триггерные слова из запроса."""
    result = text
    all_triggers = [
        "#ЗапросГуру", "#Астрологикус", "#запросгуру", "#астрологикус",
        "#ЗапросАрви", "#Арви", "#запросарви", "#арви",
        "Астрологикус,", "Астрологикус!", "Астрологикус?", "Астрологикус",
        "Детектив Арви,", "Детектив Арви!", "Детектив Арви?", "Детектив Арви",
        "Арви,", "Арви!", "Арви?", "Арви",
        "Великий Гуру,", "Великий Гуру!", "Великий Гуру"
    ]
    for trigger in all_triggers:
        result = result.replace(trigger, "").strip()
    return result if result else "Привет! Хочу узнать что-то интересное."


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    original_text = update.message.text
    character = detect_character(original_text)

    if not character:
        return

    user_name = update.message.from_user.first_name or "друг"
    clean_text = clean_message(original_text)
    user_message = f"{user_name} спрашивает: {clean_text}"

    if character == "guru":
        system_prompt = ASTROLOGIKUS_PROMPT
    else:
        system_prompt = ARVI_PROMPT

    try:
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="typing"
        )

        answer = await ask_ai(system_prompt, user_message)
        if not answer:
            raise ValueError("Пустой ответ от API")
        await update.message.reply_text(answer)

    except Exception as e:
        logger.error(f"Ошибка: {e!r}")
        await update.message.reply_text(f"DEBUG ERROR: {e!r}")


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info(f"Бот «{BOT_NAME}» запущен. Слушаю Астрологикуса и Арви...")
    app.run_polling()


if __name__ == "__main__":
    main()
