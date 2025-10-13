# 🚗 ESP32 Smart Parking System

A three-slot automated parking management system with real-time web dashboard, auto ID assignment, and Telegram receipt notifications built with MicroPython.

## 📋 Features

- **Automated Entry Control**: Ultrasonic sensor detects vehicles and opens servo gate only when slots are available
- **Smart ID Assignment**: Automatically assigns IDs 1-3 to vehicles in the order they occupy slots
- **Real-time Monitoring**: Live web dashboard showing slot status, active tickets, and billing history
- **Automatic Billing**: Tracks entry/exit times and calculates parking fees ($0.50 per minute)
- **Telegram Integration**: Sends receipt notifications when vehicles exit
- **LCD Display**: Shows available slots or "FULL" status at entry gate
- **Visual Feedback**: LED indicators for gate status and parking availability
- **Flash Animation**: Newly occupied slots flash on the dashboard for 60 seconds

## 🔧 Hardware Requirements

| Component | Quantity | Purpose |
|-----------|----------|---------|
| ESP32 Development Board | 1 | Main controller (MicroPython) |
| HC-SR04 Ultrasonic Sensor | 1 | Entry gate vehicle detection |
| IR Obstacle Sensors | 3 | Individual slot occupancy detection |
| SG90 Servo Motor | 1 | Gate control |
| 16×2 LCD Display (I2C) | 1 | Entry status display |
| LED (Green) | 1 | Gate open indicator |
| LED (Red) | 1 | Parking full indicator |
| Resistors (220Ω) | 2 | For LEDs |
| Jumper Wires | - | Connections |
| Breadboard | 1 | Optional for prototyping |

## Pin Configuration

```python
# Ultrasonic Sensor (Gate)
PIN_ULTRASONIC_TRIG = 27  # Trigger pin
PIN_ULTRASONIC_ECHO = 26  # Echo pin

# Servo Motor (Gate)
PIN_SERVO = 14

# IR Sensors (Slots)
PIN_IR_S1 = 32  # Slot 1
PIN_IR_S2 = 35  # Slot 2
PIN_IR_S3 = 34  # Slot 3

# LCD Display (I2C)
I2C_SCL = 19  # Clock
I2C_SDA = 18  # Data
I2C_FREQ = 400000

# LED Indicators
PIN_LED_GATE = 21  # Green - Gate open
PIN_LED_FULL = 22  # Red - Parking full
```

## Getting Started

### Prerequisites

