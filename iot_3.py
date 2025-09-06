import network, time, urequests
from machine import Pin, reset
import dht

# ---------- USER CONFIG ----------
WIFI_SSID     = "project"
WIFI_PASSWORD = "12345678"

BOT_TOKEN     = "8064067573:AAGC1i51f1_YWCLfpO9Ol7slTLWtY88yAnU"
GROUP_CHAT_ID = "-4915364145"

RELAY_PIN = 2
RELAY_ACTIVE_LOW = False
DHT_PIN = 4
TEMP_THRESHOLD = 30.0
POLL_TIMEOUT_S = 5
DEBUG = True
API = "https://api.telegram.org/bot" + BOT_TOKEN
# ---------------------------------

relay = Pin(RELAY_PIN, Pin.OUT)
dht_sensor = dht.DHT22(Pin(DHT_PIN))

# Global state variables
alert_active = False      # Whether we're currently in alert state (T >= 30)
last_id = None           # Last Telegram update ID
last_sensor_read = 0     # Timestamp of last sensor reading
current_temp = None      # Current temperature reading
current_humidity = None  # Current humidity reading
auto_off_sent = False    # Track if auto-off message was sent
wlan = None              # Wi-Fi connection object

# --- Logging ---
def log(*args):
    if DEBUG: 
        print("[LOG]", *args)

# --- URL encoding ---
def urlencode(d):
    parts = []
    for k, v in d.items():
        s = str(v)
        s = (s.replace("%", "%25").replace(" ", "%20").replace("\n", "%0A")
               .replace("&", "%26").replace("?", "%3F").replace("=", "%3D"))
        parts.append(str(k) + "=" + s)
    return "&".join(parts)

# --- Relay Control ---
def relay_on():
    relay.value(0 if RELAY_ACTIVE_LOW else 1)
    log("Relay turned ON")

def relay_off():
    relay.value(1 if RELAY_ACTIVE_LOW else 0)
    log("Relay turned OFF")

def relay_is_on():
    return (relay.value() == 0) if RELAY_ACTIVE_LOW else (relay.value() == 1)

# --- Wi-Fi Connection with Auto-Reconnect ---
def connect_wifi():
    global wlan
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    if wlan.isconnected():
        return True
        
    print("Connecting to Wi-Fi...")
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    
    timeout = 20
    start_time = time.time()
    while not wlan.isconnected():
        if time.time() - start_time > timeout:
            print("Wi-Fi connection timeout")
            return False
        time.sleep(0.5)
        print(".", end="")
    
    print("\nWi-Fi connected:", wlan.ifconfig()[0])
    return True

def check_wifi():
    """Check and reconnect Wi-Fi if needed"""
    global wlan
    if not wlan or not wlan.isconnected():
        print("Wi-Fi disconnected, reconnecting...")
        return connect_wifi()
    return True

# --- Telegram API Functions ---
def send_message(chat_id, text):
    """Send message to Telegram with error handling"""
    try:
        if not check_wifi():
            print("send_message: No Wi-Fi connection")
            return False
            
        url = API + "/sendMessage?" + urlencode({"chat_id": chat_id, "text": text})
        response = urequests.get(url, timeout=10)
        
        if response.status_code == 200:
            log("Message sent successfully")
            response.close()
            return True
        else:
            print("Telegram HTTP Error:", response.status_code)
            response.close()
            return False
            
    except Exception as e:
        print("send_message error:", e)
        return False

def get_updates(offset=None):
    """Get Telegram updates with error handling"""
    try:
        if not check_wifi():
            print("get_updates: No Wi-Fi connection")
            return []
            
        params = {"timeout": 1, "limit": 10}
        if offset is not None:
            params["offset"] = offset
            
        url = API + "/getUpdates?" + urlencode(params)
        response = urequests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            response.close()
            
            if data.get("ok"):
                return data.get("result", [])
            else:
                print("Telegram API Error:", data.get("description", "Unknown"))
                return []
        else:
            print("get_updates HTTP Error:", response.status_code)
            response.close()
            return []
            
    except Exception as e:
        print("get_updates error:", e)
        return []

