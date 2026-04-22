import zipfile
import os
import time
import threading
import shutil
from datetime import datetime, timedelta

# ================= BOT INSTANCE =================
bot = None

LOG_GROUP_ID = -1003724444499

# ================= TIMEZONE =================
os.environ["TZ"] = "Asia/Jakarta"
try:
    time.tzset()
except:
    pass


# ================= WAIT UNTIL =================
def wait_until(hour, minute=0):
    now = datetime.now()
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if now >= target:
        target += timedelta(days=1)
    time.sleep((target - now).total_seconds())


# ================= BACKUP =================
def create_backup():
    name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"

    with zipfile.ZipFile(name, 'w', zipfile.ZIP_DEFLATED) as z:
        files = [
            "setting.json99",
            "partner.json99",
            "buttons.json99",
            "autotag.json99"
        ]

        for f in files:
            if os.path.exists(f):
                z.write(f)

    return name


# ================= DAILY BACKUP =================
def backup_daily():
    while True:
        wait_until(7, 0)

        try:
            bot.send_message(LOG_GROUP_ID, "📦 BACKUP HARIAN")

            file = create_backup()

            with open(file, "rb") as f:
                bot.send_document(LOG_GROUP_ID, f)

            os.remove(file)

            bot.send_message(LOG_GROUP_ID, "✅ BACKUP SELESAI")

        except Exception as e:
            print("BACKUP ERROR:", e)


# ================= RESET SYSTEM =================
def reset_limit_daily():
    while True:
        now = datetime.now()

        if now.hour == 0 and now.minute < 2:
            try:
                bot.send_message(LOG_GROUP_ID, "🧹 RESET SYSTEM")

                with open("limit_gc.json0", "w") as f:
                    f.write("{}")

                for root, dirs, files in os.walk("."):
                    for d in dirs:
                        if d == "__pycache__":
                            shutil.rmtree(os.path.join(root, d), ignore_errors=True)

                for file in os.listdir("."):
                    if file.endswith(".session-journal"):
                        os.remove(file)

                bot.send_message(LOG_GROUP_ID, "✅ RESET DONE")

            except Exception as e:
                print("RESET ERROR:", e)

            time.sleep(60)

        time.sleep(20)


# ================= RESTART DAILY =================
def restart_daily():
    while True:
        wait_until(0, 0)

        try:
            bot.send_message(LOG_GROUP_ID, "♻️ RESTART DAILY")

            file = create_backup()

            with open(file, "rb") as f:
                bot.send_document(LOG_GROUP_ID, f)

            os.remove(file)

        except Exception as e:
            print("RESTART ERROR:", e)


# ================= SAFE THREAD =================
def safe_thread(func):
    def wrapper():
        while True:
            try:
                func()
            except Exception as e:
                print("THREAD ERROR:", e)
                try:
                    bot.send_message(LOG_GROUP_ID, f"🚨 THREAD ERROR\n{e}")
                except:
                    pass
                time.sleep(5)
    return wrapper


# ================= MONITOR =================
def monitor():
    while True:
        try:
            bot.get_me()
        except Exception as e:
            print("BOT CRASH:", e)
            try:
                bot.send_message(LOG_GROUP_ID, f"🚨 BOT CRASH\n{e}")
            except:
                pass
        time.sleep(30)


# ================= START SYSTEM =================
def start_database_system(bot_instance):
    global bot
    bot = bot_instance

    threading.Thread(target=safe_thread(backup_daily), daemon=True).start()
    threading.Thread(target=safe_thread(reset_limit_daily), daemon=True).start()
    threading.Thread(target=safe_thread(restart_daily), daemon=True).start()
    threading.Thread(target=monitor, daemon=True).start()

