import json
import requests
import time
import os
import random
from datetime import datetime

# =========================================================
# CONFIG
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

CHECK_INTERVAL = 600
REQUEST_TIMEOUT = 10

STATE_FILE = "monitor_state.json"
LOG_FILE = "monitor.log"

# =========================================================
# RANDOM TEST URLS
# =========================================================

TEST_URLS = [
    "http://www.gstatic.com/generate_204",
    "http://cp.cloudflare.com/generate_204",
    "http://connectivitycheck.gstatic.com/generate_204",
    "http://www.google.com/generate_204"
]

# =========================================================
# VALIDATE ENV
# =========================================================

if not BOT_TOKEN or not CHAT_ID:

    print("BOT_TOKEN or CHAT_ID missing")
    print("Please set environment variables")

    exit()

# =========================================================
# LOAD CONFIG
# =========================================================

with open("mapping.json", "r", encoding="utf-8") as f:

    data = json.load(f)

groups = data["groups"]
devices = data["devices"]

# =========================================================
# LOAD STATE
# =========================================================

if os.path.exists(STATE_FILE):

    with open(STATE_FILE, "r", encoding="utf-8") as f:

        state = json.load(f)

else:

    state = {}

# =========================================================
# FIRST RUN
# =========================================================

first_run = len(state) == 0

# =========================================================
# LOG
# =========================================================

def log(text):

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    line = f"[{now}] {text}"

    print(line)

    with open(LOG_FILE, "a", encoding="utf-8") as f:

        f.write(line + "\n")

# =========================================================
# TELEGRAM
# =========================================================

def send_telegram(message):

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    try:

        requests.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": message
            },
            timeout=15
        )

        log("TELEGRAM SENT")

    except Exception as e:

        log(f"TELEGRAM ERROR: {e}")

# =========================================================
# RANDOM TEST URL
# =========================================================

def get_random_test_url():

    return random.choice(TEST_URLS)

# =========================================================
# SAVE STATE
# =========================================================

def save_state():

    with open(STATE_FILE, "w", encoding="utf-8") as f:

        json.dump(
            state,
            f,
            indent=2,
            ensure_ascii=False
        )

# =========================================================
# GET DEVICE LIST
# =========================================================

def get_devices_by_group(group_name):

    result = []

    for device, group in devices.items():

        if group == group_name:

            result.append(device)

    return result

# =========================================================
# FORMAT DEVICE LIST
# =========================================================

def format_devices(device_list):

    if not device_list:

        return "None"

    return "\n".join([f"• {x}" for x in device_list])

# =========================================================
# TEST PROXY
# =========================================================

def test_proxy(proxy):

    proxy_type = proxy["type"].lower()

    # =====================================================
    # SCHEME
    # =====================================================

    if proxy_type == "socks5":

        scheme = "socks5h"

    elif proxy_type == "socks4":

        scheme = "socks4"

    elif proxy_type in ["http", "https"]:

        scheme = "http"

    else:

        log(f"UNSUPPORTED PROXY TYPE: {proxy_type}")

        return {
            "alive": False,
            "latency": None
        }

    # =====================================================
    # BUILD PROXY URL
    # =====================================================

    proxy_url = (
        f"{scheme}://"
        f"{proxy['user']}:{proxy['pass']}@"
        f"{proxy['proxy']}:{proxy['port']}"
    )

    proxies = {
        "http": proxy_url,
        "https": proxy_url
    }

    test_url = get_random_test_url()

    start = time.time()

    try:

        r = requests.get(
            test_url,
            proxies=proxies,
            timeout=REQUEST_TIMEOUT
        )

        latency = round((time.time() - start) * 1000)

        if r.status_code in [200, 204]:

            return {
                "alive": True,
                "latency": latency
            }

        log(
            f"BAD STATUS "
            f"{proxy['proxy']}:{proxy['port']} "
            f"-> {r.status_code}"
        )

        return {
            "alive": False,
            "latency": None
        }

    except requests.exceptions.ConnectTimeout:

        log(
            f"CONNECT TIMEOUT "
            f"{proxy['proxy']}:{proxy['port']}"
        )

    except requests.exceptions.ReadTimeout:

        log(
            f"READ TIMEOUT "
            f"{proxy['proxy']}:{proxy['port']}"
        )

    except requests.exceptions.ProxyError as e:

        log(
            f"PROXY ERROR "
            f"{proxy['proxy']}:{proxy['port']} "
            f"-> {e}"
        )

    except requests.exceptions.ConnectionError as e:

        log(
            f"CONNECTION ERROR "
            f"{proxy['proxy']}:{proxy['port']} "
            f"-> {e}"
        )

    except Exception as e:

        log(
            f"UNKNOWN ERROR "
            f"{proxy['proxy']}:{proxy['port']} "
            f"-> {e}"
        )

    return {
        "alive": False,
        "latency": None
    }

