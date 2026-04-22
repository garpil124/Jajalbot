# ================= ABSEN BOT SYSTEM (STABLE SAFE VERSION) =================

from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, filters
from datetime import datetime
import pytz
import sqlite3

WIB = pytz.timezone("Asia/Jakarta")

# ================= DB =================

db = sqlite3.connect("absen.db", check_same_thread=False)
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS absen (
    chat_id INTEGER,
    user_id INTEGER,
    name TEXT,
    type TEXT,
    alasan TEXT,
    date TEXT
)
""")
db.commit()

absen_msg = {}
pending_izin = {}

last_day = None
last_week = None


# ================= SAVE =================

def save_absen(chat_id, user_id, name, tipe, alasan=None):
    cur.execute("""
        INSERT INTO absen (chat_id, user_id, name, type, alasan, date)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (chat_id, user_id, name, tipe, alasan, datetime.now(WIB).strftime("%Y-%m-%d")))
    db.commit()


# ================= LOAD =================

def load_absen(chat_id):
    cur.execute("SELECT name, type, alasan FROM absen WHERE chat_id=?", (chat_id,))
    rows = cur.fetchall()

    data = {"hadir": [], "izin": [], "sakit": []}

    for name, tipe, alasan in rows:
        if tipe == "hadir":
            data["hadir"].append(name)
        elif tipe == "sakit":
            data["sakit"].append(name)
        elif tipe == "izin":
            data["izin"].append((name, alasan))

    return data


# ================= UI =================

def format_absen(chat_id):
    data = load_absen(chat_id)
    now = datetime.now(WIB)

    total = len(data["hadir"]) + len(data["izin"]) + len(data["sakit"])

    text = f"""
╔════════════════════════════════╗
        ✦ ATTENDANCE REPORT ✦
╚════════════════════════════════╝

📅 {now.strftime('%A, %d %B %Y')}
────────────────────────────────
📊 STATUS SUMMARY

🟢 HADIR   ▰▰▰ {len(data['hadir'])}
🟡 IZIN    ▰ {len(data['izin'])}
🔴 SAKIT   ▰ {len(data['sakit'])}

👥 TOTAL : {total}
────────────────────────────────
🏷 PARTICIPANT LOG
"""

    for n in data["hadir"]:
        text += f"\n➤ 🟢 {n}"

    for n, a in data["izin"]:
        text += f"\n➤ 🟡 {n}\n   └ {a}"

    for n in data["sakit"]:
        text += f"\n➤ 🔴 {n}"

    if total == 0:
        text += "\nBelum ada absensi."

    text += "\n────────────────────────────────\n⚡ ACTIVE SYSTEM"
    return text


# ================= BUTTON =================

def get_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🟢 HADIR", callback_data="absen_hadir"),
            InlineKeyboardButton("🟡 IZIN", callback_data="absen_izin"),
            InlineKeyboardButton("🔴 SAKIT", callback_data="absen_sakit"),
        ],
        [
            InlineKeyboardButton("🛍 STORE", url="https://t.me/storegarf")
        ]
    ])


# ================= SAFE RESET (NO BLOCK) =================

def daily_reset(context):
    global last_day

    now = datetime.now(WIB).strftime("%Y-%m-%d")

    if last_day == now:
        return

    chats = cur.execute("SELECT DISTINCT chat_id FROM absen").fetchall()

    for (chat_id,) in chats:
        try:
            context.bot.send_message(
                chat_id,
                "📊 REKAP HARI KEMARIN\n\n" + format_absen(chat_id)
            )
        except:
            pass

    cur.execute("DELETE FROM absen")
    db.commit()

    last_day = now


# ================= COMMAND =================

def absen_cmd(update, context):
    daily_reset(context)

    chat_id = update.effective_chat.id

    try:
        if chat_id in absen_msg:
            context.bot.unpin_chat_message(chat_id, absen_msg[chat_id])
    except:
        pass

    msg = update.message.reply_text(
        format_absen(chat_id),
        reply_markup=get_keyboard()
    )

    absen_msg[chat_id] = msg.message_id

    try:
        context.bot.pin_chat_message(chat_id, msg.message_id, disable_notification=True)
    except:
        pass


# ================= BUTTON HANDLER (SAFE FIX) =================

def absen_button(update, context):
    daily_reset(context)

    query = update.callback_query
    query.answer()

    user = query.from_user
    chat_id = query.message.chat.id

    data = query.data.split("_")[1]

    cur.execute(
        "SELECT 1 FROM absen WHERE chat_id=? AND user_id=?",
        (chat_id, user.id)
    )

    if cur.fetchone():
        return query.answer("❌ Sudah absen", show_alert=True)

    if data == "hadir":
        save_absen(chat_id, user.id, user.first_name, "hadir")

    elif data == "sakit":
        save_absen(chat_id, user.id, user.first_name, "sakit")

    elif data == "izin":
        pending_izin[user.id] = chat_id
        return query.message.reply_text("🟡 Kirim alasan izin:")

    try:
        context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=absen_msg.get(chat_id),
            text=format_absen(chat_id),
            reply_markup=get_keyboard()
        )
    except:
        pass


# ================= IZIN HANDLER (FIXED SCOPE) =================

def izin_handler(update, context):
    user = update.effective_user
    chat_id = update.effective_chat.id

    if user.id not in pending_izin:
        return

    if pending_izin[user.id] != chat_id:
        return

    save_absen(chat_id, user.id, user.first_name, "izin", update.message.text)

    del pending_izin[user.id]


# ================= REGISTER (SAFE NON-BLOCKING) =================

def register_absen(app):
    app.add_handler(CommandHandler("absen", absen_cmd))

    # ONLY callback pattern, tidak ganggu handler lain
    app.add_handler(CallbackQueryHandler(absen_button, pattern="^absen_"))

    # FIX: jangan global semua text (ini yang bikin bot "diem")
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, izin_handler))
