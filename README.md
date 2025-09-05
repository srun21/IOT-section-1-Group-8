# IOT-section-1-Group-8


# ESP32 DHT22 Telegram Bot - Configuration Guide

## Overview
This project creates an ESP32-based temperature monitoring system that sends alerts via Telegram and allows remote relay control.

## Features
- **Real-time monitoring**: DHT22 sensor readings every 5 seconds
- **Telegram integration**: Bot commands and automatic alerts  
- **Smart relay control**: Temperature-based automation with manual override
- **Robust operation**: Auto-reconnect WiFi, error handling, crash recovery

---

## Hardware Requirements
ESP32 Development Board = 1
DHT22 Temperature/Humidity Sensor = 1
Relay Module 5V single-channel relay = 1 
Jumper Wires Male-to-male and male-to-female = 6
ESP32 Shield Expansion board = 1

---

### Connection Diagram 
<img width="1684" height="993" alt="Screenshot 2025-09-05 200706" src="https://github.com/user-attachments/assets/8fe07c41-f4b6-4172-9218-dc955959aff6" />

---

## Telegram Bot Setup

### Step 1: Create Telegram Bot
1. **Open Telegram** and search for `@BotFather`
2. **Start chat** with BotFather and send `/newbot`
3. **Choose bot name** (e.g., "MyESP32Bot")
4. **Choose username** (must end with 'bot', e.g., "myesp32_bot")
5. **Copy the bot token** (format: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### Step 2: Get Group Chat ID
1. **Create a Telegram group** or use existing one
2. **Add your bot** to the group
3. **Send a test message** in the group
4. **Visit URL**: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
5. **Find your group chat ID** (negative number like `-1234567890`)

```
```

---

## ⚙️ Software Configuration

### Step 1: Install MicroPython
1. **Download** MicroPython firmware for ESP32
2. **Flash firmware** using esptool:
   ```bash
   esptool.py --chip esp32 --port /dev/ttyUSB0 erase_flash
   esptool.py --chip esp32 --port /dev/ttyUSB0 write_flash -z 0x1000 esp32-micropython.bin
   ```

### Step 2: Configure Code Settings
Edit the configuration section in `main.py`:

```python
# ---------- USER CONFIG ----------
WIFI_SSID     = "YourWiFiNetwork"        # Your WiFi name
WIFI_PASSWORD = "YourWiFiPassword"       # Your WiFi password

BOT_TOKEN     = "123456789:ABCdef..."    # Your bot token from BotFather
GROUP_CHAT_ID = "-1234567890"            # Your group chat ID (negative number)

RELAY_PIN = 2                            # GPIO pin for relay (default: 2)
DHT_PIN = 4                              # GPIO pin for DHT22 (default: 4)
TEMP_THRESHOLD = 30.0                    # Temperature threshold in °C
RELAY_ACTIVE_LOW = False                 # True if relay activates on LOW signal
DEBUG = True                             # Enable debug messages
# ---------------------------------
```

### Step 3: Upload Code
1. **Connect ESP32** to computer via USB
2. **Use Thonny IDE** or similar tool
3. **Upload** `main.py` to ESP32
4. **Reset** ESP32 to start program

---

## Bot Commands


 `/status`  Show current temperature, humidity, and relay state => `Temperature: 25.67°C`<br>`Humidity: 60.23%`<br>`Relay: OFF` |
 `/on` = Turn relay ON and stop temperature alerts =>`Relay turned ON - Alerts stopped` 
 `/off` = Turn relay OFF and stop all alerts => `Relay turned OFF` 




Flowchart:
<img width="2316" height="1560" alt="mermaid-diagram-2025-09-05-201824" src="https://github.com/user-attachments/assets/44842514-1ef3-461a-a9d0-bb029625f6a2" />


Task 1-Sensor Read & Print (10 pts)
• Read DHT22 every 5 seconds and print the temperature and humidity with 2
decimals
<img width="702" height="503" alt="Screenshot 2025-09-05 192601" src="https://github.com/user-attachments/assets/57dd45e6-9368-4f3d-b246-27ad9d3a5667" />

Task 2-Telegram Send (15 pts)
• Implement send_message() and post a test message to your group.
<img width="1274" height="1211" alt="Screenshot 2025-09-05 193250" src="https://github.com/user-attachments/assets/2af8e62d-0917-4229-9bd8-f994eb14ddfa" />

Task 3-Bot Command (15 pts)
• Implement /status to reply with current T/H and relay state.
• Implement /on and /off to control the relay.

<img width="1270" height="808" alt="Screenshot 2025-09-05 193621" src="https://github.com/user-attachments/assets/3d147cb3-b5db-427d-a0bd-af439b3cd3b1" />
status command

<img width="1196" height="847" alt="Screenshot 2025-09-05 193640" src="https://github.com/user-attachments/assets/443fd9db-7244-429d-aa1e-534fe93e712c" />
/on and /off command


Task 4-Bot Command (20 pts)
• No messages while T < 30 °C.
• If T ≥ 30 °C and relay is OFF, send an alert every loop (5 s) until /on is
received.
• After /on, stop alerts. When T < 30 °C, turn relay OFF automatically and send
a one-time “auto-OFF” notice.

[Watch Demo](https://drive.google.com/file/d/1KiACUyVzblg5Oj_PIu9NqFlMq9GZxGU3/view?usp=sharing)







