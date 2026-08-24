# bot.py

```python
import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# =========================
# НАСТРОЙКИ
# =========================

# Railway → Variables → BOT_TOKEN
TOKEN = os.getenv("BOT_TOKEN")

# ТВОЙ TELEGRAM ID — СЮДА ПРИХОДЯТ ЗАЯВКИ
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
    keyboard = [
        [InlineKeyboardButton("💎 100 COINS — 20 ₽", callback_data="buy_100")],
        [InlineKeyboardButton("💎 250 COINS — 50 ₽", callback_data="buy_250")],
        [InlineKeyboardButton("💎 600 COINS — 100 ₽", callback_data="buy_600")],
        [InlineKeyboardButton("💎 1500 COINS — 200 ₽", callback_data="buy_1500")],
        [InlineKeyboardButton("💎 3000 COINS — 350 ₽", callback_data="buy_3000")],
    ]

    await update.message.reply_text(
        "💜 Добро пожаловать в NEXI CASES!\n\n"
        "Выбери пакет:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# =========================
# ВСЕ КНОПКИ
# =========================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    user = query.from_user

    # -------------------------
    # ВЫБОР ПАКЕТА
    # -------------------------

    if data.startswith("buy_"):
        pack_id = data.replace("buy_", "")
        pack = PACKS.get(pack_id)

        if not pack:
            await query.message.reply_text("❌ Пакет не найден.")
            return

        context.user_data["pack_id"] = pack_id

        keyboard = [
            [InlineKeyboardButton("💳 Я ОПЛАТИЛ", callback_data="paid")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel")],
        ]

        await query.message.reply_text(
            f"💎 Вы выбрали: {pack['coins']} COINS\n"
            f"💰 К оплате: {pack['price']} ₽\n\n"
            "Переведи деньги на карту / по СБП.\n\n"
            "После оплаты нажми «💳 Я ОПЛАТИЛ».",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    # -------------------------
    # Я ОПЛАТИЛ
    # -------------------------

    if data == "paid":
        pack_id = context.user_data.get("pack_id")
        pack = PACKS.get(pack_id)

        if not pack:
            await query.message.reply_text(
                "⚠️ Сначала выбери пакет через /start."
            )
            return

        username = (
            f"@{user.username}"
            if user.username
            else "нет username"
        )

        admin_keyboard = [
            [
                InlineKeyboardButton(
                    "✅ ПОДТВЕРДИТЬ",
                    callback_data=f"approve_{user.id}_{pack_id}",
                ),
                InlineKeyboardButton(
                    "❌ ОТКЛОНИТЬ",
                    callback_data=f"reject_{user.id}_{pack_id}",
                ),
            ]
        ]

        admin_text = (
            "💜 НОВАЯ ЗАЯВКА НА ОПЛАТУ\n\n"
            f"👤 Пользователь: {user.full_name}\n"
            f"🔗 Username: {username}\n"
            f"🆔 ID: {user.id}\n\n"
            f"💎 Пакет: {pack['coins']} COINS\n"
            f"💰 Сумма: {pack['price']} ₽\n\n"
            "⚠️ Проверь оплату вручную."
        )

        try:
            # ОТПРАВЛЯЕМ ЗАЯВКУ ТЕБЕ В ЛС
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_text,
                reply_markup=InlineKeyboardMarkup(admin_keyboard),
            )

            await query.message.reply_text(
                "💜 Заявка отправлена!\n\n"
                "Ожидай проверки оплаты."
            )

            context.user_data.pop("pack_id", None)

        except Exception as error:
            print(f"Ошибка отправки заявки: {error}")

            await query.message.reply_text(
                "❌ Ошибка отправки заявки.\n"
                "Попробуй ещё раз позже."
            )

        return

    # -------------------------
    # ПОДТВЕРЖДЕНИЕ ОПЛАТЫ
    # -------------------------

    if data.startswith("approve_"):
        if user.id != ADMIN_ID:
            await query.answer("Нет доступа.", show_alert=True)
            return

        _, user_id, pack_id = data.split("_")
        user_id = int(user_id)
        pack = PACKS.get(pack_id)

        if not pack:
            return

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "🎉 Оплата подтверждена!\n\n"
                    f"💎 Твой пакет: {pack['coins']} COINS\n\n"
                    "Спасибо за покупку 💜"
                ),
            )

            await query.edit_message_text(
                query.message.text + "\n\n✅ ОПЛАТА ПОДТВЕРЖДЕНА"
            )

        except Exception as error:
            print(f"Ошибка подтверждения: {error}")

        return

    # -------------------------
    # ОТКЛОНЕНИЕ
    # -------------------------

    if data.startswith("reject_"):
        if user.id != ADMIN_ID:
            await query.answer("Нет доступа.", show_alert=True)
            return

        _, user_id, pack_id = data.split("_")
        user_id = int(user_id)

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "❌ Заявка на оплату отклонена.\n\n"
                    "Если ты уже оплатил(а), свяжись с поддержкой."
                ),
            )

            await query.edit_message_text(
                query.message.text + "\n\n❌ ЗАЯВКА ОТКЛОНЕНА"
            )

        except Exception as error:
            print(f"Ошибка отклонения: {error}")

        return

    # -------------------------
    # ОТМЕНА
    # -------------------------

    if data == "cancel":
        context.user_data.pop("pack_id", None)

        await query.message.reply_text("❌ Покупка отменена.")
        return


# =========================
# ЗАПУСК
# =========================

def main():
    if not TOKEN:
        raise ValueError(
            "BOT_TOKEN не найден. Добавь его в Railway → Variables."
        )

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("💜 NEXI CASES BOT ЗАПУЩЕН")

    app.run_polling()


if __name__ == "__main__":
    main()
```
