import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

TOKEN = os.getenv("BOT_TOKEN")

# СЮДА ПОТОМ ВСТАВИМ ТВОЙ TELEGRAM ID
ADMIN_ID = 1282434336

PACKS = {
    "100": {"coins": 100, "price": 20},
    "250": {"coins": 250, "price": 50},
    "600": {"coins": 600, "price": 100},
    "1500": {"coins": 1500, "price": 200},
    "3000": {"coins": 3000, "price": 350},
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton(
                "💎 100 COINS — 20 ₽",
                callback_data="buy_100"
            )
        ],
        [
            InlineKeyboardButton(
                "💎 250 COINS — 50 ₽",
                callback_data="buy_250"
            )
        ],
        [
            InlineKeyboardButton(
                "💎 600 COINS — 100 ₽",
                callback_data="buy_600"
            )
        ],
        [
            InlineKeyboardButton(
                "💎 1500 COINS — 200 ₽",
                callback_data="buy_1500"
            )
        ],
        [
            InlineKeyboardButton(
                "💎 3000 COINS — 350 ₽",
                callback_data="buy_3000"
            )
        ],
    ]

    await update.message.reply_text(
        "💜 Добро пожаловать в NEXI CASE!\n\n"
        "Выбери пакет NEXI Coins:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data.startswith("buy_"):
        pack_id = data.replace("buy_", "")
        pack = PACKS.get(pack_id)

        if not pack:
            await query.message.reply_text("Ошибка. Попробуй ещё раз.")
            return

        context.user_data["pack_id"] = pack_id

        keyboard = [
            [
                InlineKeyboardButton(
                    "💳 Я оплатил",
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
            "После оплаты нажми кнопку «Я оплатил». "
            "Заявка придёт администратору на подтверждение.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "paid":
        pack_id = context.user_data.get("pack_id")

        if not pack_id:
            await query.message.reply_text(
                "Сначала выбери пакет через /start"
            )
            return

        pack = PACKS.get(pack_id)
        user = query.from_user

        admin_text = (
            "💸 НОВАЯ ЗАЯВКА НА ОПЛАТУ\n\n"
            f"👤 Пользователь: {user.full_name}\n"
            f"🆔 Telegram ID: {user.id}\n"
            f"💎 Пакет: {pack['coins']} COINS\n"
            f"💰 Сумма: {pack['price']} ₽\n\n"
            "⚠️ Проверь поступление денег вручную."
        )

        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_text
            )

            await query.message.reply_text(
                "💜 Заявка отправлена!\n\n"
                "Я проверю оплату и подтвержу покупку."
            )

        except Exception as error:
            print(error)

            await query.message.reply_text(
                "⚠️ Не удалось отправить заявку администратору.\n"
                "Попробуй позже."
            )

    elif data == "cancel":
        await query.message.reply_text("❌ Покупка отменена.")


def main():
    if not TOKEN:
        raise ValueError(
            "BOT_TOKEN не найден. "
            "Добавь его в Railway Variables."
        )

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CallbackQueryHandler(button_handler)
    )

    print("NEXI bot запущен")

    app.run_polling()


if __name__ == "__main__":
    main()
