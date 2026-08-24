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
# ЛОГИ
# =========================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# =========================
# НАСТРОЙКИ
# =========================

TOKEN = os.getenv("BOT_TOKEN")

# В Railway -> Variables добавь свой Telegram ID
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# В Railway -> Variables добавь номер карты
CARD_NUMBER = os.getenv("CARD_NUMBER", "")

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
# КЛАВИАТУРА ПАКЕТОВ
# =========================

def packs_keyboard():
    keyboard = [
        [InlineKeyboardButton("💎 100 COINS — 20 ₽", callback_data="buy_100")],
        [InlineKeyboardButton("💎 250 COINS — 50 ₽", callback_data="buy_250")],
        [InlineKeyboardButton("💎 600 COINS — 100 ₽", callback_data="buy_600")],
        [InlineKeyboardButton("💎 1500 COINS — 200 ₽", callback_data="buy_1500")],
        [InlineKeyboardButton("💎 3000 COINS — 350 ₽", callback_data="buy_3000")],
    ]

    return InlineKeyboardMarkup(keyboard)


# =========================
# /START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💜 Добро пожаловать в NEXI CASES!\n\n"
        "Выбери пакет:",
        reply_markup=packs_keyboard(),
    )


# =========================
# ОБРАБОТЧИК КНОПОК
# =========================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if not query:
        return

    await query.answer()

    data = query.data
    user = query.from_user

    # =========================
    # ВЫБОР ПАКЕТА
    # =========================

    if data.startswith("buy_"):
        pack_id = data.replace("buy_", "", 1)
        pack = PACKS.get(pack_id)

        if not pack:
            await query.message.reply_text(
                "❌ Пакет не найден. Попробуй ещё раз."
            )
            return

        context.user_data["pack_id"] = pack_id

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "💳 Я ОПЛАТИЛ",
                    callback_data="paid"
                )
            ],
            [
                InlineKeyboardButton(
                    "❌ Отмена",
                    callback_data="cancel"
                )
            ],
        ])

        card_text = CARD_NUMBER if CARD_NUMBER else "Номер карты не указан"

        await query.message.reply_text(
            f"💎 Вы выбрали: {pack['coins']} NEXI COINS\n"
            f"💰 К оплате: {pack['price']} ₽\n\n"
            f"💳 Номер карты:\n"
            f"`{card_text}`\n\n"
            "После оплаты нажми кнопку «💳 Я ОПЛАТИЛ».",
            reply_markup=keyboard,
            parse_mode="Markdown",
        )

        return

    # =========================
    # ПОЛЬЗОВАТЕЛЬ НАЖАЛ Я ОПЛАТИЛ
    # =========================

    if data == "paid":

        pack_id = context.user_data.get("pack_id")
        pack = PACKS.get(pack_id)

        if not pack:
            await query.message.reply_text(
                "⚠️ Сначала выбери пакет через /start."
            )
            return

        if ADMIN_ID == 0:
            await query.message.reply_text(
                "❌ Ошибка настройки бота. ADMIN_ID не указан."
            )
            return

        username = (
            f"@{user.username}"
            if user.username
            else "нет username"
        )

        # КНОПКИ ДЛЯ АДМИНА
        admin_keyboard = InlineKeyboardMarkup([
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
        ])

        admin_text = (
            "💳 НОВАЯ ЗАЯВКА НА ПРОВЕРКУ ОПЛАТЫ\n\n"
            f"👤 Имя: {user.full_name}\n"
            f"📱 Username: {username}\n"
            f"🆔 Telegram ID: {user.id}\n\n"
            f"💎 Пакет: {pack['coins']} NEXI COINS\n"
            f"💰 Сумма: {pack['price']} ₽\n\n"
            "⚠️ Пользователь нажал «Я ОПЛАТИЛ(А)».\n"
            "Проверь оплату и выбери действие ниже."
        )

        try:
            # ОТПРАВЛЯЕМ ЗАЯВКУ АДМИНУ
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_text,
                reply_markup=admin_keyboard,
            )

            await query.message.reply_text(
                "💜 Заявка отправлена на проверку!\n\n"
                "Ожидай подтверждения оплаты."
            )

            # Удаляем выбранный пакет,
            # чтобы следующая покупка начиналась заново
            context.user_data.pop("pack_id", None)

        except Exception as error:
            logging.exception(
                f"Ошибка отправки заявки администратору: {error}"
            )

            await query.message.reply_text(
                "❌ Не удалось отправить заявку на проверку.\n"
                "Попробуй ещё раз немного позже."
            )

        return

    # =========================
    # АДМИН ПОДТВЕРЖДАЕТ
    # =========================

    if data.startswith("approve_"):

        if user.id != ADMIN_ID:
            await query.answer(
                "❌ У тебя нет доступа.",
                show_alert=True
            )
            return

        try:
            _, user_id, pack_id = data.split("_", 2)

            user_id = int(user_id)
            pack = PACKS.get(pack_id)

            if not pack:
                await query.answer(
                    "❌ Пакет не найден.",
                    show_alert=True
                )
                return

            # ПИШЕМ ПОКУПАТЕЛЮ
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "🎉 ОПЛАТА ПОДТВЕРЖДЕНА!\n\n"
                    f"💎 Твой пакет: {pack['coins']} NEXI COINS\n\n"
                    "Спасибо за покупку 💜"
                ),
            )

            # УБИРАЕМ КНОПКИ И ОТМЕЧАЕМ ЗАЯВКУ
            await query.edit_message_text(
                text=(
                    query.message.text
                    + "\n\n"
                    + "━━━━━━━━━━━━━━━━━━\n"
                    + "✅ ОПЛАТА ПОДТВЕРЖДЕНА"
                ),
            )

            await query.answer("Оплата подтверждена!")

        except Exception as error:
            logging.exception(
                f"Ошибка подтверждения оплаты: {error}"
            )

            await query.answer(
                "❌ Произошла ошибка.",
                show_alert=True
            )

        return

    # =========================
    # АДМИН ОТКЛОНЯЕТ
    # =========================

    if data.startswith("reject_"):

        if user.id != ADMIN_ID:
            await query.answer(
                "❌ У тебя нет доступа.",
                show_alert=True
            )
            return

        try:
            _, user_id, pack_id = data.split("_", 2)

            user_id = int(user_id)

            # ПИШЕМ ПОКУПАТЕЛЮ
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "❌ Заявка на оплату отклонена.\n\n"
                    "Если ты уже оплатил(а), попробуй связаться с поддержкой."
                ),
            )

            # УБИРАЕМ КНОПКИ И ОТМЕЧАЕМ ЗАЯВКУ
            await query.edit_message_text(
                text=(
                    query.message.text
                    + "\n\n"
                    + "━━━━━━━━━━━━━━━━━━\n"
                    + "❌ ЗАЯВКА ОТКЛОНЕНА"
                ),
            )

            await query.answer("Заявка отклонена.")

        except Exception as error:
            logging.exception(
                f"Ошибка отклонения заявки: {error}"
            )

            await query.answer(
                "❌ Произошла ошибка.",
                show_alert=True
            )

        return

    # =========================
    # ОТМЕНА
    # =========================

    if data == "cancel":

        context.user_data.pop("pack_id", None)

        await query.message.reply_text(
            "❌ Покупка отменена.\n\n"
            "Чтобы выбрать новый пакет, нажми /start."
        )

        return


# =========================
# ЗАПУСК БОТА
# =========================

def main():

    if not TOKEN:
        raise ValueError(
            "BOT_TOKEN не найден. Добавь его в Railway → Variables."
        )

    if ADMIN_ID == 0:
        raise ValueError(
            "ADMIN_ID не найден. Добавь его в Railway → Variables."
        )

    if not CARD_NUMBER:
        raise ValueError(
            "CARD_NUMBER не найден. Добавь его в Railway → Variables."
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

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("💜 NEXI CASES BOT ЗАПУЩЕН")

    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
