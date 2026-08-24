# bot.py

```python
import os
import json
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 1282434336


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💜 Добро пожаловать в NEXI CASES!\n\n"
        "Выберите кейс в Mini App и оформите заявку на покупку."
    )


async def receive_webapp_data(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    try:
        raw_data = update.effective_message.web_app_data.data
        user = update.effective_user

        try:
            data = json.loads(raw_data)
        except json.JSONDecodeError:
            data = {"package": raw_data}

        package = data.get("package", "Не указан")
        price = data.get("price", "Не указана")
        payment_method = data.get("payment_method", "Карта / СБП")

        username = f"@{user.username}" if user.username else "Нет username"
        name = user.first_name or "Не указано"

        now = datetime.now().strftime("%d.%m.%Y %H:%M")
        order_id = f"{user.id}_{int(datetime.now().timestamp())}"

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "✅ Подтвердить",
                    callback_data=f"approve:{user.id}:{order_id}"
                ),
                InlineKeyboardButton(
                    "❌ Отклонить",
                    callback_data=f"reject:{user.id}:{order_id}"
                ),
            ]
        ])

        admin_text = (
            "💜 НОВАЯ ЗАЯВКА НА ОПЛАТУ\n\n"
            f"📦 Пакет: {package}\n"
            f"💰 Сумма: {price}\n"
            f"💳 Оплата: {payment_method}\n\n"
            f"👤 Имя: {name}\n"
            f"🔗 Username: {username}\n"
            f"🆔 Telegram ID: {user.id}\n\n"
            f"🕐 Время: {now}\n"
            f"📋 Заявка: {order_id}\n\n"
            "⚠️ Проверь оплату вручную перед подтверждением."
        )

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_text,
            reply_markup=keyboard
        )

        await update.effective_message.reply_text(
            "💜 Заявка отправлена!\n\n"
            "Мы проверим оплату и подтвердим покупку."
        )

        print(f"Заявка отправлена: {order_id}")

    except Exception as e:
        print(f"ОШИБКА: {e}")

        await update.effective_message.reply_text(
            "❌ Не удалось отправить заявку. Попробуйте ещё раз."
        )


async def handle_admin_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.answer(
            "У вас нет доступа.",
            show_alert=True
        )
        return

    try:
        action, user_id, order_id = query.data.split(":")
        user_id = int(user_id)

        if action == "approve":
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "✅ Оплата подтверждена!\n\n"
                    "Спасибо за покупку 💜"
                )
            )

            await query.edit_message_text(
                query.message.text + "\n\n✅ ЗАЯВКА ПОДТВЕРЖДЕНА"
            )

        elif action == "reject":
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "❌ Заявка отклонена.\n\n"
                    "Если вы уже оплатили, свяжитесь с поддержкой."
                )
            )

            await query.edit_message_text(
                query.message.text + "\n\n❌ ЗАЯВКА ОТКЛОНЕНА"
            )

    except Exception as e:
        print(f"ОШИБКА ОБРАБОТКИ: {e}")


def main():
    if not BOT_TOKEN:
        raise ValueError(
            "BOT_TOKEN не найден. Проверь Variables в Railway."
        )

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(
        MessageHandler(
            filters.StatusUpdate.WEB_APP_DATA,
            receive_webapp_data
        )
    )

    app.add_handler(
        CallbackQueryHandler(handle_admin_callback)
    )

    print("NEXI CASES BOT запущен")

    app.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()
```
