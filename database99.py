import zipfile
import os
import time
import threading
import shutil
from datetime import datetime, timedelta

PARTNER_FILE = "partner.json99"
SETTING_FILE = "setting.json99"
LOG_GROUP_ID = -1003828328341

bot = None

# ================= SET TIMEZONE =================
os.environ["TZ"] = "Asia/Jakarta"
try:
    time.tzset()
except:
    pass

# ================= WAIT TIME =================
def wait_until(hour, minute=0):
    now = datetime.now()
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if now >= target:
        target += timedelta(days=1)
    time.sleep((target - now).total_seconds())

# ================= CREATE BACKUP =================
def create_backup():
    name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    with zipfile.ZipFile(name, 'w') as z:
        if os.path.exists(PARTNER_FILE):
            z.write(PARTNER_FILE)
        if os.path.exists(SETTING_FILE):
            z.write(SETTING_FILE)
    return name

# ================= AUTO BACKUP =================
def backup_daily():
    while True:
        wait_until(7, 0)
        try:
            bot.send_message(LOG_GROUP_ID, "📦 BACKUP HARIAN DIMULAI (07:00 WIB)")

            file = create_backup()
            with open(file, "rb") as f:
                bot.send_document(LOG_GROUP_ID, f)

            os.remove(file)

            bot.send_message(LOG_GROUP_ID, "✅ BACKUP HARIAN SELESAI")

        except Exception as e:
            print("❌ BACKUP ERROR:", e)
            try:
                bot.send_message(LOG_GROUP_ID, f"❌ BACKUP ERROR\n{e}")
            except:
                pass

# ================= RESET LIMIT =================
def reset_limit_daily():
    while True:
        now = datetime.now()

        if now.hour == 0 and now.minute < 2:
            try:
                bot.send_message(LOG_GROUP_ID, "🧹 RESET LIMIT + CLEAN CACHE")

                with open("limit_gc.json99", "w") as f:
                    f.write("{}")

                # CLEAN CACHE
                for root, dirs, files in os.walk("."):
                    for d in dirs:
                        if d == "__pycache__":
                            shutil.rmtree(os.path.join(root, d), ignore_errors=True)

                for file in os.listdir("."):
                    if file.endswith(".session-journal"):
                        os.remove(file)

                bot.send_message(LOG_GROUP_ID, "✅ RESET SELESAI")

            except Exception as e:
                print("❌ RESET ERROR:", e)

            time.sleep(60)

        time.sleep(20)

# ================= RESTART =================
def restart_daily():
    while True:
        wait_until(0, 0)
        try:
            bot.send_message(LOG_GROUP_ID, "♻️ SYSTEM RESET HARIAN")

            file = create_backup()
            with open(file, "rb") as f:
                bot.send_document(LOG_GROUP_ID, f)

            os.remove(file)

        except Exception as e:
            print("❌ RESTART ERROR:", e)

# ================= SAFE THREAD =================
def safe_thread(func):
    def wrapper():
        while True:
            try:
                func()
            except Exception as e:
                print("❌ THREAD ERROR:", e)
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
            print("❌ BOT CRASH:", e)
            try:
                bot.send_message(LOG_GROUP_ID, f"🚨 BOT CRASH\n{e}")
            except:
                pass
        time.sleep(30)

# ================= START =================
is_started = False

def safe_thread(func):
    def wrapper():
        try:
            func()
        except Exception as e:
            print("THREAD ERROR:", e)
    return wrapper


def start_database_system(bot_instance):
    global bot, is_started

    if is_started:
        print("⚠️ DATABASE SUDAH JALAN")
        return

    is_started = True
    bot = bot_instance

    threading.Thread(target=safe_thread(backup_daily), daemon=True).start()
    threading.Thread(target=safe_thread(reset_limit_daily), daemon=True).start()
    threading.Thread(target=safe_thread(restart_daily), daemon=True).start()
    threading.Thread(target=safe_thread(monitor), daemon=True).start()
