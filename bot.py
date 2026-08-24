# bot.py

```python
import os
import json

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💜 NEXI CASES BOT работает.\n"
        "Заявки из Mini App принимаются."
    )


async def web_app_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    print("=== ПОЛУЧЕН WEB_APP_DATA ===")

    try:
        raw = update.effective_message.web_app_data.data
        print("ДАННЫЕ:", raw)

        data = json.loads(raw)

        if data.get("type") != "payment_request":
            print("НЕ ТОТ ТИП ДАННЫХ")
            return

        coins = int(data.get("coins", 0))
        price = int(data.get("price", 0))

        if PACKS.get(coins) != price:
            print("НЕВЕРНЫЙ ПАКЕТ:", coins, price)
            return

        user = update.effective_user

        username = (
            f"@{user.username}"
            if user.username
            else "нет username"
        )

        text = (
            "🚨 НОВАЯ ЗАЯВКА НА ОПЛАТУ\n\n"
            f"👤 Имя: {user.full_name}\n"
            f"🔗 Username: {username}\n"
            f"🆔 ID: {user.id}\n\n"
            f"💎 Пакет: {coins} COINS\n"
            f"💰 Сумма: {price} ₽\n\n"
            "⚠️ Пользователь нажал «Я ОПЛАТИЛ(А)»."
        )

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "✅ ПОДТВЕРДИТЬ",
                    callback_data=f"approve:{user.id}:{coins}"
                ),
                InlineKeyboardButton(
                    "❌ ОТКЛОНИТЬ",
                    callback_data=f"reject:{user.id}:{coins}"
                ),
            ]
        ])

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=text,
            reply_markup=keyboard,
        )

        print("=== ЗАЯВКА УСПЕШНО ОТПРАВЛЕНА АДМИНУ ===")

    except Exception as error:
        print("=== ОШИБКА WEB_APP_DATA ===")
        print(repr(error))


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
                f"💎 Тебе одобрен пакет: {coins} COINS\n\n"
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
                "Если произошла ошибка, обратись в поддержку."
            ),
        )

        await query.edit_message_text(
            query.message.text
            + "\n\n━━━━━━━━━━━━━━\n"
            + "❌ ЗАЯВКА ОТКЛОНЕНА"
        )


async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):
    print("=== ОШИБКА БОТА ===")
    print(repr(context.error))


def main():
    if not TOKEN:
        raise ValueError(
            "BOT_TOKEN не найден в Railway Variables"
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

    app.add_handler(
        MessageHandler(
            filters.StatusUpdate.WEB_APP_DATA,
            web_app_handler,
        )
    )

    app.add_handler(
        CallbackQueryHandler(button_handler)
    )

    app.add_error_handler(error_handler)

    print("=== NEXI BOT ЗАПУЩЕН ===")

    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=False,
    )


if __name__ == "__main__":
    main()
```
