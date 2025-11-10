# ESP32 → MQTT → Node-RED → InfluxDB → Grafana Dashboard

This project demonstrates a complete IoT data pipeline using an ESP32 running MicroPython, sending random sensor values via MQTT to Node-RED, which stores the data in InfluxDB and visualizes it in Grafana.

# Here is the program flow:

### 1. BMP280 and ESP32 (Data Collection) 

**The BMP 280 sensor read the data every 5s and control by the ESP32 board.**
1. BMP280 reads: Temperature, Pressure, Altitute
2. ESP32 connect to wifi
3. The code set to sent data every 5s
4. JSON payload ```{"temperature": 23.4, "pressure": 1010.5, "altitude": 22.6}```
   
### Code for Thonny
```python
import network, time, json
from umqtt.simple import MQTTClient
from machine import Pin, I2C
import bmp280

# WiFi Configuration
SSID = "Robotic WIFI"
PASSWORD = "rbtWIFI@2025"

# MQTT Configuration
BROKER = "test.mosquitto.org"
PORT = 1883
CLIENT_ID = b"esp32_bmp280_1"
TOPIC = b"/aupp/esp32/mqttG8"
KEEPALIVE = 30

# I2C Configuration for BMP280
# Adjust pins based on your ESP32 wiring (common pins: SDA=21, SCL=22)
i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)

def wifi_connect():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to WiFi...")
        wlan.connect(SSID, PASSWORD)
        t0 = time.ticks_ms()
        while not wlan.isconnected():
            if time.ticks_diff(time.ticks_ms(), t0) > 20000:
                raise RuntimeError("Wi-Fi connect timeout")
            time.sleep(0.3)
    print("WiFi OK:", wlan.ifconfig())
    return wlan

def make_client():
    return MQTTClient(client_id=CLIENT_ID, server=BROKER, port=PORT, keepalive=KEEPALIVE)

def connect_mqtt(c):
    time.sleep(0.5)
    c.connect()
    print("MQTT connected")

def init_bmp280():
    try:
        sensor = bmp280.BMP280(i2c)
        print("BMP280 sensor initialized")
        return sensor
    except Exception as e:
        print("BMP280 init error:", e)
        return None

def read_bmp280(sensor):
    try:
        # Read temperature and pressure from BMP280
        temperature = sensor.temperature
        pressure = sensor.pressure
        
        # Calculate altitude (based on standard atmospheric pressure)
        # Altitude formula: h = 44330 * (1 - (P/P0)^(1/5.255))
        pressure_hpa = pressure / 100
        altitude = 44330 * (1.0 - pow(pressure_hpa / 1013.25, 0.1903))
        
        return {
            "temperature": round(temperature, 2),
            "pressure": round(pressure_hpa, 2),
            "altitude": round(altitude, 2)
        }
    except Exception as e:
        print("Read error:", e)
        return None

def main():
    wifi_connect()
    sensor = init_bmp280()
    
    if sensor is None:
        print("Cannot proceed without sensor")
        return
    
    client = make_client()
    
    while True:
        try:
            connect_mqtt(client)
            while True:
                # Read sensor data
                data = read_bmp280(sensor)
                
                if data:
                    # Convert to JSON string
                    msg = json.dumps(data)
                    client.publish(TOPIC, msg)
                    print("Sent:", msg)
                else:
                    print("Failed to read sensor")
                
                time.sleep(5)
                
        except OSError as e:
            print("MQTT error:", e)
            try:
                client.close()
            except:
                pass
            print("Retrying MQTT in 3s...")
            time.sleep(3)

main()
```
### Thonny Terminal:
![thonny terminal](https://github.com/srun21/IOT-section-1-Group-8/blob/Lab-1/Lab_4/images/thonny_terminal.png)

### 2. MQTT broker (Message Transport)

1. MQTT act as message hub between ESP32 and Node-Red
2. Mosquito running on ```localhost:1883```
3. ESP32 sent JSON to topic: ```/aupp/esp32/mqtt8```
   
### 3. Node-Red (Data Processing)  

**Start node-red and browsing to http://127.0.0.1:1880**
1. MQTT in Node-Red connect to  ```/aupp/esp32/mqtt8```
2. Node-Red receive JSON
3. On function 1
   ```
     {
    temperature: 23.4,
    pressure: 1010.5,
    altitude: 22.6}
**The Flow:** 
- Sends to two outputs:
  - Output 1 → InfluxDB (storage)
  - Output 2 → Debug (monitoring)

![Node-Red](https://github.com/srun21/IOT-section-1-Group-8/blob/Lab-1/Lab_4/images/node-red.png)

### 4. InfluxDB (Database)
- Database: `aupp_lab`
- Measurement: `sensor_data`
- Stores three fields:
  - `temperature` field
  - `pressure` field
  - `altitude` field
- Each record has a timestamp
- Running on `localhost:8086`

### 5. Grafana (Dashboard)

- Connects to InfluxDB data source
- Running on `localhost:3000`
- **Three panels:**
  1. *Temperature Panel*
     - Query: `SELECT field(temperature) FROM sensor_data`
     - Unit: Celsius (°C)  
  2. *Pressure Panel*
     - Query: `SELECT field(pressure) FROM sensor_data`
     - Unit: Hectopascals (hPa)
  3. *Altitude Panel*
     - Query: `SELECT field(altitude) FROM sensor_data`
     - Unit: Meters (m)

![Grafana Dashboard](https://github.com/srun21/IOT-section-1-Group-8/blob/Lab-1/Lab_4/images/grafana.png)

### Final Program Flow

- `BMP280 Sensor`
  - `    (I2C)`
- `ESP32 (reads every 5s)`
  - `    (WiFi)`
- `MQTT Broker (Mosquitto)`
  - `    (MQTT protocol)`
- `Node-RED (processes JSON)`
  - `    (HTTP API)`
- `InfluxDB (stores time-series data)`
  - `    (InfluxQL queries)`
- `Grafana (displays 3 graphs) `

** Demo Video:
![Short Demo](https://github.com/srun21/IOT-section-1-Group-8/blob/Lab-1/Lab_4/images/lab4_recording.mov)
