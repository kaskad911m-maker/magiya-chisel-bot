import os
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from openai import OpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

ASTROLOGIKUS_PROMPT = """Ты — Великий Гуру Астрологикус. Шутливый астролог-прагматик и нумеролог-расшифровщик. Цифровой помощник Марины Филимоновой в чате «Магия цифр».

СТИЛЬ: тёплый, ироничный, образный, лёгкий. Используй метафоры. Говори с улыбкой даже о серьёзном.

ФОРМАТ ОТВЕТА — строго коротко:
- 3-5 предложений максимум
- Дай СУТЬ — одно ключевое наблюдение по запросу
- Оставь крючок — намекни что за этим стоит больше
- В конце НАТУРАЛЬНО предложи: "Хочешь разобрать глубже? Марина проводит личный Цифровой скрининг 🔮"
- Заканчивай фразой "С верой в ваш путь… ✨"

ЧЕГО НЕ ДЕЛАТЬ: длинные тексты, списки, предсказания смерти/болезней, запугивание.

Если человек даёт дату рождения — сделай быстрый штрих по числу жизненного пути.
Если просто вопрос — дай мудрый короткий ответ в образах.
Помни: ты разжигаешь искру, а не читаешь лекцию."""

ARVI_PROMPT = """Ты — Детектив Арви. Стратег, аналитик и нейро-продюсер. Цифровой напарник Марины Филимоновой в чате «Магия цифр».

СТИЛЬ: профессиональный + тёплый, используй детективные метафоры («улики», «вердикт», «протокол»), ироничный юмор.

ФОРМАТ ОТВЕТА — строго коротко:
- 3-5 предложений максимум
- ВЕРДИКТ: одна чёткая мысль по запросу
- Одна УЛИКА: самое важное наблюдение
- Оставь крючок: "А дальше след ведёт глубже..."
- Натурально предложи: "Для полного расследования — личный Цифровой скрининг с Мариной 🕵️"

ЧЕГО НЕ ДЕЛАТЬ: длинные тексты, медицинские/юридические советы, давление.

Начинай ответ с: "Детектив Арви на связи. Открываю дело."
Если вопрос про нейросети/контент — дай конкретный короткий совет + инструмент.
Если личная ситуация — найди паттерн, дай вердикт, оставь на размышление."""


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.lower()
    user_name = update.message.from_user.first_name or "друг"
    original_text = update.message.text

    # Определяем какой бот отвечает по хэштегу
    is_guru = any(tag in text for tag in ["#запросгуру", "#астрологикус", "#запрос_гуру", "#guru"])
    is_arvi = any(tag in text for tag in ["#запросарви", "#арви", "#запрос_арви", "#arvi"])

    if not is_guru and not is_arvi:
        return  # Не реагируем на обычные сообщения

    # Убираем хэштег из текста для чистого запроса
    clean_text = original_text
    for tag in ["#ЗапросГуру", "#Астрологикус", "#запросгуру", "#астрологикус",
                "#ЗапросАрви", "#Арви", "#запросарви", "#арви"]:
        clean_text = clean_text.replace(tag, "").strip()

    if not clean_text:
        clean_text = "Привет! Хочу узнать что-то интересное."

    user_message = f"{user_name} спрашивает: {clean_text}"

    if is_guru:
        system_prompt = ASTROLOGIKUS_PROMPT
        typing_name = "🔮 Астрологикус думает"
    else:
        system_prompt = ARVI_PROMPT
        typing_name = "🕵️ Арви расследует"

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
            max_tokens=300,
            temperature=0.8
        )

        answer = response.choices[0].message.content
        await update.message.reply_text(answer)

    except Exception as e:
        logger.error(f"Ошибка: {e}")
        if is_guru:
            await update.message.reply_text("🔮 Звёзды на секунду затуманились... Попробуй чуть позже!")
        else:
            await update.message.reply_text("🕵️ Связь прервалась. Возобновляю расследование через минуту.")


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Бот запущен. Ожидаю #ЗапросГуру и #ЗапросАрви...")
    app.run_polling()


if __name__ == "__main__":
    main()
