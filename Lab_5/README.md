# LAB 5 - Mobile App DC Motor Control with Grafana Dashboard
# ESP32 Motor Control with MQTT + Node-RED + InfluxDB
# Group 8
## 1. Overview

In this lab, students will design a mobile application (using MIT App Inventor) to remotely control a DC motor via an ESP32 (MicroPython) web server. The ESP32 will expose HTTP endpoints (/forward, /backward, /stop, /speed), while the mobile app will send commands over Wi-Fi to control direction and speed. All control actions and speed updates will be recorded to an IoT dashboard (InfluxDB + Grafana) for real-time monitoring and analysis.


## 2. Equipment
- ESP32 Dev Board (MicroPython flashed)
- L298N motor driver
- DC motor + power supply (7–12 V)
- Jumper wires 
- Laptop with Thonny IDE
- Mobile phone with MIT App Inventor installed
- Wi-Fi access point
- Grafana Cloud account and local InfluxDB server


## 3. Wiring Diagram

### Wires Diagram 
![diagram](https://github.com/srun21/IOT-section-1-Group-8/blob/main/Lab_5/images/diagram.jpg)


## 4. Tasks & Checkpoints

### Task 1 – ESP32 Web Server (15 pts)

#### Web Url
``` http://172.20.10.5/ ```
```
API Endpoints:
   • http://172.20.10.5/forward
   • http://172.20.10.5/backward
   • http://172.20.10.5/stop
   • http://172.20.10.5/speed?value=50
   • http://172.20.10.5/status
```

![web_server](https://github.com/srun21/IOT-section-1-Group-8/blob/main/Lab_5/images/web_server.png)

```  Code ```
```html
HOME_HTML = """<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ESP32 Motor Control</title>
<style>
...
</style>
</head>
<body>
<div class="container">
  <h3>🚗 ESP32 Motor Control</h3>
  
  <button class="forward" onclick="sendCmd('/forward')">⬆️ FORWARD</button>
  <button class="stop" onclick="sendCmd('/stop')">⏹️ STOP</button>
  <button class="backward" onclick="sendCmd('/backward')">⬇️ BACKWARD</button>
  
  <div style="margin-top: 20px;">
    <label style="font-weight: bold;">⚡ Speed Control</label>
    <div class="speed-display" id="speedval">70%</div>
    <input id="spd" type="range" min="0" max="100" value="70"
      oninput="updateSpeed(this.value)">
  </div>
  
  <div class="status" id="status">Status: Ready</div>
</div>

<script>
function updateSpeed(val) {
  document.getElementById('speedval').innerText = val + '%';
  sendCmd('/speed?value=' + val);
}

function sendCmd(path) {
  document.getElementById('status').innerText = 'Sending...';
  fetch(path)
    .then(r => r.text())
    .then(msg => {
      document.getElementById('status').innerText = 'Status: ' + msg;
    })
    .catch(e => {
      document.getElementById('status').innerText = 'Error: ' + e;
    });
}
</script>
</body>
</html>
"""
```


### Task 2 – Mobile App Design (20 pts)
- Build an MIT App Inventor interface with:
  - Buttons: Forward, Backward, Stop
  - Slider: Speed (0–100 %)
  - Label for status.
- Buttons send requests to http://<ESP32_IP>/forward?speed=NN etc.
  
 ``` App Design ```
 
  ![MIT Invention App](https://github.com/srun21/IOT-section-1-Group-8/blob/main/Lab_5/images/mit_app_1.jpg)
    
``` Code Block ```

  ![MIT Code Block](https://github.com/srun21/IOT-section-1-Group-8/blob/main/Lab_5/images/mit_app_2.jpg)

### Task 3 – Data Logging to InfluxDB (25 pts)

``` mqtt -> node_red -> influxdb ```

#### mqtt broker
```
MQTT Broker: 172.20.10.3:1883
MQTT Topic: motor/control
```

#### Node-Red Url
``` http://127.0.0.1:1880/```

#### Influx Node
- ``` {"timestamp": "<ISO_time>", "action": "forward", "speed": 70}```
- Verify the data appears in InfluxDB bucket/table.

![node_red](https://github.com/srun21/IOT-section-1-Group-8/blob/main/Lab_5/images/node_red_1.jpg)

![node_red and terminal](https://github.com/srun21/IOT-section-1-Group-8/blob/main/Lab_5/images/node_red_2.jpg)


### Task 4 – Grafana Dashboard (20 pts)

- Configure Grafana to visualize:
  - Motor speed vs time
  - Last command direction
  - Table of events with timestamps

#### Motor speed vs time query
  ```SELECT speed FROM motor_control WHERE $timeFilter ```

#### Last command direction query
  ``` SELECT action FROM motor_control ORDER BY time DESC LIMIT 1 ``` 

#### Table of events with timestamps
  ``` SELECT time, action, speed, device FROM motor_control ORDER BY time DESC LIMIT 20 ```

![Grafana DashBoard](https://github.com/srun21/IOT-section-1-Group-8/blob/main/Lab_5/images/grafana.jpg)
![Grafana Video demo](https://github.com/srun21/IOT-section-1-Group-8/blob/main/Lab_5/images/grafana_video.mov.zip)

### Task 5 – Reliability & Analysis (10 pts)

- Add Wi-Fi auto-reconnect logic.
``` # Check WiFi every 30 seconds
if time.time() - last_check > 30:
    if not sta.isconnected():
        print("⚠️  WiFi disconnected, reconnecting...")
        sta.connect(WIFI_SSID, WIFI_PASSWORD)
        time.sleep(5)
    last_check = time.time()
```
 
- Handle bad HTTP requests gracefully (print error and continue).
``` except OSError as e:
    if getattr(e, "errno", None) != 116:
        print("⚠️  Socket error:", e)
```

- Discuss response delay and accuracy issues.


### Project Demo
#### ** Full Project Video Demo **
![Video Demo](https://github.com/srun21/IOT-section-1-Group-8/blob/main/Lab_5/images/Lab_5_demo.mp4.zip)
