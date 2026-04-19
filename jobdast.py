from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler, Filters
import sqlite3, datetime

db = sqlite3.connect("tmo.db", check_same_thread=False)
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS jobdast(
    group_id INTEGER PRIMARY KEY,
    host TEXT,
    backup TEXT,
    keliling TEXT,
    tagall TEXT,
    gcast TEXT,
    link TEXT
)
""")
db.commit()

user_state = {}
last_input = {}

FIELDS_USER = ["host", "backup", "keliling"]
FIELDS_TEXT = ["tagall", "gcast", "link"]
ALL_FIELDS = FIELDS_USER + FIELDS_TEXT


# ================= INIT =================
def init_group(gid):
    cur.execute("INSERT OR IGNORE INTO jobdast(group_id) VALUES(?)", (gid,))
    db.commit()


def safe(x):
    return x or ""


# ================= DATA =================
def get_data(gid):
    init_group(gid)
    cur.execute("""
        SELECT host,backup,keliling,tagall,gcast,link
        FROM jobdast WHERE group_id=?
    """, (gid,))
    return cur.fetchone() or ("", "", "", "", "", "")


def get_field(gid, f):
    if f not in ALL_FIELDS:
        return ""
    cur.execute(f"SELECT {f} FROM jobdast WHERE group_id=?", (gid,))
    r = cur.fetchone()
    return safe(r[0]) if r else ""


# ================= FORMAT =================
def format_user(x):
    if not x:
        return "-"

    out = []
    for v in x.split("\n"):
        if not v.strip():
            continue
        try:
            uid, name = v.split("|", 1)
            out.append(f"• [{name}](tg://user?id={uid})")
        except:
            out.append(f"• {v}")

    return "\n".join(out)


def format_text(x):
    if not x:
        return "-"
    return "\n".join([i for i in x.split("\n") if i.strip()])


def nice_date():
    return datetime.datetime.now().strftime("%d/%m/%Y")


# ================= PANEL =================
def build_text(gid):
    h,b,k,t,g,l = get_data(gid)

    return f"""✦ 𝗝𝗢𝗕𝗗𝗘𝗞𝗦 𝗧𝗠𝗢 ✦
🗓️ {nice_date()}
━━━━━━━━━━━━━━━━

◆ HOST 🎙️ :
{format_user(h)}

◆ BACKUP 🎧 :
{format_user(b)}

◆ KELILING 📝 :
{format_user(k)}

◆ TAGALL 🧾 :
{format_text(t)}

◆ GCAST 📂 :
{format_text(g)}

◆ LINK 📌 :
{format_text(l)}

━━━━━━━━━━━━━━━━
🛍️ @storegarf
"""


def keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("HOST 🎙️", callback_data="job_host"),
         InlineKeyboardButton("DEL", callback_data="job_reset_host")],

        [InlineKeyboardButton("BACKUP ⚙️", callback_data="job_backup"),
         InlineKeyboardButton("DEL", callback_data="job_reset_backup")],

        [InlineKeyboardButton("KELILING 🧾", callback_data="job_keliling"),
         InlineKeyboardButton("DEL", callback_data="job_reset_keliling")],

        [InlineKeyboardButton("TAGALL 📂", callback_data="job_tagall"),
         InlineKeyboardButton("VIEW 👁️", callback_data="job_view_tagall"),
         InlineKeyboardButton("DEL 🧹", callback_data="job_reset_tagall")],

        [InlineKeyboardButton("GCAST 📨", callback_data="job_gcast"),
         InlineKeyboardButton("VIEW 👁️", callback_data="job_view_gcast"),
         InlineKeyboardButton("DEL 🧹", callback_data="job_reset_gcast")],

        [InlineKeyboardButton("LINK 📌", callback_data="job_link"),
         InlineKeyboardButton("VIEW 👁️", callback_data="job_view_link"),
         InlineKeyboardButton("DEL 🧹", callback_data="job_reset_link")],

        [InlineKeyboardButton("COPY ALL 💻", callback_data="job_copy")],
        [InlineKeyboardButton("RESET ALL 🚨", callback_data="job_reset_all")]
    ])


# ================= COMMAND =================
def job_cmd(update, context):
    gid = update.effective_chat.id
    init_group(gid)

    update.message.reply_text(
        build_text(gid),
        reply_markup=keyboard(),
        parse_mode="Markdown"
    )


# ================= BUTTON =================
def job_button(update, context):
    query = update.callback_query
    query.answer()

    gid = query.message.chat.id
    uid = query.from_user.id
    name = query.from_user.first_name

    data = query.data.replace("job_", "")

    if data in FIELDS_USER:
        old = get_field(gid, data)
        new = f"{uid}|{name}" if not old else old + "\n" + f"{uid}|{name}"

        cur.execute(f"UPDATE jobdast SET {data}=? WHERE group_id=?", (new, gid))
        db.commit()

    elif data in FIELDS_TEXT:
        user_state[(uid, gid)] = data
        return query.message.reply_text("Kirim text nya")

    elif data.startswith("view_"):
        field = data.replace("view_", "")
        query.message.reply_text(format_text(get_field(gid, field)))
        return

    elif data == "copy":
        query.message.reply_text(build_text(gid), parse_mode="Markdown")
        return

    elif data == "reset_all":
        cur.execute("UPDATE jobdast SET host='',backup='',keliling='',tagall='',gcast='',link='' WHERE group_id=?", (gid,))
        db.commit()

    elif data.startswith("reset_"):
        f = data.replace("reset_", "")
        cur.execute(f"UPDATE jobdast SET {f}='' WHERE group_id=?", (gid,))
        db.commit()

    query.message.edit_text(
        build_text(gid),
        reply_markup=keyboard(),
        parse_mode="Markdown"
    )


# ================= INPUT =================
def job_input(update, context):
    gid = update.effective_chat.id
    uid = update.effective_user.id

    key = user_state.get((uid, gid))
    if not key:
        return

    text = update.message.text

    old = get_field(gid, key)
    new = text if not old else old + "\n" + text

    cur.execute(f"UPDATE jobdast SET {key}=? WHERE group_id=?", (new, gid))
    db.commit()

    user_state.pop((uid, gid), None)

    update.message.reply_text("Saved ✅")


# ================= REGISTER =================
def register_jobdast(dp):
    dp.add_handler(CommandHandler("getjobdast", job_cmd))
    dp.add_handler(CallbackQueryHandler(job_button, pattern="^job_"))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, job_input))
