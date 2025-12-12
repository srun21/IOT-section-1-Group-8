# ESP32 IoT System with Web Interface and LCD Display

A MicroPython-based IoT system for ESP32 that integrates sensor monitoring, LED control, and LCD display functionality through a user-friendly web interface.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Hardware Requirements](#hardware-requirements)
- [Wiring Diagram](#wiring-diagram)
- [Software Setup](#software-setup)
- [Wi-Fi Configuration](#wi-fi-configuration)
- [Running the Server](#running-the-server)
- [Usage Instructions](#usage-instructions)
- [Project Structure](#project-structure)

## Overview

This project demonstrates an event-driven IoT system that bridges web-based controls with physical hardware. Users can control an LED, monitor environmental data from sensors, and send custom messages to an LCD display—all through a web browser interface.

## Features

-  **Web-Based Control Panel**: Intuitive HTML interface for device interaction
-  **LED Control**: Toggle LED on/off from the web interface
-  **Environmental Monitoring**: Real-time temperature and humidity readings from DHT11 sensor
-  **Distance Measurement**: Ultrasonic distance sensing with HC-SR04
-  **LCD Display Integration**: 16×2 I²C LCD for displaying sensor data and custom messages
-  **Custom Messaging**: Send text from web interface directly to LCD
-  **Selective Display**: Choose which sensor data to show on LCD via web buttons

## Hardware Requirements

| Component | Quantity | Notes |
|-----------|----------|-------|
| ESP32 Development Board | 1 | With MicroPython firmware |
| DHT11 Sensor | 1 | Temperature/Humidity |
| HC-SR04 Ultrasonic Sensor | 1 | Distance measurement |
| 16×2 LCD with I²C Backpack | 1 | I²C address 0x27 or 0x3F |
| LED | 1 | Any color |
| Resistor 220Ω-330Ω | 1 | For LED current limiting |
| Breadboard | 1 | Standard size |
| Jumper Wires | ~20 | Male-to-male |
| USB Cable | 1 | For programming |

## Wiring Diagram
<img width="1134" height="584" alt="image" src="https://github.com/user-attachments/assets/f0c831af-d86f-48aa-b4ec-36393ffa2f0a" />

## Software Setup

### Prerequisites

- **Thonny IDE** (recommended) or any MicroPython-compatible IDE
- **MicroPython firmware** for ESP32 ([Download here](https://micropython.org/download/esp32/))
- **USB drivers** for ESP32 (CP210x or CH340 depending on your board)

### Step 1: Flash MicroPython Firmware

If MicroPython is not already installed on your ESP32:

```bash
# Install esptool
pip install esptool

# Erase flash
esptool.py --chip esp32 --port COM3 erase_flash

# Flash MicroPython (adjust port and firmware file)
esptool.py --chip esp32 --port COM3 --baud 460800 write_flash -z 0x1000 esp32-micropython.bin
```

**Note**: Replace `COM3` with your actual port (`COM3`, `COM4` on Windows or `/dev/ttyUSB0` on Linux/Mac).

### Step 2: Clone This Repository

```bash
git clone https://github.com/yourusername/esp32-iot-lab.git
cd esp32-iot-lab
```

### Step 3: Install Required Libraries

The project uses the following MicroPython libraries (included in the repo):

- `lcd_i2c.py` - I²C LCD driver
- `dht.py` - DHT sensor library (built-in to MicroPython)

### Step 4: Upload Files to ESP32

Using **Thonny IDE**:

1. Open Thonny and connect to ESP32
2. Select **Run** → **Configure interpreter**
3. Choose **MicroPython (ESP32)** and select your port
4. Upload the following files to the ESP32:
   - `main.py`
   - `boot.py`
   - `webserver.py`
   - `lcd_i2c.py`
   - `sensor_handler.py`
   - `index.html`

## Wi-Fi Configuration

### Method 1: Edit boot.py (Recommended)

1. Open `boot.py` in your editor
2. Replace the Wi-Fi credentials:

```python
# Wi-Fi Configuration
SSID = "YourWiFiName"          # Replace with your Wi-Fi network name
PASSWORD = "YourWiFiPassword"   # Replace with your Wi-Fi password
```

3. Save and upload to ESP32

**Important Notes**:
- ESP32 only supports **2.4GHz Wi-Fi** networks (not 5GHz)
- Ensure your network is not using enterprise authentication
- Hidden SSIDs may require additional configuration

## Running the Server

### Starting the Server

1. **Connect ESP32** to your computer via USB
2. **Open Thonny** or your serial monitor (115200 baud)
3. **Press the EN/RST button** on ESP32 or run `main.py`

### Expected Boot Sequence

You should see output similar to this:

```
====================================
ESP32 IoT System Starting...
====================================

[WIFI] Connecting to 'YourWiFiName'...
[WIFI] Connected!
[WIFI] IP Address: 192.168.1.100
[WIFI] Subnet Mask: 255.255.255.0
[WIFI] Gateway: 192.168.1.1

[LCD] Initializing I2C LCD...
[LCD] LCD Ready at address 0x27

[SENSORS] Initializing DHT11 on GPIO 15...
[SENSORS] Initializing HC-SR04 (TRIG=GPIO5, ECHO=GPIO18)...
[SENSORS] Sensors Ready

[LED] LED initialized on GPIO 2

[SERVER] Starting web server on port 80...
[SERVER] Server running at http://192.168.1.100
====================================
Ready! Open browser to access the interface
====================================
```

4. **Note the IP address** displayed (e.g., `192.168.1.100`)
5. **Open a web browser** on any device connected to the same Wi-Fi network
6. **Navigate to** `http://192.168.1.100` (use your actual IP)

### Server Status Indicators

- **LCD displays**: "System Ready" on Line 1, "IP: 192.168.1.100" on Line 2
- **Serial monitor**: Shows connection logs and request handling
- **LED**: May blink briefly during initialization

## Usage Instructions

### Accessing the Web Interface

1. Open your web browser (Chrome, Firefox, Safari, Edge)
2. Enter the ESP32's IP address in the URL bar
3. You should see the control panel interface


### Feature Guide

#### 1️⃣Task1 : LED Control

**Location**: Top section of web interface

**How to use**:
- Click **"Turn LED ON"** button → LED lights up, button changes to "Turn LED OFF"
- Click **"Turn LED OFF"** button → LED turns off, button changes to "Turn LED ON"

**What happens**:
- Web page sends GET request to `/led/on` or `/led/off`
- ESP32 sets GPIO 2 HIGH or LOW
- Button updates to reflect current state


#### 2️⃣ Task2 : Sensor Monitoring

**Location**: Middle section showing real-time readings

**Available readings**:
- **Temperature**: Displays current temperature in °C
- **Humidity**: Displays current humidity in %
- **Distance**: Displays ultrasonic distance in cm

**How it works**:
- Page automatically refreshes sensor data every 2 seconds
- Data fetched from `/sensors` endpoint
- No button press needed - automatic updates


#### 3️⃣ Task 3 : Display Distance and Temperature on LCD

**Location**: Sensor control buttons section

**How to use**:
1. Click **"Show Temperature on LCD"** button
2. LCD immediately displays:
   - Line 2: "23.5 C" (current reading)

**Example LCD output**:
```   
 Temp: 23.5 C          
```

#### Display Distance on LCD

**Location**: Sensor control buttons section

**How to use**:
1. Click **"Show Distance on LCD"** button
2. LCD immediately displays:
   - Line 1: "Distance:"  "15.3 cm"

**Example LCD output**:
```
Distance: 15.3 cm             
```


#### 4️⃣ Send Custom Message to LCD

**Location**: Bottom section with text input

**How to use**:
1. Click in the **text input box**
2. Type your message (up to 32 characters recommended)
3. Click **"Send to LCD"** button
4. Your message appears on the LCD

**Message formatting**:
- Messages longer than 16 characters automatically scroll 
- Special characters supported
- Clears previous content

**Example**:
- Input: `Hello IoT World!`
- LCD displays:
```
Hello IoT World!
                
```

- Input: `Temperature: 25C Humidity: 60%`
- LCD displays:
```
->Temperature: 25C Humidity: 60% ->   
```

![Custom Message Demo](docs/custom_message.gif)

### Complete Usage Workflow Example

1. **Start the system** → LCD shows "System Ready"
2. **Open web browser** → Navigate to ESP32 IP address
3. **Turn LED on** → Verify LED lights up
4. **Check sensor readings** → Observe temperature, humidity, distance
5. **Show temperature on LCD** → Click button, verify LCD display
6. **Show distance on LCD** → Click button, verify LCD display
7. **Send custom message** → Type "Hello World", click send, verify LCD
8. **Turn LED off** → Click button, verify LED turns off


## Project Structure

```
esp32-iot-lab/
├── README.md                      # This file
│
├── src/                           # Source code
│   ├── main.py                    # Main application entry point
│   ├── boot.py                    # Wi-Fi connection and boot config
│   ├── webserver.py               # Web server implementation
│   ├── lcd_i2c.py                 # I²C LCD display driver
│   ├── sensor_handler.py          # DHT11 and HC-SR04 handlers
│   └── index.html                 # Web interface HTML
│
├── docs/                          # Documentation and media
│   ├── wiring_diagram.png         # Circuit schematic
│   ├── hardware_front.jpg         # Hardware photo - front
│   ├── hardware_detail.jpg        # Hardware photo - connections
│   ├── web_interface.png          # Web UI screenshot
│   ├── led_control.gif            # LED control demo
│   ├── sensor_readings.png        # Sensor display screenshot
│   ├── lcd_sensors.jpg            # LCD showing sensor data
│   ├── custom_message.gif         # Custom message demo
│   ├── demo_video.mp4             # Full system demonstration
│   └── lab_report.pdf             # Complete lab documentation
│
└── examples/                      # Example configurations
    ├── config_template.py         # Configuration template
    └── test_sensors.py            # Sensor testing script
```


## Demo & Evidence

### 📹 Video Demonstration

Watch the complete system in action:

[![ESP32 IoT System Demo](https://drive.google.com/file/d/1rcY6AtEul9S9YsR2Ri9AhAiE6g-fEOQz/view?usp=sharing)


## Learning Outcomes

This project demonstrates:

- ✅ MicroPython web server implementation
- ✅ HTML-based hardware control interfaces
- ✅ Sensor data acquisition and processing
- ✅ I²C communication protocol
- ✅ Event-driven IoT system design
- ✅ Integration of multiple hardware components
- ✅ RESTful API design principles
- ✅ Network communication in embedded systems



---

**Course**: Introduction to IOT
**Institution**: American University of Phnom Penh
**Semester**: Fall 2025  
**Lab**: ESP32 Web Interface and LCD Integration

---
