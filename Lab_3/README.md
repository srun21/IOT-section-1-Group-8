# 📊 ESP32 Environmental Monitoring with BMP280

**A complete guide to building an weather dashboard using ESP32, BMP280 sensor, and cloud integration**

![Project Banner](<img width="1042" height="531" alt="image" src="https://github.com/user-attachments/assets/0d170740-05c6-4c18-a603-ca570d2b4fe1" />
)


## 🎯 Introduction

This laboratory project demonstrates how to create a real-time environmental monitoring system using the **BMP280 sensor** and **ESP32 microcontroller**. You'll learn to measure atmospheric pressure, temperature, and altitude, then transmit this data to cloud platforms for visualization and analysis.

### What You'll Learn
- Interface BMP280 sensor with ESP32 using I²C protocol
- Implement MQTT communication for IoT data transmission
- Integrate sensor data with ThingsBoard cloud platform
- Build real-time monitoring dashboards

### Project Architecture
```
[BMP280 Sensor] → [ESP32] → [Wi-Fi] → [MQTT Broker] → [ThingsBoard Cloud]
```

---

## 🔧 Hardware Setup

### Components Required

| Component | Specification | Quantity |
|-----------|--------------|----------|
| ESP32 Development Board | Any variant with Wi-Fi | 1 |
| BMP280 Sensor Module | I²C interface | 1 |
| Jumper Wires | Male-to-Female | 4 |
| USB Cable | Micro-USB or USB-C | 1 |
| Breadboard (Optional) | For prototyping | 1 |

### 🔌 Wiring Diagram

Connect the BMP280 to your ESP32 as follows:

| BMP280 | ESP32 | Description |
|--------|-------|-------------|
| VCC | 3.3V | Power supply |
| GND | GND | Ground connection |
| SCL | GPIO 22 | I²C Clock line |
| SDA | GPIO 21 | I²C Data line |

> **⚡ Important:** Always use 3.3V for VCC. While some modules have onboard regulators that accept 5V, connecting 5V directly to a bare BMP280 chip will damage it.

---

## Getting Started

### Software Prerequisites

