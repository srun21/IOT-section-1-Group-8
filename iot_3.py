import network, time, urequests
from machine import Pin, reset
import dht

# ---------- USER CONFIG ----------
WIFI_SSID     = "project"
WIFI_PASSWORD = "12345678"

BOT_TOKEN     = "8064067573:AAGC1i51f1_YWCLfpO9Ol7slTLWtY88yAnU"   # your bot token
GROUP_CHAT_ID = "-4915364145"   # replace with your group chat id

RELAY_PIN = 2                  # GPIO for Relay
RELAY_ACTIVE_LOW = False
DHT_PIN = 4                    # GPIO for DHT22
TEMP_THRESHOLD = 30            # °C threshold
POLL_TIMEOUT_S = 20
DEBUG = True
API = "https://api.telegram.org/bot" + BOT_TOKEN
# ---------------------------------

relay = Pin(RELAY_PIN, Pin.OUT)
dht_sensor = dht.DHT22(Pin(DHT_PIN))

mode_auto = True   # auto by default
alert_sent = False # track if high-temp alert already sent
last_id = None
last_report = 0    # for 5s interval updates

# --- Logging ---
def log(*a):
    if DEBUG: print(*a)

# --- URL encoding (simple) ---
def urlencode(d):
    parts = []
    for k, v in d.items():
        s = str(v)
        s = (s.replace("%", "%25").replace(" ", "%20").replace("\n", "%0A")
               .replace("&", "%26").replace("?", "%3F").replace("=", "%3D"))
        parts.append(str(k)+"="+s)
    return "&".join(parts)

# --- Relay helpers ---
def relay_on():  relay.value(0 if RELAY_ACTIVE_LOW else 1)
def relay_off(): relay.value(1 if RELAY_ACTIVE_LOW else 0)
def relay_is_on(): return (relay.value()==0) if RELAY_ACTIVE_LOW else (relay.value()==1)

# --- Wi-Fi ---
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting Wi-Fi...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        t0 = time.time()
        while not wlan.isconnected():
            if time.time()-t0 > 25:
                raise RuntimeError("Wi-Fi connect timeout")
            time.sleep(0.25)
    print("Wi-Fi OK:", wlan.ifconfig())
    return wlan

# --- Telegram API ---
def send_message(chat_id, text):
    try:
        url = API + "/sendMessage?" + urlencode({"chat_id": chat_id, "text": text})
        r = urequests.get(url)
        _ = r.text; r.close()
        log("→ sent to", chat_id)
    except Exception as e:
        print("send_message error:", e)

def get_updates(offset=None, timeout=POLL_TIMEOUT_S):
    qs = {"timeout": timeout}
    if offset is not None:
        qs["offset"] = offset
    url = API + "/getUpdates?" + urlencode(qs)
    try:
        r = urequests.get(url)
        data = r.json(); r.close()
        if not data.get("ok"):
            return []
        return data.get("result", [])
    except Exception as e:
        print("get_updates error:", e)
        return []

# --- DHT22 Sensor ---
def read_dht22():
    try:
        dht_sensor.measure()
        return dht_sensor.temperature(), dht_sensor.humidity()
    except Exception as e:
        print("DHT22 Error:", e)
        return None, None

# --- Handle Commands ---
HELP = (
    "Commands:\n"
    "/on – turn relay ON (manual)\n"
    "/off – turn relay OFF (manual)\n"
    "/auto – switch back to auto mode\n"
    "/status – relay + mode state\n"
    "/temp – show current temp"
)

def handle_cmd(chat_id, text):
    global mode_auto
    t = (text or "").strip().lower()

    if t in ("/on", "on"):
        relay_on()
        mode_auto = False
        send_message(chat_id, "Relay ON (manual override)")
    elif t in ("/off", "off"):
        relay_off()
        mode_auto = False
        send_message(chat_id, "Relay OFF (manual override)")
    elif t in ("/auto", "auto"):
        mode_auto = True
        send_message(chat_id, "Switched to AUTO mode")
    elif t in ("/status", "status"):
        msg = "Relay is " + ("ON" if relay_is_on() else "OFF")
        msg += " | Mode: " + ("AUTO" if mode_auto else "MANUAL")
        send_message(chat_id, msg)
    elif t in ("/temp", "temp"):
        temp, hum = read_dht22()
        if temp is not None:
            send_message(chat_id, "Temp: {}°C\n Humidity: {}%".format(temp, hum))
        else:
            send_message(chat_id, "Sensor error")
    else:
        send_message(chat_id, HELP)

# --- Main Loop ---
def main():
    global alert_sent, mode_auto, last_id, last_report
    connect_wifi()
    relay_off()

    print("Bot running. AUTO mode + 5s sensor reports…")

    while True:
        try:
            now = time.time()

            # read sensor
            temp, hum = read_dht22()
            if temp is not None:
                # auto control
                if mode_auto:
                    if temp > TEMP_THRESHOLD:
                        if not relay_is_on():
                            relay_on()
                            send_message(GROUP_CHAT_ID, "Temp High: {}°C – Relay AUTO-ON".format(temp))
                        if not alert_sent:
                            send_message(GROUP_CHAT_ID, "Alert: Temp {}°C above {}°C".format(temp, TEMP_THRESHOLD))
                            alert_sent = True
                    else:
                        if relay_is_on():
                            relay_off()
                            send_message(GROUP_CHAT_ID, "Temp Normal: {}°C – Relay AUTO-OFF".format(temp))
                        if alert_sent:
                            alert_sent = False

                # periodic 5s report
                if now - last_report >= 5:
                    msg = "Update:\n {}°C\n {}%\nRelay: {}\nMode: {}".format(
                        temp, hum, "ON" if relay_is_on() else "OFF", "AUTO" if mode_auto else "MANUAL"
                    )
                    send_message(GROUP_CHAT_ID, msg)
                    last_report = now

            # check Telegram commands
            updates = get_updates(offset=(last_id + 1) if last_id else None)
            for u in updates:
                last_id = u["update_id"]
                msg = u.get("message") or u.get("edited_message")
                if not msg: continue
                cid = msg["chat"]["id"]
                txt = msg.get("text", "")
                log("From", cid, ":", txt)
                handle_cmd(cid, txt)

        except Exception as e:
            print("Loop error:", e)
            time.sleep(2)

        time.sleep(1)

try:
    main()
except Exception as e:
    print("Fatal error:", e)
    time.sleep(5)
    reset()