# --- DHT22 Sensor Reading ---
def read_dht22():
    """Read DHT22 sensor with error handling"""
    global current_temp, current_humidity
    
    try:
        dht_sensor.measure()
        temp = dht_sensor.temperature()
        humidity = dht_sensor.humidity()
        
        current_temp = temp
        current_humidity = humidity
        
        # Print with 2 decimal places as required
        print("Temperature: {:.2f}°C, Humidity: {:.2f}%".format(temp, humidity))
        
        return temp, humidity
        
    except OSError as e:
        print("DHT22 OSError:", e, "- skipping this cycle")
        return None, None
    except Exception as e:
        print("DHT22 Error:", e)
        return None, None

# --- Command Handlers ---
def handle_commands():
    """Process Telegram commands"""
    global last_id, alert_active, auto_off_sent
    
    updates = get_updates(offset=(last_id + 1) if last_id else None)
    
    for update in updates:
        last_id = update["update_id"]
        
        message = update.get("message") or update.get("edited_message")
        if not message:
            continue
            
        chat_id = message["chat"]["id"]
        text = message.get("text", "").strip()
        
        log("Received command:", text, "from chat:", chat_id)
        
        # Handle commands
        if text.lower() == "/status":
            if current_temp is not None and current_humidity is not None:
                status_msg = "Temperature: {:.2f}°C\nHumidity: {:.2f}%\nRelay: {}".format(
                    current_temp, current_humidity, "ON" if relay_is_on() else "OFF"
                )
            else:
                status_msg = "Sensor Error\nRelay: {}".format("ON" if relay_is_on() else "OFF")
            
            send_message(chat_id, status_msg)
            
        elif text.lower() == "/on":
            relay_on()
            # Stop alerts when manually turned on
            if alert_active:
                send_message(chat_id, "Relay turned ON - Alerts stopped")
                alert_active = False
            else:
                send_message(chat_id, "Relay turned ON")
            auto_off_sent = False
            
        elif text.lower() == "/off":
            relay_off()
            alert_active = False
            auto_off_sent = False
            send_message(chat_id, "Relay turned OFF")

# --- Main Control Logic ---
def main():
    global alert_active, last_sensor_read, auto_off_sent
    
    # Initialize
    if not connect_wifi():
        print("Failed to connect to Wi-Fi. Restarting...")
        time.sleep(5)
        reset()
    
    relay_off()  # Start with relay OFF
    
    print("System started. Reading DHT22 every 5 seconds...")
    
    # Send test message for Task 2
    if send_message(GROUP_CHAT_ID, "Bot started! System ready for monitoring."):
        print("Test message sent successfully!")
    
    while True:
        try:
            current_time = time.time()
            
            # Read sensor every 5 seconds (Task 1)
            if current_time - last_sensor_read >= 5.0:
                temp, humidity = read_dht22()
                last_sensor_read = current_time
                
                if temp is not None:
                    # Task 4 logic: Temperature-based alerts and control
                    if temp >= TEMP_THRESHOLD:
                        # Temperature is high
                        if not alert_active:
                            # First time reaching threshold
                            alert_active = True
                            auto_off_sent = False  # Reset auto-off flag
                        
                        # If relay is OFF, send alert every loop
                        if not relay_is_on():
                            alert_msg = "⚠️ ALERT: Temperature {:.2f}°C (≥ {:.1f}°C)\nRelay is OFF. Send /on to activate.".format(
                                temp, TEMP_THRESHOLD
                            )
                            send_message(GROUP_CHAT_ID, alert_msg)
                    
                    else:
                        # Temperature is below threshold
                        if alert_active and relay_is_on():
                            # Auto turn OFF relay and send one-time notice
                            relay_off()
                            if not auto_off_sent:
                                send_message(GROUP_CHAT_ID, "✅ Temperature normalized ({:.2f}°C). Relay auto-OFF.".format(temp))
                                auto_off_sent = True
                        
                        alert_active = False
            
            # Handle Telegram commands (Task 3)
            handle_commands()
            
            # Short sleep to prevent busy waiting
            time.sleep(0.1)
            
        except Exception as e:
            print("Main loop error:", e)
            time.sleep(2)  # Wait before retrying

# --- Entry Point ---
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Program interrupted")
    except Exception as e:
        print("Fatal error:", e)
        print("Restarting in 10 seconds...")
        time.sleep(10)
        reset()
