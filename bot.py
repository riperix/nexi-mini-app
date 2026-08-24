import os
import sqlite3
from datetime import datetime

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

# Добавь в Railway Variables:
# ADMIN_ID = твой Telegram ID
# CARD_NUMBER = номер карты
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CARD_NUMBER = os.getenv("CARD_NUMBER", "")

DB_NAME = "nexi_bot.db"


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
# БАЗА ДАННЫХ
# =========================

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            coins INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            pack_id TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()


def save_user(user):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO users (user_id, username, full_name, coins)
        VALUES (?, ?, ?, 0)
        ON CONFLICT(user_id) DO UPDATE SET
            username = excluded.username,
            full_name = excluded.full_name
    """, (
        user.id,
        user.username or "",
        user.full_name or "",
    ))

    conn.commit()
    conn.close()


def get_balance(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT coins FROM users WHERE user_id = ?",
        (user_id,)
    )

    row = cursor.fetchone()
    conn.close()

    return row[0] if row else 0


def add_coins(user_id, coins):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users
        SET coins = coins + ?
        WHERE user_id = ?
    """, (coins, user_id))

    conn.commit()
    conn.close()


def create_order(user_id, pack_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO orders (
            user_id,
            pack_id,
            status,
            created_at
        )
        VALUES (?, ?, 'pending', ?)
    """, (
        user_id,
        pack_id,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ))

    order_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return order_id


def get_order(order_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT order_id, user_id, pack_id, status
        FROM orders
        WHERE order_id = ?
    """, (order_id,))

    order = cursor.fetchone()

    conn.close()

    return order


def get_latest_pending_order(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT order_id, user_id, pack_id, status
        FROM orders
        WHERE user_id = ?
        AND status = 'pending'
        ORDER BY order_id DESC
        LIMIT 1
    """, (user_id,))

    order = cursor.fetchone()

    conn.close()

    return order


def set_order_status(order_id, status):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE orders
        SET status = ?
        WHERE order_id = ?
        AND status = 'pending'
    """, (status, order_id))

    changed = cursor.rowcount

    conn.commit()
    conn.close()

    return changed > 0


# =========================
# ПРОВЕРКА АДМИНА
# =========================

def is_admin(user_id):
    return user_id == ADMIN_ID


# =========================
# /START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user)

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
        "💜 Добро пожаловать в NEXI CASES!\n\n"
        "Выбери пакет:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# =========================
# /BALANCE
# =========================

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user)

    coins = get_balance(user.id)

    await update.message.reply_text(
        f"💜 Твой баланс:\n\n"
        f"💎 {coins} NEXI COINS"
    )


# =========================
# /APPROVE USER_ID
# =========================

async def approve_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    user = update.effective_user

    if not is_admin(user.id):
        await update.message.reply_text("❌ Нет доступа.")
        return

    if not context.args:
        await update.message.reply_text(
            "❌ Использование:\n"
            "/approve ID_ПОЛЬЗОВАТЕЛЯ"
        )
        return

    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "❌ ID пользователя должен состоять из цифр."
        )
        return

    order = get_latest_pending_order(user_id)

    if not order:
        await update.message.reply_text(
            "❌ Активная заявка этого пользователя не найдена."
        )
        return

    order_id, _, pack_id, status = order
    pack = PACKS.get(pack_id)

    if not pack:
        await update.message.reply_text("❌ Пакет не найден.")
        return

    if not set_order_status(order_id, "approved"):
        await update.message.reply_text(
            "❌ Эта заявка уже была обработана."
        )
        return

    add_coins(user_id, pack["coins"])
    new_balance = get_balance(user_id)

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "🎉 ОПЛАТА ПОДТВЕРЖДЕНА!\n\n"
                f"💎 Начислено: {pack['coins']} NEXI COINS\n"
                f"💜 Твой баланс: {new_balance} NEXI COINS\n\n"
                "Спасибо за покупку 💜"
            ),
        )
    except Exception as error:
        print(f"Не удалось написать пользователю: {error}")

    await update.message.reply_text(
        "✅ Заявка подтверждена!\n\n"
        f"👤 Пользователь: {user_id}\n"
        f"💎 Начислено: {pack['coins']} COINS\n"
        f"💜 Новый баланс: {new_balance} COINS"
    )


