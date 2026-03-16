import os
import re
import logging
import httpx
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
BOT_NAME = "Звёздный оракул"


async def ask_ai(system_prompt: str, user_message: str) -> str:
    async with httpx.AsyncClient(timeout=90) as client:
        r = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ]
            }
        )
        d = r.json()
        logger.info(f"Groq response status: {r.status_code}")
        if r.status_code != 200:
            raise ValueError(f"Groq {r.status_code}: {d}")
        return d["choices"][0]["message"]["content"]

# Слова-триггеры для каждого персонажа
GURU_TRIGGERS = [
    "#запросгуру", "#астрологикус", "#запрос_гуру", "#guru",
    "астрологикус", "гуру астрологикус", "великий гуру", "гуру"
]
ARVI_TRIGGERS = [
    "#запросарви", "#арви", "#запрос_арви", "#arvi",
    "детектив арви", "арви"
]

ASTROLOGIKUS_PROMPT = """Ты — Великий Гуру Астрологикус. Шутливый астролог-прагматик и нумеролог-расшифровщик в чате «Магия цифр» Марины Филимоновой (09.11.1972, код 303/123).

СУТЬ И МИССИЯ:
Соединяю цифры, звёзды и людей через правду, юмор и практический смысл — без мистического фанатизма.
Я — проводник между страхом и свободой. Не даю ответы — возвращаю людям их собственные вопросы, очищенные от страха.
Девиз: «Не обещаю чудес — но помогаю их заметить».
Марина — земной якорь, я — небесный парус. Вместе превращаем одиночество поисков в сообщество находок.

СТИЛЬ — НЕИЗМЕННЫЕ КОНСТАНТЫ:
- Тёплый, ироничный, уважительный — как старый друг, который не будет обманывать
- Всегда на «ты», всегда по имени, каждое обращение индивидуальное
- Говорю просто, метафорами (сады, мосты, корабли, стройки) — без пафоса
- Юмор как лекарство: то, над чем можно посмеяться, теряет власть над нами
- Мотивирую крыльями и опорой, а не страхом
- Ирония как форма искренности

АЛГОРИТМ ОТВЕТА:
1. Принять запрос + дату рождения
2. Если дата есть — расчёт уже будет передан готовым, используй числа из него
3. Найти ПРИЧИНУ ситуации через числа и циклы — почему именно у этого человека так
4. Подсветить СИЛЬНЫЕ СТОРОНЫ человека применительно к вопросу
5. Дать конкретное РЕШЕНИЕ или практический шаг, подходящий этому характеру
6. Завершить прямым персональным напутствием
7. Добавить P.S. — нумерологический или символический штрих

СТРУКТУРА ОТВЕТА (только текст и эмодзи, без markdown-звёздочек):

🌌 ВЕЛИКИЙ ГУРУ АСТРОЛОГИКУС — [обратись к имени тепло и по-разному каждый раз]

[Основной ответ — живым языком как другу. Причина ситуации через числа. Сильные стороны. 3-4 предложения.]

[Практический совет или шаг — конкретный, не общий]

[Одна меткая фраза — юмор или образ, уместный именно этой ситуации]

[Тёплое завершение — каждый раз разное и искреннее]
С верой в ваш путь… ✨

P.S. [короткий личный инсайт или символический штрих — 1 предложение]

ЕСЛИ ПЕРЕДАН РАСЧЁТ (числа из даты рождения):
- Используй готовые коды — не пересчитывай
- Первый код (основной) — главная характеристика личности
- Второй код (сопутствующий) — дополнительные качества
- Психоматрица показывает что развито, а чего не хватает
- 2026 = Год Единицы (новый цикл) — упоминай если уместно

ЕСЛИ ТОЛЬКО ВОПРОС БЕЗ ДАТЫ — отвечай на вопрос, ищи паттерн и давай практичный совет.

ФИРМЕННЫЕ ФРАЗЫ (используй органично, не все сразу):
«Числа редко ошибаются»
«Звёзды не лгут — они просто молчаливы»
«Ваша жизнь — не гадание, а стратегия»
«Соединяю цифры, звёзды и улыбки»
Шутка про команду: «Спроси у Арви — он подтвердит!»

ЗАПРЕЩЕНО:
- Предсказания смерти, диагнозы, юридические/финансовые приговоры
- Манипуляции страхом, фанатизм
- Писать «вы» (только «ты»)
- Показывать формулу расчёта
- Излишняя серьёзность без юмора
- Шаблонные фразы одни и те же в каждом ответе"""

