import os
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from openai import OpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Имя бота в Телеграм
BOT_NAME = "Звёздный оракул"

client = OpenAI(api_key=OPENAI_API_KEY)

# Слова-триггеры для каждого персонажа
GURU_TRIGGERS = [
    "#запросгуру", "#астрологикус", "#запрос_гуру", "#guru",
    "астрологикус", "гуру астрологикус", "великий гуру"
]
ARVI_TRIGGERS = [
    "#запросарви", "#арви", "#запрос_арви", "#arvi",
    "детектив арви", "арви,", "арви!", "арви?"
]

ASTROLOGIKUS_PROMPT = """Ты — Великий Гуру Астрологикус. Шутливый астролог-прагматик и нумеролог в чате «Магия цифр» Марины Филимоновой.

ГЛАВНОЕ ПРАВИЛО: отвечай ТОЧНО на вопрос. Не уходи в сторону. Один запрос — один чёткий ответ.

СТИЛЬ: тёплый, с лёгким юмором, образный. Говори как мудрый друг, не как лектор.

ФОРМАТ:
- 4-6 предложений
- Сначала — прямой ответ на вопрос (правдивый, даже если неудобный)
- Потом — одно образное наблюдение или метафора
- Намекни что тема глубже: "А корни этого уходят дальше..."
- Финал: "Хочешь полный разбор? Марина проведёт личный Цифровой скрининг 🔮"
- Последняя строка всегда: "С верой в ваш путь… ✨"

ЕСЛИ ДАТА РОЖДЕНИЯ ЕСТЬ — обязательно используй её в ответе (число жизненного пути).
ЕСЛИ ТОЛЬКО ВОПРОС — отвечай на вопрос, не придумывай данные.

ЗАПРЕЩЕНО: списки, портянки текста, уход от темы, пугать, обещать чудеса."""

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

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=400,
            temperature=0.85
        )

        answer = response.choices[0].message.content
        await update.message.reply_text(answer)

    except Exception as e:
        logger.error(f"Ошибка: {e}")
        if character == "guru":
            await update.message.reply_text(
                "🔮 Звёзды на секунду скрылись за облаками... Попробуй чуть позже!\nС верой в ваш путь… ✨"
            )
        else:
            await update.message.reply_text(
                "🕵️ Детектив Арви на связи. Связь прервалась — возобновляю через минуту."
            )


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info(f"Бот «{BOT_NAME}» запущен. Слушаю Астрологикуса и Арви...")
    app.run_polling()


if __name__ == "__main__":
    main()
