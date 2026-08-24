import os
import json
import hmac
import hashlib
from contextlib import asynccontextmanager
from urllib.parse import parse_qsl

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)


# =========================
# НАСТРОЙКИ
# =========================

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 1282434336

PACKS = {
    100: 20,
    250: 50,
    600: 100,
    1500: 200,
    3000: 350,
}

if not TOKEN:
    raise RuntimeError(
        "BOT_TOKEN не найден в Railway Variables"
    )


# =========================
# ПРОВЕРКА TELEGRAM Mini App
# =========================

def validate_init_data(init_data: str):
    try:
        data = dict(
            parse_qsl(
                init_data,
                keep_blank_values=True
            )
        )

        received_hash = data.pop("hash", None)

        if not received_hash:
            return None

        data_check_string = "\n".join(
            f"{key}={value}"
            for key, value in sorted(data.items())
        )

        secret_key = hmac.new(
            b"WebAppData",
            TOKEN.encode(),
            hashlib.sha256
        ).digest()

        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(
            calculated_hash,
            received_hash
        ):
            return None

        user_json = data.get("user")

        if not user_json:
            return None

        return json.loads(user_json)

    except Exception as error:
        print("ОШИБКА ПРОВЕРКИ INIT DATA:", error)
        return None


# =========================
# TELEGRAM КОМАНДА /start
# =========================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await update.message.reply_text(
        "💜 NEXI CASES BOT работает!\n\n"
        "Заявки из Mini App будут приходить сюда."
    )


# =========================
# КНОПКИ ПОДТВЕРЖДЕНИЯ
# =========================

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query

    if query.from_user.id != ADMIN_ID:
        await query.answer(
            "Нет доступа.",
            show_alert=True
        )
        return

    await query.answer()

    try:
        action, buyer_id, coins, price = (
            query.data.split("_")
        )

        buyer_id = int(buyer_id)
        coins = int(coins)
        price = int(price)

    except Exception as error:
        print("ОШИБКА КНОПКИ:", error)
        return

    if action == "approve":

        await context.bot.send_message(
            chat_id=buyer_id,
            text=(
                "🎉 Оплата подтверждена!\n\n"
                f"💎 Тебе начислен пакет: "
                f"{coins} COINS\n\n"
                "Спасибо за покупку 💜"
            )
        )

        await query.edit_message_text(
            query.message.text
            + "\n\n"
            + "━━━━━━━━━━━━━━\n"
            + "✅ ОПЛАТА ПОДТВЕРЖДЕНА"
        )

    elif action == "reject":

        await context.bot.send_message(
            chat_id=buyer_id,
            text=(
                "❌ Заявка на оплату отклонена.\n\n"
                "Если ты действительно оплатил(а), "
                "обратись в поддержку."
            )
        )

        await query.edit_message_text(
            query.message.text
            + "\n\n"
            + "━━━━━━━━━━━━━━\n"
            + "❌ ЗАЯВКА ОТКЛОНЕНА"
        )


# =========================
# TELEGRAM BOT
# =========================

telegram_app = (
    ApplicationBuilder()
    .token(TOKEN)
    .build()
)

telegram_app.add_handler(
    CommandHandler("start", start)
)

telegram_app.add_handler(
    CallbackQueryHandler(button_handler)
)


# =========================
# ЗАПУСК БОТА В FASTAPI
# =========================

@asynccontextmanager
async def lifespan(app: FastAPI):

    await telegram_app.initialize()
    await telegram_app.start()

    if telegram_app.updater:
        await telegram_app.updater.start_polling(
            drop_pending_updates=False
        )

    print("💜 TELEGRAM БОТ ЗАПУЩЕН")
    print("💜 ОЖИДАЮ ЗАЯВКИ ИЗ MINI APP")

    yield

    if telegram_app.updater:
        await telegram_app.updater.stop()

    await telegram_app.stop()
    await telegram_app.shutdown()


# =========================
# FASTAPI SERVER
# =========================

app = FastAPI(
    title="NEXI CASES API",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# ПРОВЕРКА СЕРВЕРА
# =========================

@app.get("/")
async def home():
    return {
        "status": "ok",
        "message": "NEXI CASES API работает"
    }


@app.get("/health")
async def health():
    return {
        "status": "ok"
    }


# =========================
# ПРИЁМ ЗАЯВКИ
# =========================

@app.post("/payment")
async def payment(request: Request):

    try:
        body = await request.json()

    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Неверный JSON"
        )

    init_data = body.get("initData", "")

    user = validate_init_data(init_data)

    if not user:
        raise HTTPException(
            status_code=403,
            detail=(
                "Не удалось проверить "
                "пользователя Telegram"
            )
        )

    try:
        coins = int(body.get("coins"))
        price = int(body.get("price"))

    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Неверные данные пакета"
        )

    if PACKS.get(coins) != price:
        raise HTTPException(
            status_code=400,
            detail="Неверный пакет или цена"
        )

    user_id = user.get("id")

    first_name = (
        user.get("first_name")
        or "Без имени"
    )

    last_name = (
        user.get("last_name")
        or ""
    )

    full_name = (
        f"{first_name} {last_name}"
    ).strip()

    username = user.get("username")

    username_text = (
        f"@{username}"
        if username
        else "нет username"
    )

    admin_text = (
        "💜 НОВАЯ ЗАЯВКА НА ОПЛАТУ\n\n"
        f"👤 Пользователь: {full_name}\n"
        f"🔗 Username: {username_text}\n"
        f"🆔 ID: {user_id}\n\n"
        f"💎 Пакет: {coins} COINS\n"
        f"💰 Сумма: {price} ₽\n\n"
        "⚠️ Проверь оплату вручную."
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ ПОДТВЕРДИТЬ",
                callback_data=(
                    f"approve_{user_id}_"
                    f"{coins}_{price}"
                )
            ),
            InlineKeyboardButton(
                "❌ ОТКЛОНИТЬ",
                callback_data=(
                    f"reject_{user_id}_"
                    f"{coins}_{price}"
                )
            ),
        ]
    ])

    try:
        await telegram_app.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_text,
            reply_markup=keyboard
        )

        print(
            f"💜 ЗАЯВКА ОТПРАВЛЕНА: "
            f"{user_id} | "
            f"{coins} COINS | "
            f"{price} ₽"
        )

        return {
            "ok": True,
            "message": "Заявка отправлена"
        }

    except Exception as error:

        print(
            "ОШИБКА ОТПРАВКИ ЗАЯВКИ:",
            repr(error)
        )

        raise HTTPException(
            status_code=500,
            detail="Не удалось отправить заявку"
        )