# =========================================================
# CHECK GROUP
# =========================================================

def check_group(group_name, group):

    log(f"CHECK GROUP: {group_name}")

    # =====================================================
    # MAIN
    # =====================================================

    main_result = test_proxy(group["main"])

    if main_result["alive"]:

        log(
            f"{group_name} MAIN OK "
            f"({main_result['latency']} ms)"
        )

        return {
            "status": "MAIN",
            "active": "MAIN",
            "latency": main_result["latency"]
        }

    log(f"{group_name} MAIN DEAD")

    # =====================================================
    # BACKUPS
    # =====================================================

    backups = group.get("backups", [])

    for i, backup in enumerate(backups, start=1):

        backup_name = f"BACKUP{i}"

        log(f"CHECK {group_name} -> {backup_name}")

        result = test_proxy(backup)

        if result["alive"]:

            log(
                f"{group_name} USING {backup_name} "
                f"({result['latency']} ms)"
            )

            return {
                "status": "BACKUP",
                "active": backup_name,
                "latency": result["latency"]
            }

    # =====================================================
    # DEAD
    # =====================================================

    log(f"{group_name} ALL PROXIES DEAD")

    return {
        "status": "DEAD",
        "active": "NONE",
        "latency": None
    }

# =========================================================
# STARTUP MESSAGE
# =========================================================

def build_startup_message(all_status):

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    msg = (
        f"📊 SYSTEM STATUS\n\n"
        f"Time: {now}\n\n"
    )

    for group_name, status in all_status.items():

        if status["status"] == "MAIN":

            msg += (
                f"{group_name}\n"
                f"→ MAIN\n"
                f"→ {status['latency']} ms\n\n"
            )

        elif status["status"] == "BACKUP":

            msg += (
                f"{group_name}\n"
                f"→ {status['active']}\n"
                f"→ {status['latency']} ms\n\n"
            )

        else:

            msg += (
                f"{group_name}\n"
                f"→ ALL DEAD\n\n"
            )

    return msg

# =========================================================
# ALERT MESSAGE
# =========================================================

def build_alert_message(group_name, status, device_text):

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if status["status"] == "MAIN":

        return (
            f"✅ RECOVERED\n\n"
            f"Time: {now}\n"
            f"Group: {group_name}\n"
            f"Active Proxy: MAIN\n"
            f"Latency: {status['latency']} ms\n\n"
            f"Devices:\n"
            f"{device_text}"
        )

    if status["status"] == "BACKUP":

        return (
            f"⚠️ FAILOVER\n\n"
            f"Time: {now}\n"
            f"Group: {group_name}\n"
            f"MAIN DEAD\n"
            f"Using: {status['active']}\n"
            f"Latency: {status['latency']} ms\n\n"
            f"Devices:\n"
            f"{device_text}"
        )

    return (
        f"🚨 CRITICAL\n\n"
        f"Time: {now}\n"
        f"Group: {group_name}\n"
        f"ALL PROXIES DEAD\n\n"
        f"Devices:\n"
        f"{device_text}"
    )

# =========================================================
# START
# =========================================================

log("MONITOR STARTED")

# =========================================================
# MAIN LOOP
# =========================================================

while True:

    try:

        log("========================================")
        log("START CHECKING")
        log("========================================")

        startup_status = {}

        for group_name, group in groups.items():

            current_status = check_group(
                group_name,
                group
            )

            startup_status[group_name] = current_status

            old_status = state.get(group_name)

            device_list = get_devices_by_group(group_name)

            device_text = format_devices(device_list)

            # =================================================
            # FIRST RUN
            # =================================================

            if first_run:

                state[group_name] = current_status

                save_state()

                continue

            # =================================================
            # CHANGED
            # =================================================

            changed = current_status != old_status

            if changed:

                log(
                    f"STATUS CHANGED: "
                    f"{group_name} -> {current_status}"
                )

                msg = build_alert_message(
                    group_name,
                    current_status,
                    device_text
                )

                send_telegram(msg)

                state[group_name] = current_status

                save_state()

            else:

                log(f"NO CHANGE: {group_name}")

        # =====================================================
        # FIRST RUN REPORT
        # =====================================================

        if first_run:

            startup_msg = build_startup_message(
                startup_status
            )

            send_telegram(startup_msg)

            first_run = False

        log(f"SLEEP {CHECK_INTERVAL}s")

        time.sleep(CHECK_INTERVAL)

    except Exception as e:

        log(f"MAIN LOOP ERROR: {e}")

        time.sleep(30)