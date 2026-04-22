from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import CallbackContext, CommandHandler, CallbackQueryHandler, MessageHandler, Filters
import sqlite3
import datetime

# ================= DB =================

db = sqlite3.connect("tmo.db", check_same_thread=False)
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS jobdast(
    group_id INTEGER PRIMARY KEY,
    host TEXT DEFAULT '',
    backup TEXT DEFAULT '',
    keliling TEXT DEFAULT '',
    tagall TEXT DEFAULT '',
    gcast TEXT DEFAULT '',
    link TEXT DEFAULT ''
)
""")
db.commit()

panel_msg = {}
user_state = {}

FIELDS_USER = {"host", "backup", "keliling"}
FIELDS_TEXT = {"tagall", "gcast", "link"}
ALL_FIELDS = FIELDS_USER | FIELDS_TEXT


# ================= INIT =================

def init_group(gid):
    cur.execute("INSERT OR IGNORE INTO jobdast(group_id) VALUES(?)", (gid,))
    db.commit()


# ================= SAFE GET =================

def get_data(gid):
    init_group(gid)
    cur.execute("""
        SELECT host,backup,keliling,tagall,gcast,link
        FROM jobdast WHERE group_id=?
    """, (gid,))
    return cur.fetchone() or ("", "", "", "", "", "")


def get_field(gid, f):
    cur.execute(f"SELECT {f} FROM jobdast WHERE group_id=?", (gid,))
    r = cur.fetchone()
    return r[0] if r and r[0] is not None else ""


# ================= FORMAT =================

def nice_date():
    return datetime.datetime.now().strftime("%d/%m/%Y")


def format_text(x):
    if not x:
        return "➖ Kosong"
    return "\n".join([f"• {i}" for i in x.split("\n") if i.strip()])


def format_user(x):
    if not x:
        return "➖ Kosong"
    out = []
    for v in x.split("\n"):
        try:
            uid, name = v.split("|", 1)
            out.append(f"👤 {name}")
        except:
            continue
    return "\n".join(out) if out else "➖ Kosong"


# ================= PANEL =================

def build_panel(gid):
    h,b,k,t,g,l = get_data(gid)

    return f"""
╔══════════════════════╗
        ⚡ JOBDAST ⚡
╚══════════════════════╝
📅 {nice_date()}

👑 HOST
{format_user(h)}

🛡 BACKUP
{format_user(b)}

🚶 KELILING
{format_user(k)}

📣 TAGALL
{format_text(t)}

📡 GCAST
{format_text(g)}

🔗 LINK
{format_text(l)}

━━━━━━━━━━━━━━━━━━━━━━
🛍 @storegarf
"""


# ================= BUTTON =================

def panel_btn():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👑 HOST", callback_data="jd:host"),
            InlineKeyboardButton("🗑", callback_data="jd:del_host")
        ],
        [
            InlineKeyboardButton("🛡 BACKUP", callback_data="jd:backup"),
            InlineKeyboardButton("🗑", callback_data="jd:del_backup")
        ],
        [
            InlineKeyboardButton("🚶 KELILING", callback_data="jd:keliling"),
            InlineKeyboardButton("🗑", callback_data="jd:del_keliling")
        ],
        [
            InlineKeyboardButton("📣 TAGALL", callback_data="jd:tagall"),
            InlineKeyboardButton("📡 GCAST", callback_data="jd:gcast")
        ],
        [
            InlineKeyboardButton("🔗 LINK", callback_data="jd:link")
        ],
        [
            InlineKeyboardButton("📋 COPY", callback_data="jd:copy"),
            InlineKeyboardButton("♻ RESET", callback_data="jd:reset")
        ]
    ])


# ================= COMMAND =================

def getjobdast_cmd(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    init_group(chat_id)

    msg = update.message.reply_text(
        build_panel(chat_id),
        reply_markup=panel_btn()
    )

    panel_msg[chat_id] = msg.message_id


# ================= CALLBACK =================

def jobdast_cb(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    chat_id = query.message.chat.id
    user_id = query.from_user.id
    data = query.data.replace("jd:", "")

    # ===== ADD USER =====
    if data in FIELDS_USER:
        old = get_field(chat_id, data) or ""
        new = old + f"\n{user_id}|{query.from_user.first_name}"

        cur.execute(f"UPDATE jobdast SET {data}=? WHERE group_id=?", (new, chat_id))
        db.commit()

        return query.edit_message_text(build_panel(chat_id), reply_markup=panel_btn())


    # ===== TEXT MODE =====
    if data in FIELDS_TEXT:
        user_state[user_id] = (chat_id, data)
        return query.message.reply_text("✍️ Kirim teks sekarang...")


    # ===== DELETE =====
    if data.startswith("del_"):
        field = data.replace("del_", "")
        if field in ALL_FIELDS:
            cur.execute(f"UPDATE jobdast SET {field}='' WHERE group_id=?", (chat_id,))
            db.commit()

        return query.edit_message_text(build_panel(chat_id), reply_markup=panel_btn())


    # ===== RESET =====
    if data == "reset":
        cur.execute("""
            UPDATE jobdast SET host='',backup='',keliling='',
            tagall='',gcast='',link=''
            WHERE group_id=?
        """, (chat_id,))
        db.commit()

        return query.edit_message_text(build_panel(chat_id), reply_markup=panel_btn())


    # ===== COPY =====
    if data == "copy":
        return query.message.reply_text("📋 COPY PANEL\n\n" + build_panel(chat_id))


# ================= TEXT HANDLER (FIX AUTOTAGALL SAFE) =================

def text_handler(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if user_id not in user_state:
        return

    state_chat, field = user_state[user_id]

    # ❗ FIX PENTING: jangan campur group lain
    if chat_id != state_chat:
        return

    text = update.message.text

    old = get_field(chat_id, field) or ""
    new = old + "\n" + text

    cur.execute(f"UPDATE jobdast SET {field}=? WHERE group_id=?", (new, chat_id))
    db.commit()

    user_state.pop(user_id, None)

    update.message.reply_text("✅ BERHASIL DISIMPAN")

    # refresh panel
    if chat_id in panel_msg:
        try:
            context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=panel_msg[chat_id],
                text=build_panel(chat_id),
                reply_markup=panel_btn()
            )
        except:
            pass


# ================= REGISTER =================

def register_jobdast(dp):
    dp.add_handler(CommandHandler("getjobdast", getjobdast_cmd))
    dp.add_handler(CallbackQueryHandler(jobdast_cb, pattern="^jd:"))
    dp.add_handler(MessageHandler(Filters.text & Filters.group, text_handler))