1. **Thonny IDE** - [Download here](https://thonny.org/)
2. **MicroPython Firmware** - Must be flashed to ESP32
3. **BMP280 Library** - `bmp280.py` driver file
4. **MQTT Library** - `umqtt.simple` (built into MicroPython)

### Installation Steps

**Step 1: Prepare Your ESP32**
```bash
# Flash MicroPython firmware using esptool
esptool.py --port /dev/ttyUSB0 erase_flash
esptool.py --port /dev/ttyUSB0 write_flash -z 0x1000 esp32-micropython.bin
```

**Step 2: Upload Required Libraries**
- Download `bmp280.py` from the Lab3 repository
- Open Thonny IDE and connect to your ESP32
- Save `bmp280.py` to the device's root directory

**Step 3: Verify Connection**
```python
from machine import Pin, I2C

i2c = I2C(0, scl=Pin(22), sda=Pin(21))
print(i2c.scan())  # Should show [0x76] or [0x77]
```

---

## 🧪 Project Components


---

## 💻 Implementation Guide

### Part 1: Basic Sensor Reading

This example reads temperature, pressure, and altitude from the BMP280 every 2 seconds.

```python
from machine import Pin, I2C
from bmp280 import BMP280
import time

# Initialize I²C bus
i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)

# Initialize BMP280 sensor
bmp = BMP280(i2c, addr=0x76)

print("BMP280 Environmental Monitor")
print("=" * 40)

while True:
    # Read sensor values
    temp = bmp.temperature
    pressure = bmp.pressure / 100  # Convert Pa to hPa
    altitude = bmp.altitude
    
    # Display readings
    print(f"Temperature: {temp:.2f} °C")
    print(f"Pressure:    {pressure:.2f} hPa")
    print(f"Altitude:    {altitude:.2f} m")
    print("-" * 40)
    
    time.sleep(2)
```

**Expected Output:**
```
Temperature: 25.34 °C
Pressure:    1013.25 hPa
Altitude:    120.45 m
```



```

### Publishing Sensor Data via MQTT

This example publishes BMP280 data to a public MQTT broker.

```python
import network
import time
import json
from machine import Pin, I2C
from bmp280 import BMP280
from umqtt.simple import MQTTClient

# ========== Configuration ==========
WIFI_SSID = "YourNetworkName"
WIFI_PASS = "YourPassword"

MQTT_BROKER = "test.mosquitto.org"
MQTT_PORT = 1883
CLIENT_ID = b"esp32_bmp280_sensor"
TOPIC_TEMP = b"mylab/sensor/temperature"
TOPIC_PRESSURE = b"mylab/sensor/pressure"
TOPIC_ALTITUDE = b"mylab/sensor/altitude"

# ========== Wi-Fi Connection ==========
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    if wlan.isconnected():
        print("Already connected to Wi-Fi")
        return
    
    print(f"Connecting to {WIFI_SSID}...")
    wlan.connect(WIFI_SSID, WIFI_PASS)
    
    timeout = 20
    while not wlan.isconnected() and timeout > 0:
        time.sleep(1)
        timeout -= 1
        print(".", end="")
    
    if wlan.isconnected():
        print("\n✓ Wi-Fi Connected!")
        print(f"IP Address: {wlan.ifconfig()[0]}")
    else:
        raise Exception("Failed to connect to Wi-Fi")

# ========== Main Program ==========
def main():
    # Connect to Wi-Fi
    connect_wifi()
    
    # Initialize sensor
    i2c = I2C(0, scl=Pin(22), sda=Pin(21))
    bmp = BMP280(i2c, addr=0x76)
    print("✓ BMP280 sensor initialized")
    
    # Connect to MQTT broker
    print(f"Connecting to MQTT broker: {MQTT_BROKER}")
    client = MQTTClient(CLIENT_ID, MQTT_BROKER, port=MQTT_PORT, keepalive=60)
    client.connect()
    print("✓ Connected to MQTT broker\n")
    
    print("Publishing sensor data... (Ctrl+C to stop)")
    
    try:
        while True:
            # Read sensor
            temp = bmp.temperature
            pressure = bmp.pressure / 100
            altitude = bmp.altitude
            
            # Create JSON payload
            payload = json.dumps({
                "temperature": round(temp, 2),
                "pressure": round(pressure, 2),
                "altitude": round(altitude, 2),
                "timestamp": time.time()
            })
            
            # Publish to MQTT
            client.publish(TOPIC_TEMP, str(round(temp, 2)))
            client.publish(TOPIC_PRESSURE, str(round(pressure, 2)))
            client.publish(TOPIC_ALTITUDE, str(round(altitude, 2)))
            
            print(f" Published: Temp={temp:.2f}°C, Pressure={pressure:.2f}hPa, Alt={altitude:.2f}m")
            
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\n\nDisconnecting...")
        client.disconnect()
        print("✓ Disconnected from MQTT broker")

if __name__ == "__main__":
    main()
```

### Testing with MQTT Explorer

1. **Download MQTT Explorer**  
   Get it from: [MQTT Explorer Releases](https://github.com/thomasnordquist/MQTT-Explorer/releases)

2. **Configure Connection**
   - Host: `test.mosquitto.org`
   - Port: `1883`
   - Protocol: `mqtt://`

3. **Subscribe to Topics**
   - Navigate to your topic path (e.g., `aupp/lab/`)
   - View real-time data updates

![MQTT Explorer Screenshot](image/mqtt.png)

---

## ☁️ Cloud Integration

### ThingsBoard Platform Overview

**ThingsBoard** is an open-source IoT platform that provides device management, data collection, processing, visualization, and analytics.

### Setting Up ThingsBoard

**Step 1: Create Account**
- Visit [ThingsBoard Cloud](https://thingsboard.cloud/)
- Sign up for a free account

**Step 2: Add Device**
1. Navigate to **Devices** in the left menu
2. Click the **+** button to add a new device
3. Name your device (e.g., "ESP32_BMP280")
4. Copy the **Access Token** (you'll need this!)

**Step 3: Configure ESP32**

```python
import network
import time
import json
from machine import Pin, I2C
from bmp280 import BMP280
from umqtt.simple import MQTTClient

# ========== Configuration ==========
WIFI_SSID = "YourNetwork"
WIFI_PASS = "YourPassword"

# ThingsBoard settings
TB_HOST = "mqtt.thingsboard.cloud"
TB_PORT = 1883
TB_TOKEN = b"YOUR_DEVICE_ACCESS_TOKEN"  # Replace with your token!
TB_TOPIC = b"v1/devices/me/telemetry"

# ========== Wi-Fi Connection ==========
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    if not wlan.isconnected():
        print("Connecting to Wi-Fi...")
        wlan.connect(WIFI_SSID, WIFI_PASS)
        
        start = time.ticks_ms()
        while not wlan.isconnected():
            if time.ticks_diff(time.ticks_ms(), start) > 15000:
                raise RuntimeError("Wi-Fi connection timeout")
            time.sleep(0.5)
    
    print(f"✓ Wi-Fi Connected: {wlan.ifconfig()[0]}")

# ========== Main Program ==========
def main():
    # Connect Wi-Fi
    connect_wifi()
    
    # Initialize BMP280
    i2c = I2C(0, scl=Pin(22), sda=Pin(21))
    bmp = BMP280(i2c, addr=0x76)
    print("✓ BMP280 initialized")
    
    # Connect to ThingsBoard
    print(f"Connecting to ThingsBoard: {TB_HOST}")
    client = MQTTClient(
        client_id=b"esp32_tb_client",
        server=TB_HOST,
        port=TB_PORT,
        user=TB_TOKEN,  # Token is used as username
        password=b"",   # Password is empty
        keepalive=30
    )
    client.connect()
    print("✓ Connected to ThingsBoard\n")
    
    print("Streaming data to ThingsBoard...")
    
    try:
        while True:
            # Read sensor
            temperature = bmp.temperature
            pressure = bmp.pressure / 100
            altitude = bmp.altitude
            
            # Create telemetry payload
            telemetry = {
                "temperature": round(temperature, 2),
                "pressure": round(pressure, 2),
                "altitude": round(altitude, 2)
            }
            
            # Publish to ThingsBoard
            payload = json.dumps(telemetry).encode()
            client.publish(TB_TOPIC, payload)
            
            print(f"Sent: {telemetry}")
            
            time.sleep(10)  # Send every 10 seconds
            
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        client.disconnect()
        print("✓ Disconnected from ThingsBoard")

if __name__ == "__main__":
    main()
```

### Creating a Dashboard

**Step 1: View Latest Telemetry**
- Go to your device in ThingsBoard
- Click on **Latest Telemetry** tab
- Verify data is being received

**Step 2: Create Dashboard**
1. Navigate to **Dashboards** → Click **+**
2. Add a new dashboard (e.g., "Weather Station")
3. Click **Edit mode** (pencil icon)

**Step 3: Add Widgets**
- **Temperature Gauge:**
  - Widget: Digital gauge
  - Datasource: Your device → temperature
  - Units: °C
  - Color thresholds: Green (20-25), Yellow (25-30), Red (>30)

- **Pressure Chart:**
  - Widget: Time-series line chart
  - Datasource: Your device → pressure
  - Time window: Last hour

- **Altitude Display:**
  - Widget: Cards widget
  - Datasource: Your device → altitude
  - Units: meters



## 📚 Additional Resources

### Documentation
- [BMP280 Datasheet](https://www.bosch-sensortec.com/products/environmental-sensors/pressure-sensors/bmp280/)
- [MicroPython Documentation](https://docs.micropython.org/)
- [ThingsBoard Documentation](https://thingsboard.io/docs/)
- [MQTT Protocol Specification](http://mqtt.org/)

### Tools
- [Thonny IDE](https://thonny.org/)
- [MQTT Explorer](https://mqtt-explorer.com/)
- [ESP32 Flasher Tool](https://github.com/espressif/esptool)


## Video demo



---
