```python
import os
import logging

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


# Заявки, которые ожидают проверки.
# Работает, пока бот не перезапускается.
PENDING_ORDERS = {}


# =========================
# ЛОГИ
# =========================

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


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
# /BALANCE
# =========================

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💎 Баланс COINS отображается в твоём NEXI CASES Mini App."
    )


# =========================
# /APPROVE ID
# =========================

async def approve_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Нет доступа.")
        return

    if not context.args:
        await update.message.reply_text(
            "Использование:\n/approve ID_ПОЛЬЗОВАТЕЛЯ"
        )
        return

    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "❌ ID должен состоять из цифр."
        )
        return

    order = PENDING_ORDERS.get(user_id)

    if not order:
        await update.message.reply_text(
            "❌ Активная заявка не найдена."
        )
        return

    pack = PACKS[order["pack_id"]]

    await context.bot.send_message(
        chat_id=user_id,
        text=(
            "🎉 ОПЛАТА ПОДТВЕРЖДЕНА!\n\n"
            f"💎 Тебе одобрено: {pack['coins']} COINS\n\n"
            "Открой NEXI CASES Mini App."
        ),
    )

    del PENDING_ORDERS[user_id]

    await update.message.reply_text(
        f"✅ Заявка пользователя {user_id} подтверждена.\n"
        f"💎 Одобрено: {pack['coins']} COINS"
    )


# =========================
# /REJECT ID
# =========================

async def reject_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Нет доступа.")
        return

    if not context.args:
        await update.message.reply_text(
            "Использование:\n/reject ID_ПОЛЬЗОВАТЕЛЯ"
        )
        return

    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "❌ ID должен состоять из цифр."
        )
        return

    if user_id not in PENDING_ORDERS:
        await update.message.reply_text(
            "❌ Активная заявка не найдена."
        )
        return

    await context.bot.send_message(
        chat_id=user_id,
        text=(
            "❌ Заявка на оплату отклонена.\n\n"
            "Если ты уже оплатил(а), свяжись с поддержкой."
        ),
    )

    del PENDING_ORDERS[user_id]

    await update.message.reply_text(
        "❌ Заявка отклонена."
    )


# =========================
# ВСЕ КНОПКИ
# =========================

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    user = query.from_user
    data = query.data

    await query.answer()


    # -------------------------
    # ВЫБОР ПАКЕТА
    # -------------------------

    if data.startswith("buy_"):
        pack_id = data.replace("buy_", "")
        pack = PACKS.get(pack_id)

        if not pack:
            await query.message.reply_text(
                "❌ Пакет не найден."
            )
            return

        context.user_data["pack_id"] = pack_id

        keyboard = [
            [
                InlineKeyboardButton(
                    "💳 Я ОПЛАТИЛ(А)",
                    callback_data="paid"
                )
            ],
            [
                InlineKeyboardButton(
                    "❌ Отмена",
                    callback_data="cancel"
                )
            ],
        ]

        await query.message.reply_text(
            f"💜 К оплате: {pack['price']} ₽\n"
            f"💎 Ты получишь: {pack['coins']} COINS\n\n"
            "Переведи деньги на карту, указанную в Mini App.\n\n"
            "После оплаты нажми «💳 Я ОПЛАТИЛ(А)».",
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

        # Сохраняем заявку
        PENDING_ORDERS[user.id] = {
            "pack_id": pack_id
        }

        username = (
            f"@{user.username}"
            if user.username
            else "нет username"
        )

        admin_text = (
            "💸 НОВАЯ ЗАЯВКА НА ОПЛАТУ\n\n"
            f"👤 Пользователь: {user.full_name}\n"
            f"📱 Username: {username}\n"
            f"🆔 Telegram ID: {user.id}\n\n"
            f"💎 Пакет: {pack['coins']} COINS\n"
            f"💰 Сумма: {pack['price']} ₽\n\n"
            "⚠️ Проверь поступление денег вручную."
        )

        # КНОПКИ АДМИНА
        admin_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "✅ ПОДТВЕРДИТЬ",
                    callback_data=f"approve_{user.id}"
                ),
                InlineKeyboardButton(
                    "❌ ОТКЛОНИТЬ",
                    callback_data=f"reject_{user.id}"
                ),
            ]
        ])

        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_text,
                reply_markup=admin_keyboard,
            )

            await query.message.reply_text(
                "💜 Заявка отправлена!\n\n"
                "Ожидай проверки оплаты."
            )

            context.user_data.pop("pack_id", None)

        except Exception as error:
            logging.exception(
                f"Ошибка отправки заявки: {error}"
            )

            await query.message.reply_text(
                "❌ Не удалось отправить заявку."
            )

        return


    # -------------------------
    # КНОПКА ПОДТВЕРДИТЬ
    # -------------------------

    if data.startswith("approve_"):
        if user.id != ADMIN_ID:
            await query.answer(
                "❌ Нет доступа.",
                show_alert=True
            )
            return

        user_id = int(
            data.replace("approve_", "")
        )

        order = PENDING_ORDERS.get(user_id)

        if not order:
            await query.answer(
                "❌ Заявка уже обработана.",
                show_alert=True
            )
            return

        pack = PACKS[order["pack_id"]]

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "🎉 ОПЛАТА ПОДТВЕРЖДЕНА!\n\n"
                    f"💎 Одобрено: {pack['coins']} COINS\n\n"
                    "Открой NEXI CASES Mini App."
                ),
            )

            del PENDING_ORDERS[user_id]

            await query.edit_message_text(
                query.message.text
                + "\n\n"
                + "━━━━━━━━━━━━━━\n"
                + "✅ ОПЛАТА ПОДТВЕРЖДЕНА\n"
                + f"💎 ОДОБРЕНО: {pack['coins']} COINS"
            )

        except Exception as error:
            logging.exception(
                f"Ошибка подтверждения: {error}"
            )

        return


    # -------------------------
    # КНОПКА ОТКЛОНИТЬ
    # -------------------------

    if data.startswith("reject_"):
        if user.id != ADMIN_ID:
            await query.answer(
                "❌ Нет доступа.",
                show_alert=True
            )
            return

        user_id = int(
            data.replace("reject_", "")
        )

        if user_id not in PENDING_ORDERS:
            await query.answer(
                "❌ Заявка уже обработана.",
                show_alert=True
            )
            return

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "❌ Заявка на оплату отклонена."
                ),
            )

            del PENDING_ORDERS[user_id]

            await query.edit_message_text(
                query.message.text
                + "\n\n"
                + "━━━━━━━━━━━━━━\n"
                + "❌ ЗАЯВКА ОТКЛОНЕНА"
            )

        except Exception as error:
            logging.exception(
                f"Ошибка отклонения: {error}"
            )

        return


    # -------------------------
    # ОТМЕНА
    # -------------------------

    if data == "cancel":
        context.user_data.pop("pack_id", None)

        await query.message.reply_text(
            "❌ Покупка отменена."
        )

        return


# =========================
# ЗАПУСК
# =========================

def main():
    if not TOKEN:
        raise ValueError(
            "BOT_TOKEN не найден."
        )

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("balance", balance)
    )

    app.add_handler(
        CommandHandler("approve", approve_command)
    )

    app.add_handler(
        CommandHandler("reject", reject_command)
    )

    app.add_handler(
        CallbackQueryHandler(button_handler)
    )

    print("💜 NEXI CASES BOT ЗАПУЩЕН")

    app.run_polling()


if __name__ == "__main__":
    main()
```
