# Smart Delivery Box 📦🔒

An intelligent IoT-based package delivery system that automatically detects, secures, and notifies owners about package deliveries in real-time.

![Project Status](https://img.shields.io/badge/status-completed-success)
![Platform](https://img.shields.io/badge/platform-ESP32-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [System Architecture](#system-architecture)
- [Hardware Requirements](#hardware-requirements)
- [Software Requirements](#software-requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Operating Modes](#operating-modes)
- [API Reference](#api-reference)
- [Troubleshooting](#troubleshooting)
- [Future Improvements](#future-improvements)
- [Contributing](#contributing)
- [Authors](#authors)
- [License](#license)

## 🎯 Overview

The Smart Delivery Box addresses the growing problem of package theft and missed deliveries by providing an automated, secure storage solution. The system uses ultrasonic sensors to detect package placement, automatically locks the box, and sends instant notifications to the owner via Telegram Bot.

### Problem Statement

- Package theft affects millions of households annually
- Traditional mailboxes leave packages vulnerable
- No real-time notification or tracking of deliveries
- Weather damage and security concerns

### Solution

An IoT-enabled delivery box that combines:
- Real-time monitoring and notifications
- Automatic locking mechanism
- Remote control via Telegram/Web dashboard
- Comprehensive data logging and visualization

## ✨ Features

- **Automatic Package Detection**: Ultrasonic sensors detect when packages are placed inside
- **Smart Locking System**: Servo motor automatically locks the box after delivery
- **Instant Notifications**: Real-time alerts via Telegram Bot with timestamp
- **Remote Control**: Unlock and manage the box from anywhere via Telegram or web dashboard
- **Dual Package Support**: Can hold up to 2 packages with individual tracking
- **Theft Detection**: Buzzer alarm triggers if packages are removed without authorization
- **Event Logging**: Complete delivery history with timestamps stored in InfluxDB
- **Data Visualization**: Grafana dashboard for monitoring and analytics
- **LCD Status Display**: Visual feedback on the device itself
- **Audio Alerts**: Buzzer notifications for various events

## 🏗️ System Architecture

```
ESP32 (Sensors/Actuators)
    |
    └─ MQTT
        ↓
    Node-RED
        ├─ InfluxDB (Store Data)
        │     ↓
        │   Grafana (Visualize)
        │
        └─ Telegram (Notifications)
```

### Communication Flow

```
Telegram Bot
    ↓
Node-RED (receives /open command)
    ↓
MQTT publish to "smartbox/command" with "open"
    ↓
ESP32 receives and opens door
    ↓
ESP32 publishes status to MQTT
    ↓
Node-RED sends "✅ Door opened" to Telegram
```

## 🛠️ Hardware Requirements

| Component | Specification | Purpose |
|-----------|--------------|---------|
| **ESP32 Dev Board** | Dual-core 240MHz, 520KB SRAM, WiFi 802.11 b/g/n | Main controller |
| **HC-SR04 Ultrasonic Sensor (x2)** | Range: 2-400cm, 5V | Package detection |
| **IR Obstacle Sensor** | Detection: 2-30cm adjustable | Door status monitoring |
| **SG90 Servo Motor (x2)** | Torque: 1.8 kg·cm, 4.8-6V | Lock & door control |
| **16x2 LCD with I2C** | 5V, I2C interface | Status display |
| **Active Buzzer** | 12V | Audio alerts |
| **Relay Module** | 12V control | Buzzer power management |
| **Power Supply** | 12V 2A AC/DC adapter | System power |

### Pin Configuration

```cpp
// Ultrasonic Sensors
#define TRIG_PIN_1 12
#define ECHO_PIN_1 14
#define TRIG_PIN_2 25
#define ECHO_PIN_2 33

// IR Sensor
#define IR_SENSOR_PIN 27

// Servo Motors
#define LOCK_SERVO_PIN 13
#define DOOR_SERVO_PIN 15

// LCD (I2C)
#define SDA_PIN 21
#define SCL_PIN 22

// Buzzer & Button
#define BUZZER_PIN 26
#define BUTTON_PIN 4
```

## 💻 Software Requirements

### ESP32 Dependencies

Install these libraries via Arduino IDE Library Manager:

```cpp
- WiFi.h (built-in)
- PubSubClient.h (MQTT client)
- ESP32Servo.h (Servo control)
- LiquidCrystal_I2C.h (LCD display)
- time.h (NTP time sync)
```

### Cloud Services

- **MQTT Broker**: HiveMQ Cloud or Mosquitto
- **Node-RED**: v3.0+ for flow automation
- **InfluxDB**: v2.0+ for time-series data
- **Grafana**: v9.0+ for visualization
- **Telegram Bot**: Create via @BotFather

### Development Tools

- Arduino IDE 2.0+ or PlatformIO
- Node-RED (local or cloud instance)
- InfluxDB Cloud or self-hosted
- Grafana Cloud or self-hosted

## 📥 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/smart-delivery-box.git
cd smart-delivery-box
```

### 2. ESP32 Setup

1. Install Arduino IDE and ESP32 board support
2. Install required libraries
3. Open `smart_delivery_box.ino`
4. Update configuration in `config.h`:

```cpp
// WiFi Configuration
#define WIFI_SSID "your_wifi_ssid"
#define WIFI_PASSWORD "your_wifi_password"

// MQTT Configuration
#define MQTT_SERVER "your_mqtt_broker"
#define MQTT_PORT 1883
#define MQTT_USER "your_username"
#define MQTT_PASSWORD "your_password"

// Telegram Configuration
#define BOT_TOKEN "your_telegram_bot_token"
```

5. Upload to ESP32

### 3. Node-RED Setup

1. Install Node-RED:
```bash
npm install -g node-red
```

2. Install required nodes:
```bash
cd ~/.node-red
npm install node-red-contrib-telegrambot
npm install node-red-contrib-influxdb
```

3. Import the flow:
   - Copy content from `flows/nodered-flow.json`
   - Open Node-RED dashboard (http://localhost:1880)
   - Import via Menu → Import → Clipboard

4. Configure nodes:
   - Update MQTT broker settings
   - Add Telegram bot token
   - Configure InfluxDB connection

### 4. InfluxDB Setup

1. Create account at InfluxDB Cloud or install locally
2. Create organization and bucket named `smartbox`
3. Generate API token
4. Update Node-RED InfluxDB nodes with credentials

### 5. Grafana Setup

1. Access Grafana (http://localhost:3000)
2. Add InfluxDB as data source
3. Import dashboard from `dashboards/grafana-dashboard.json`
4. Configure refresh intervals and alerts

### 6. Telegram Bot Setup

1. Create bot via [@BotFather](https://t.me/BotFather)
2. Save the bot token
3. Start conversation with your bot
4. Use `/start` to initialize

## ⚙️ Configuration

### MQTT Topics

```
smartbox/command    - Remote commands (subscribe)
smartbox/status     - Box status updates (publish)
smartbox/event      - Delivery events (publish)
smartbox/package    - Package tracking (publish)
```

### Telegram Commands

```
/start      - Initialize bot and get chat ID
/status     - Get current box status
/open       - Open the door
/close      - Close the door
/lock       - Lock the box
/unlock     - Unlock the box
/retrieve   - Enter retrieval mode
```

### Sensor Calibration

Adjust these thresholds in code based on your box dimensions:

```cpp
#define PACKAGE_THRESHOLD 10  // cm - distance indicating package present
#define DOOR_CLOSE_DELAY 10000  // ms - auto-close after 10 seconds
#define THEFT_CHECK_SAMPLES 5  // confirmations before theft alert
```

## 🚀 Usage

### Normal Delivery Workflow

1. **System Idle** (Box Empty)
   - Door: Closed
   - Lock: Unlocked
   - LCD: "BOX EMPTY"

2. **First Package Delivery**
   - Delivery person presses button or uses remote open
   - Places package inside (Ultrasonic 1 detects)
   - Door auto-closes after 10 seconds
   - System auto-locks
   - Owner receives Telegram notification

3. **Second Package Delivery**
   - Owner must unlock remotely first (box is locked)
   - System checks Package #1 is still present (theft detection)
   - Delivery person places Package #2
   - Door auto-closes and locks
   - Owner receives notification

4. **Package Retrieval**
   - Owner sends `/retrieve` command
   - Box unlocks and opens
   - Owner removes packages
   - System detects empty box and returns to Idle

### Theft Detection

If a package is removed during unauthorized access:
1. Buzzer sounds alarm
2. Instant Telegram alert sent
3. Door immediately closes and locks
4. Event logged with timestamp
5. System remains in alert state

## 📊 API Reference

### MQTT Command Format

**Unlock Box:**
```json
{
  "topic": "smartbox/command",
  "payload": "unlock"
}
```

**Check Status:**
```json
{
  "topic": "smartbox/status",
  "response": {
    "locked": false,
    "door_open": true,
    "package_count": 1,
    "packages": [
      {
        "id": "PKG001",
        "timestamp": "2025-12-09T10:30:00Z"
      }
    ]
  }
}
```

### Web Dashboard Endpoints

```javascript
// Status Endpoint
GET /api/status
Response: {
  "locked": boolean,
  "door_open": boolean,
  "package_count": integer,
  "packages": array
}

// Command Endpoint
POST /api/command
Body: {
  "action": "unlock" | "lock" | "open" | "close" | "retrieve"
}
```

## 🔧 Troubleshooting

### Common Issues

**WiFi Connection Fails**
```
- Check SSID and password
- Ensure ESP32 is within WiFi range
- Verify 2.4GHz network (ESP32 doesn't support 5GHz)
- Check router firewall settings
```

**MQTT Not Connecting**
```
- Verify broker address and port
- Check username/password credentials
- Ensure QoS level is supported (recommend QoS 1)
- Test broker with MQTT Explorer tool
```

**Servo Jitters or Doesn't Move**
```
- Check power supply (separate 5V recommended)
- Add 100µF capacitor across servo power pins
- Reduce servo speed in code
- Verify GPIO pin connections
```

**False Package Detections**
```
- Adjust PACKAGE_THRESHOLD value
- Increase THEFT_CHECK_SAMPLES for more confirmation
- Check sensor mounting and alignment
- Add delay between readings
```

**Telegram Bot Not Responding**
```
- Verify bot token is correct
- Check Node-RED flow is deployed
- Ensure MQTT broker is running
- Test bot directly via @BotFather
```

### Debug Mode

Enable verbose logging:

```cpp
#define DEBUG_MODE true

#if DEBUG_MODE
  Serial.println("Debug: " + message);
#endif
```

## 🔮 Future Improvements

### Planned Features

- [ ] **ESP32-CAM Integration**: Capture delivery photos
- [ ] **OTP Access System**: Time-limited passcodes for delivery personnel
- [ ] **Multi-Compartment Support**: Individual storage for multiple users
- [ ] **Solar Power Option**: Off-grid operation capability
- [ ] **GPS Tracking**: Mobile/rental box versions
- [ ] **Voice Assistant Integration**: Alexa/Google Home support
- [ ] **Mobile App**: Native iOS/Android application
- [ ] **Weight Sensors**: Additional package verification
- [ ] **Temperature Monitoring**: For temperature-sensitive deliveries
- [ ] **Battery Backup**: Continue operation during power outages

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Code Style

- Follow Arduino code conventions
- Use meaningful variable names
- Comment complex logic
- Test thoroughly before submitting

## 👥 Authors

**CHENG Mengsrun** - *Lead Developer*
**LIM Bunheng** - *Hardware Engineer*

**Course**: ICT 360 - Introduction to Internet of Things  
**Institution**: American University of Phnom Penh  
**Instructor**: Theara SENG  
**Date**: December 9, 2025

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- American University of Phnom Penh for providing resources
- Instructor Theara SENG for guidance and support
- ESP32 community for extensive documentation
- Node-RED community for automation examples

## 📞 Contact

For questions or support:
- Open an issue in this repository
- Email: [your.email@example.com]
- Project Link: [https://github.com/yourusername/smart-delivery-box](https://github.com/yourusername/smart-delivery-box)

---

**Made with ❤️ by Group 8 - ICT 360 Final Project**