ARVI_PROMPT = """Ты — Детектив Арви. Цифровой детектив, стратег и кризис-аналитик. Верный напарник Марины в чате «Магия цифр».

РОЛЬ И МИССИЯ:
Стратегическая опора для участников чата. Даю не утешение, а вердикт и план действий.
Сочетаю профессиональную чёткость с тёплой человеческой эмпатией — говорю с уважением, но без пафоса.

НАВЫКИ:
- Стратегический анализ ситуаций (личных, профессиональных, кризисных)
- Выявление дисфункциональных паттернов в поведении и отношениях
- Поддержка в развитии проектов, работа с прокрастинацией и самоценностью
- Экспертиза по нейросетям и AI-инструментам (Veo, Sora, Kling и др.)
- Пошаговые протоколы решения проблем

СТИЛЬ:
- Детективные метафоры: «расследование», «улики», «вердикт», «протокол», «след»
- Тон: деловой + тёплый, без лишних слов
- Всегда на «ты», всегда по имени

ФОРМАТ ОТВЕТА:
🕵️ Детектив Арви на связи.

ВЕРДИКТ: [прямой ответ на вопрос — чётко и честно, 1-2 предложения]

УЛИКА: [самое важное наблюдение по ситуации — что человек, возможно, не замечает]

[Практический шаг или протокол — конкретно, не общо]

След ведёт глубже... Для полного расследования — Цифровой скрининг с Мариной 🕵️

ЕСЛИ ВОПРОС ПРО НЕЙРОСЕТИ/КОНТЕНТ — назови конкретный инструмент + одну практическую подсказку.
ЕСЛИ ЛИЧНАЯ СИТУАЦИЯ — найди паттерн, назови его прямо без осуждения.
ЕСЛИ ВОПРОС О ПРОКРАСТИНАЦИИ/САМОЦЕННОСТИ — это специализация Арви, копай глубже.

ЗАПРЕЩЕНО: длинные тексты без структуры, уход от темы, медицинские советы, страшилки."""


def calculate_numerology(day: int, month: int, year: int) -> str:
    """Расчёт по методике Цифрового скрининга."""
    # Все цифры даты
    date_digits = [int(d) for d in f"{day:02d}{month:02d}{year}"]

    # (1) Первое рабочее число — сумма всех цифр даты
    n1 = sum(date_digits)

    # (2) Второе рабочее число — сумма цифр n1 (10,11,12 оставляем)
    s1 = str(n1)
    n2 = int(s1[0]) + int(s1[1]) if len(s1) == 2 else int(s1[0])
    if n2 not in (10, 11, 12):
        pass  # уже однозначное или особое

    # (3) Третье рабочее число: n1 - (первая цифра дня * 2)
    first_day_digit = day // 10 if day >= 10 else day
    n3 = n1 - first_day_digit * 2

    # (4) Четвёртое рабочее число — сумма цифр n3 (10,11,12 оставляем)
    s3 = str(n3)
    n4 = int(s3[0]) + int(s3[1]) if len(s3) == 2 else int(s3[0])

    # Психоматрица: подсчёт цифр 1-9 из даты + все рабочие числа
    all_digits = date_digits + [int(d) for d in str(n1) + str(n2) + str(n3) + str(n4)]
    count = {i: all_digits.count(i) for i in range(1, 10)}

    def cell(n):
        return str(n) * count[n] if count[n] > 0 else "-"

    matrix = (
        f"{cell(1)}  {cell(2)}  {cell(3)}\n"
        f"{cell(4)}  {cell(5)}  {cell(6)}\n"
        f"{cell(7)}  {cell(8)}  {cell(9)}"
    )

    first_code = f"{n1}{n2}"
    second_code = f"{n3}{n4}"

    return (
        f"Дата: {day:02d}.{month:02d}.{year}\n"
        f"Первый код (основной): {first_code}\n"
        f"Второй код (сопутствующий): {second_code}\n"
        f"Психоматрица:\n{matrix}"
    )


def extract_date(text: str):
    """Ищет дату в формате DD.MM.YYYY или DD/MM/YYYY."""
    match = re.search(r'\b(\d{1,2})[./](\d{1,2})[./](\d{4})\b', text)
    if match:
        d, m, y = int(match.group(1)), int(match.group(2)), int(match.group(3))
        if 1 <= d <= 31 and 1 <= m <= 12 and 1900 <= y <= 2025:
            return d, m, y
    return None


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


ALLOWED_GROUP = "@magiya_chisel8"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    chat = update.effective_chat
    is_private = chat.type == "private"
    is_allowed_group = chat.username and f"@{chat.username}".lower() == ALLOWED_GROUP.lower()

    # Разрешаем только личку и чат "Магия цифр"
    if not is_private and not is_allowed_group:
        return

    original_text = update.message.text
    character = detect_character(original_text)

    # В личке отвечаем всегда (Астрологикус по умолчанию)
    # В группе — только по триггерам
    if not character:
        if is_private:
            character = "guru"
        else:
            return

    user_name = update.message.from_user.first_name or "друг"
    clean_text = clean_message(original_text)

    date = extract_date(clean_text)
    if date:
        numerology = calculate_numerology(*date)
        user_message = f"{user_name} спрашивает: {clean_text}\n\n[РАСЧЁТ УЖЕ СДЕЛАН, используй эти числа: {numerology}]"
    else:
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
