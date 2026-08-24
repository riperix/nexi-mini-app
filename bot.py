# bot.py

```python
import os
import asyncio
import threading

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

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

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 1282434336

PACKS = {
    100: 20,
    250: 50,
    600: 100,
    1500: 200,
    3000: 350,
}

# =========================
# WEB SERVER
# =========================

api = FastAPI()


class PaymentRequest(BaseModel):
    coins: int
    price: int
    user_id: int
    username: str = ""
    first_name: str = ""


telegram_app = None
telegram_loop = None


@api.get("/")
async def health():
    return {
        "status": "ok",
        "service": "NEXI CASES",
    }


@api.post("/payment")
async def payment(request: PaymentRequest):

    if PACKS.get(request.coins) != request.price:
        raise HTTPException(
            status_code=400,
            detail="Неверный пакет",
        )

    if not telegram_app or not telegram_loop:
        raise HTTPException(
            status_code=503,
            detail="Бот ещё не запущен",
        )

    username = (
        f"@{request.username}"
        if request.username
        else "нет username"
    )

    admin_text = (
        "🚨 НОВАЯ ЗАЯВКА НА ОПЛАТУ\n\n"
        f"👤 Имя: {request.first_name or 'Неизвестно'}\n"
        f"🔗 Username: {username}\n"
        f"🆔 ID: {request.user_id}\n\n"
        f"💎 Пакет: {request.coins} COINS\n"
        f"💰 Сумма: {request.price} ₽\n\n"
        "⚠️ Пользователь нажал «Я ОПЛАТИЛ(А)»."
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ ПОДТВЕРДИТЬ",
                callback_data=(
                    f"approve:{request.user_id}:{request.coins}"
                ),
            ),
            InlineKeyboardButton(
                "❌ ОТКЛОНИТЬ",
                callback_data=(
                    f"reject:{request.user_id}:{request.coins}"
                ),
            ),
        ]
    ])

    future = asyncio.run_coroutine_threadsafe(
        telegram_app.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_text,
            reply_markup=keyboard,
        ),
        telegram_loop,
    )

    try:
        future.result(timeout=15)
    except Exception as error:
        print("ОШИБКА ОТПРАВКИ:", repr(error))
        raise HTTPException(
            status_code=500,
            detail="Не удалось отправить заявку",
        )

    print(
        "ЗАЯВКА ОТПРАВЛЕНА:",
        request.user_id,
        request.coins,
        request.price,
    )

    return {
        "ok": True,
    }


# =========================
# TELEGRAM BOT
# =========================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "💜 NEXI CASES BOT работает.\n\n"
        "Я принимаю заявки из Mini App."
    )


async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    if query.from_user.id != ADMIN_ID:
        await query.answer(
            "Нет доступа.",
            show_alert=True,
        )
        return

    await query.answer()

    try:
        action, buyer_id, coins = query.data.split(":")

        buyer_id = int(buyer_id)
        coins = int(coins)

    except Exception as error:
        print("ОШИБКА КНОПКИ:", repr(error))
        return

    if coins not in PACKS:
        return

    if action == "approve":

        await context.bot.send_message(
            chat_id=buyer_id,
            text=(
                "🎉 ОПЛАТА ПОДТВЕРЖДЕНА!\n\n"
                f"💎 Тебе начислен пакет: "
                f"{coins} COINS\n\n"
                "Спасибо за покупку 💜"
            ),
        )

        await query.edit_message_text(
            query.message.text
            + "\n\n━━━━━━━━━━━━━━\n"
            + "✅ ОПЛАТА ПОДТВЕРЖДЕНА"
        )

    elif action == "reject":

        await context.bot.send_message(
            chat_id=buyer_id,
            text=(
                "❌ Заявка на оплату отклонена.\n\n"
                "Если произошла ошибка, "
                "обратись в поддержку."
            ),
        )

        await query.edit_message_text(
            query.message.text
            + "\n\n━━━━━━━━━━━━━━\n"
            + "❌ ЗАЯВКА ОТКЛОНЕНА"
        )


# =========================
# ЗАПУСК БОТА
# =========================

def run_bot():

    global telegram_app
    global telegram_loop

    if not TOKEN:
        raise ValueError(
            "BOT_TOKEN не найден в Variables"
        )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    telegram_loop = loop

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

    telegram_app.run_polling(
        allowed_updates=Update.ALL_TYPES,
    )


# =========================
# ЗАПУСК ВСЕГО
# =========================

if __name__ == "__main__":

    bot_thread = threading.Thread(
        target=run_bot,
        daemon=True,
    )

    bot_thread.start()

    port = int(
        os.getenv("PORT", "8000")
    )

    print(
        f"WEB SERVER ЗАПУЩЕН НА PORT {port}"
    )

    uvicorn.run(
        api,
        host="0.0.0.0",
        port=port,
    )
```