# =========================
# /REJECT USER_ID
# =========================

async def reject_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    user = update.effective_user

    if not is_admin(user.id):
        await update.message.reply_text("❌ Нет доступа.")
        return

    if not context.args:
        await update.message.reply_text(
            "❌ Использование:\n"
            "/reject ID_ПОЛЬЗОВАТЕЛЯ"
        )
        return

    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "❌ ID пользователя должен состоять из цифр."
        )
        return

    order = get_latest_pending_order(user_id)

    if not order:
        await update.message.reply_text(
            "❌ Активная заявка этого пользователя не найдена."
        )
        return

    order_id, _, pack_id, status = order
    pack = PACKS.get(pack_id)

    if not set_order_status(order_id, "rejected"):
        await update.message.reply_text(
            "❌ Эта заявка уже была обработана."
        )
        return

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "❌ Заявка на оплату отклонена.\n\n"
                "Если ты уже оплатил(а), свяжись с поддержкой."
            ),
        )
    except Exception as error:
        print(f"Не удалось написать пользователю: {error}")

    await update.message.reply_text(
        "❌ Заявка отклонена."
    )


# =========================
# КНОПКИ
# =========================

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    user = query.from_user

    await query.answer()

    save_user(user)

    data = query.data


    # =========================
    # ВЫБОР ПАКЕТА
    # =========================

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

        payment_text = (
            f"💎 Вы выбрали: {pack['coins']} NEXI COINS\n"
            f"💰 К оплате: {pack['price']} ₽\n\n"
        )

        if CARD_NUMBER:
            payment_text += (
                f"💳 Номер карты:\n"
                f"`{CARD_NUMBER}`\n\n"
            )

        payment_text += (
            "После оплаты нажми кнопку "
            "«💳 Я ОПЛАТИЛ(А)»."
        )

        await query.message.reply_text(
            payment_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )
        return


    # =========================
    # Я ОПЛАТИЛ
    # =========================

    if data == "paid":
        pack_id = context.user_data.get("pack_id")
        pack = PACKS.get(pack_id)

        if not pack:
            await query.message.reply_text(
                "⚠️ Сначала выбери пакет через /start."
            )
            return

        order_id = create_order(
            user.id,
            pack_id
        )

        username = (
            f"@{user.username}"
            if user.username
            else "нет username"
        )

        admin_keyboard = [
            [
                InlineKeyboardButton(
                    "✅ ПОДТВЕРДИТЬ",
                    callback_data=f"approve_{order_id}",
                ),
                InlineKeyboardButton(
                    "❌ ОТКЛОНИТЬ",
                    callback_data=f"reject_{order_id}",
                ),
            ]
        ]

        admin_text = (
            "💳 НОВАЯ ЗАЯВКА НА ПРОВЕРКУ ОПЛАТЫ\n\n"
            f"👤 Имя: {user.full_name}\n"
            f"📱 Username: {username}\n"
            f"🆔 Telegram ID: {user.id}\n\n"
            f"💎 Пакет: {pack['coins']} NEXI COINS\n"
            f"💰 Сумма: {pack['price']} ₽\n\n"
            "⚠️ Пользователь нажал «Я ОПЛАТИЛ(А)».\n"
            "Проверь поступление денег.\n\n"
            f"Для команды:\n"
            f"/approve {user.id}\n"
            f"/reject {user.id}"
        )

        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_text,
                reply_markup=InlineKeyboardMarkup(
                    admin_keyboard
                ),
            )

            await query.message.reply_text(
                "💜 Заявка отправлена на проверку!\n\n"
                "Ожидай подтверждения оплаты."
            )

            context.user_data.pop(
                "pack_id",
                None
            )

        except Exception as error:
            print(
                f"Ошибка отправки заявки: {error}"
            )

            await query.message.reply_text(
                "❌ Не удалось отправить заявку.\n"
                "Попробуй ещё раз позже."
            )

        return


    # =========================
    # КНОПКА ПОДТВЕРДИТЬ
    # =========================

    if data.startswith("approve_"):
        if not is_admin(user.id):
            await query.answer(
                "❌ Нет доступа.",
                show_alert=True,
            )
            return

        try:
            order_id = int(
                data.replace("approve_", "")
            )
        except ValueError:
            return

        order = get_order(order_id)

        if not order:
            await query.answer(
                "❌ Заявка не найдена.",
                show_alert=True,
            )
            return

        _, user_id, pack_id, status = order
        pack = PACKS.get(pack_id)

        if not pack:
            return

        if status != "pending":
            await query.answer(
                "⚠️ Эта заявка уже обработана.",
                show_alert=True,
            )
            return

        if not set_order_status(
            order_id,
            "approved"
        ):
            return

        add_coins(
            user_id,
            pack["coins"]
        )

        new_balance = get_balance(user_id)

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "🎉 ОПЛАТА ПОДТВЕРЖДЕНА!\n\n"
                    f"💎 Начислено: {pack['coins']} NEXI COINS\n"
                    f"💜 Твой баланс: "
                    f"{new_balance} NEXI COINS\n\n"
                    "Спасибо за покупку 💜"
                ),
            )
        except Exception as error:
            print(
                f"Ошибка сообщения пользователю: {error}"
            )

        await query.edit_message_text(
            query.message.text
            + "\n\n"
            + "✅ ОПЛАТА ПОДТВЕРЖДЕНА\n"
            + f"💎 НАЧИСЛЕНО: "
            + f"{pack['coins']} COINS"
        )

        return


    # =========================
    # КНОПКА ОТКЛОНИТЬ
    # =========================

    if data.startswith("reject_"):
        if not is_admin(user.id):
            await query.answer(
                "❌ Нет доступа.",
                show_alert=True,
            )
            return

        try:
            order_id = int(
                data.replace("reject_", "")
            )
        except ValueError:
            return

        order = get_order(order_id)

        if not order:
            return

        _, user_id, pack_id, status = order

        if status != "pending":
            await query.answer(
                "⚠️ Эта заявка уже обработана.",
                show_alert=True,
            )
            return

        if not set_order_status(
            order_id,
            "rejected"
        ):
            return

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "❌ Заявка на оплату отклонена.\n\n"
                    "Если ты уже оплатил(а), "
                    "свяжись с поддержкой."
                ),
            )
        except Exception as error:
            print(
                f"Ошибка сообщения пользователю: {error}"
            )

        await query.edit_message_text(
            query.message.text
            + "\n\n"
            + "❌ ЗАЯВКА ОТКЛОНЕНА"
        )

        return


    # =========================
    # ОТМЕНА
    # =========================

    if data == "cancel":
        context.user_data.pop(
            "pack_id",
            None
        )

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
            "BOT_TOKEN не найден. "
            "Добавь его в Railway Variables."
        )

    if not ADMIN_ID:
        raise ValueError(
            "ADMIN_ID не найден. "
            "Добавь его в Railway Variables."
        )

    init_db()

    app = (
        ApplicationBuilder()
        .token(TOKEN)
        .build()
    )

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("balance", balance)
    )

    app.add_handler(
        CommandHandler(
            "approve",
            approve_command
        )
    )

    app.add_handler(
        CommandHandler(
            "reject",
            reject_command
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            button_handler
        )
    )

    print("💜 NEXI CASES BOT ЗАПУЩЕН")

    app.run_polling()


if __name__ == "__main__":
    main()