1. **ESP32 with MicroPython** installed
   - Download firmware: [MicroPython ESP32 Downloads](https://micropython.org/download/esp32/)
   - Flash tool: [esptool.py](https://github.com/espressif/esptool)

2. **Python 3.x** (for uploading code)

3. **Required MicroPython Libraries** (all included in the code):
   - `network` - WiFi connectivity
   - `socket` - Web server
   - `urequests` - Telegram API calls
   - `machine` - Hardware control (Pin, PWM, I2C)
   - `utime` - Time functions

### Installation

1. **Flash MicroPython to ESP32**
   ```bash
   # Erase flash
   esptool.py --port /dev/ttyUSB0 erase_flash
   
   # Flash MicroPython firmware
   esptool.py --chip esp32 --port /dev/ttyUSB0 write_flash -z 0x1000 esp32-*.bin
   ```

2. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/esp32-smart-parking.git
   cd esp32-smart-parking
   ```

3. **Configure WiFi and Telegram**
   
   Edit `main_consolidated.py`:
   ```python
   WIFI_SSID = "Your_WiFi_SSID"
   WIFI_PASS = "Your_WiFi_Password"
   TELEGRAM_BOT_TOKEN = "Your_Bot_Token"
   CHAT_ID = "Your_Chat_ID"
   ```

4. **Upload to ESP32**
   
     using **Thonny IDE**:
   - Open `main_consolidated.py`
   - Save as `main.py` to the ESP32
   - Click Run

5. **Connect to Serial Monitor**
   ```bash
   screen /dev/ttyUSB0 115200
   # or
   minicom -D /dev/ttyUSB0 -b 115200
   ```
   
   You'll see the ESP32's IP address after successful WiFi connection.

## How It Works

### Entry Process

1. Vehicle approaches gate (distance < 10cm detected by ultrasonic)
2. System checks slot availability:
   - **Slots available**: 
     - LCD shows "Free: S1 S2 S3"
     - Green LED lights up
     - Servo gate opens to 40-90 degree for 2 seconds
   - **All full**: 
     - LCD shows "FULL"
     - Red LED lights up
     - Gate remains closed
3. Vehicle parks in available slot
4. IR sensor detects occupancy (debounced for 300ms)
5. System assigns lowest available ID (1, 2, or 3)
6. Records entry time and creates active ticket
7. **Dashboard flash**: Newly occupied slot flashes for 60 seconds ( open web with your IP Address)
8. If parking becomes full while gate is open, gate closes immediately

### Exit Process

1. Vehicle leaves slot
2. IR sensor detects vacancy for ≥1 second (exit grace period)
3. System calculates:
   - Duration (rounded up to nearest minute)
   - Fee ($0.50/minute)
4. Ticket marked as CLOSED
5. **Telegram receipt sent automatically**
6. Slot and ID become available for next vehicle
7. Gate closes if it was open

### ID Assignment Logic

IDs are assigned **dynamically** based on occupancy order:
- First car to park gets ID 1
- Second car gets ID 2
- Third car gets ID 3
- When a car leaves, its ID is released
- Next entering car gets the lowest available ID

**Example Scenario**:
```
Car A parks in S2 → Assigned ID 1
Car B parks in S1 → Assigned ID 2
Car A leaves S2   → ID 1 freed
Car C parks in S3 → Assigned ID 1 (reused)
Car D parks in S2 → Assigned ID 3
```

## 🌐 Web Dashboard

Access the dashboard by opening a browser and navigating to the ESP32's IP address (shown on Serial Monitor and LCD).

```
http://192.168.x.x
```

### Dashboard Features

**Status Bar** (Auto-refreshes every 3 seconds):
```
Total Slots: 3 | Free: 2 | Occupied: 1 | Status: Available
```

**Slot Panel**:
- **Visual representation** of each slot (S1, S2, S3)
- **Color coding**: Green border (Free) / Red border (Occupied)
- **Flash effect**: Newly occupied slots flash red for 60 seconds
- For occupied slots: Shows ID, Elapsed time (HH:MM:SS)

**Active Tickets Table**:
| ID | Slot | Time-In | Elapsed |
|----|------|---------|---------|
| 1  | S2   | 2025-10-13 14:23:15 | 00:05:32 |
| 2  | S1   | 2025-10-13 14:25:40 | 00:03:07 |

**Recent Tickets Table** (Last 10 closed):
| ID | Slot | Duration | Fee | Time-Out |
|----|------|----------|-----|----------|
| 3  | S3   | 15 min   | $7.50 | 2025-10-13 14:38:42 |
| 1  | S2   | 8 min    | $4.00 | 2025-10-13 14:31:15 |

### Dashboard Design
- **Responsive layout** adapts to mobile and desktop
- **Modern UI** with card-based design
- **Real-time updates** via meta refresh (no JavaScript needed)
- **Color-coded status** for instant visibility

## Telegram Setup

### 1. Create a Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Follow instructions to name your bot
4. Copy the **Bot Token** (looks like: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 2. Get Your Chat ID

**Method 1** - Using @userinfobot:
1. Search for `@userinfobot` in Telegram
2. Start a chat - it will show your Chat ID

**Method 2** - Using API:
1. Send any message to your bot
2. Visit: `https://api.telegram.org/bot<YourBOTToken>/getUpdates`
3. Find `"chat":{"id":123456789}` in the JSON response

### 3. Update Configuration

Edit in `main_consolidated.py`:
```python
TELEGRAM_BOT_TOKEN = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
CHAT_ID = "123456789"
```

### Receipt Format

When a vehicle exits, you receive:
```
Ticket CLOSED
ID: 1 Slot: S2
Duration: 15 minutes
Fee: $7.5
```

## ⚙️ Configuration Parameters

All configurable parameters are at the top of `main.py`:

### Network Settings
```python
WIFI_SSID = "Your_WiFi_SSID"
WIFI_PASS = "Your_WiFi_Password"
TELEGRAM_BOT_TOKEN = "Your_Bot_Token"
CHAT_ID = "Your_Chat_ID"
```

### Detection & Pricing
```python
ULTRASONIC_DETECT_CM = 10     # Detection distance in cm
FEE_PER_MIN = 0.5             # $0.50 per minute
NUM_SLOTS = 3                 # Total parking slots
WEBSERVER_PORT = 80           # HTTP port
```

## 📊 System States & Flow

```
IDLE → VEHICLE_DETECTED → CHECK_AVAILABILITY
                                ↓
                   (If Free)    |    (If Full)
                        ↓       |       ↓
                 GATE_OPENING   |   GATE_BLOCKED
                        ↓
                 GATE_OPEN (2s timeout)
                        ↓
                 GATE_CLOSING → PARKING_MONITOR
                                      ↓
                            (IR Detects Occupancy)
                                      ↓
                            ID_ASSIGNMENT → FLASH_ANIMATION
                                      ↓
                                  OCCUPIED
                                      ↓
                            (IR Detects Vacancy >1s)
                                      ↓
                            EXIT_DETECTED → BILLING
                                      ↓
                            TELEGRAM_SEND → IDLE
```

### Changing Refresh Rate

```python
DASHBOARD_REFRESH = 5  # Change to 5 seconds
```

## 📝 Code Structure

```
main.py
├── Configuration (lines 1-35)
├── WiFi Helper (lines 37-48)
├── Telegram API (lines 50-75)
├── LCD API Classes (lines 77-130)
├── Parking Logic Classes (lines 132-242)
│   ├── Slot
│   ├── Ticket
│   └── ParkingManager
├── Web Server & HTML Renderer (lines 244-380)
├── Hardware Setup & Control (lines 382-470)
├── Initialization (lines 472-493)
└── Main Loop (lines 495-end)
```


## 📚 Video Demonstration




---
