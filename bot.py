# bot.py

```python
import os
import json

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# =========================
# НАСТРОЙКИ
# =========================

TOKEN = os.getenv("BOT_TOKEN")

# ТВОЙ TELEGRAM ID
ADMIN_ID = 1282434336


# =========================
# ПАКЕТЫ
# =========================

PACKS = {
    "100": {"coins": 100, "price": 20},
    "250": {"coins": 250, "price": 50},
    "600": {"coins": 600, "price": 100},
    "1500": {"coins": 1500, "price": 200},
    "3000": {"coins": 3000, "price": 350},
}


# =========================
# /START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💜 NEXI CASES BOT работает.\n\n"
        "Заявки из Mini App будут приходить сюда."
    )


# =========================
# ПОЛУЧЕНИЕ ЗАЯВКИ ИЗ MINI APP
# =========================

async def web_app_data(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    try:
        raw_data = update.effective_message.web_app_data.data
        data = json.loads(raw_data)

    except Exception as error:
        print(f"ОШИБКА ЧТЕНИЯ MINI APP: {error}")
        return

    if data.get("type") != "payment_request":
        return

    coins = int(data.get("coins", 0))
    price = int(data.get("price", 0))

    if coins <= 0 or price <= 0:
        print("НЕВЕРНЫЕ ДАННЫЕ ЗАЯВКИ:", data)
        return

    # Проверяем, что пакет настоящий
    valid_pack = None

    for pack_id, pack in PACKS.items():
        if pack["coins"] == coins and pack["price"] == price:
            valid_pack = pack_id
            break

    if not valid_pack:
        print("НЕИЗВЕСТНЫЙ ПАКЕТ:", data)
        return

    user = update.effective_user

    username = (
        f"@{user.username}"
        if user.username
        else "Нет username"
    )

    admin_text = (
        "🚨 НОВАЯ ЗАЯВКА НА ОПЛАТУ\n\n"
        f"👤 Имя: {user.full_name}\n"
        f"🔗 Username: {username}\n"
        f"🆔 Telegram ID: {user.id}\n\n"
        f"💎 Пакет: {coins} NEXI COINS\n"
        f"💰 Сумма: {price} ₽\n\n"
        "⚠️ Пользователь нажал «Я ОПЛАТИЛ(А)»."
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ ПОДТВЕРДИТЬ",
                callback_data=f"approve_{user.id}_{valid_pack}"
            ),
            InlineKeyboardButton(
                "❌ ОТКЛОНИТЬ",
                callback_data=f"reject_{user.id}_{valid_pack}"
            ),
        ]
    ])

    try:
        # ЗАЯВКА ПРИХОДИТ ТЕБЕ В ЛИЧНЫЙ ЧАТ
        # ОТ @NexiCasesBot
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_text,
            reply_markup=keyboard
        )

        print(
            f"ЗАЯВКА ОТПРАВЛЕНА: "
            f"user={user.id}, coins={coins}, price={price}"
        )

    except Exception as error:
        print(f"ОШИБКА ОТПРАВКИ ЗАЯВКИ: {error}")


# =========================
# КНОПКИ АДМИНА
# =========================

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    user = query.from_user

    # Только ты можешь нажимать
    if user.id != ADMIN_ID:
        await query.answer(
            "❌ У тебя нет доступа.",
            show_alert=True
        )
        return

    await query.answer()

    data = query.data

    # =========================
    # ПОДТВЕРДИТЬ
    # =========================

    if data.startswith("approve_"):

        try:
            _, buyer_id, pack_id = data.split("_")

            buyer_id = int(buyer_id)
            pack = PACKS.get(pack_id)

            if not pack:
                return

            await context.bot.send_message(
                chat_id=buyer_id,
                text=(
                    "🎉 ОПЛАТА ПОДТВЕРЖДЕНА!\n\n"
                    f"💎 Твой пакет: "
                    f"{pack['coins']} NEXI COINS\n\n"
                    "Спасибо за покупку 💜"
                )
            )

            await query.edit_message_text(
                query.message.text
                + "\n\n━━━━━━━━━━━━━━\n"
                + "✅ ОПЛАТА ПОДТВЕРЖДЕНА"
            )

        except Exception as error:
            print(f"ОШИБКА ПОДТВЕРЖДЕНИЯ: {error}")

        return

    # =========================
    # ОТКЛОНИТЬ
    # =========================

    if data.startswith("reject_"):

        try:
            _, buyer_id, pack_id = data.split("_")

            buyer_id = int(buyer_id)

            await context.bot.send_message(
                chat_id=buyer_id,
                text=(
                    "❌ Заявка на оплату отклонена.\n\n"
                    "Если ты уже оплатил(а), "
                    "обратись в поддержку."
                )
            )

            await query.edit_message_text(
                query.message.text
                + "\n\n━━━━━━━━━━━━━━\n"
                + "❌ ЗАЯВКА ОТКЛОНЕНА"
            )

        except Exception as error:
            print(f"ОШИБКА ОТКЛОНЕНИЯ: {error}")

        return


# =========================
# ОШИБКИ
# =========================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):
    print(f"ОШИБКА БОТА: {context.error}")


# =========================
# ЗАПУСК
# =========================

def main():

    if not TOKEN:
        raise ValueError(
            "BOT_TOKEN не найден. "
            "Добавь его в Railway → Variables."
        )

    app = (
        ApplicationBuilder()
        .token(TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .pool_timeout(30)
        .build()
    )

    app.add_handler(
        CommandHandler("start", start)
    )

    # ПОЛУЧАЕМ ДАННЫЕ ИЗ MINI APP
    app.add_handler(
        MessageHandler(
            filters.StatusUpdate.WEB_APP_DATA,
            web_app_data
        )
    )

    # Кнопки ПОДТВЕРДИТЬ / ОТКЛОНИТЬ
    app.add_handler(
        CallbackQueryHandler(button_handler)
    )

    app.add_error_handler(error_handler)

    print("💜 NEXI CASES BOT ЗАПУЩЕН")

    app.run_polling(
        drop_pending_updates=False
    )


if __name__ == "__main__":
    main()
```
