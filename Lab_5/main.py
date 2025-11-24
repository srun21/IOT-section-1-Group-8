import network, socket, ure, time, ujson
from machine import Pin, PWM
from umqtt.simple import MQTTClient

# ======================== CONFIGURATION ========================
# WiFi Configuration
WIFI_SSID = "m1"
WIFI_PASSWORD = "44445555"

# MQTT Configuration (Your Mac's IP)
MQTT_BROKER = "172.20.10.3"  # Your Mac's IP
MQTT_PORT = 1883
MQTT_CLIENT_ID = "esp32_motor"
MQTT_TOPIC = "motor/control"

# ======================== MOTOR SETUP ========================
# L298N pins
IN1 = Pin(26, Pin.OUT)
IN2 = Pin(27, Pin.OUT)
ENA = PWM(Pin(25), freq=1000)
PWM_MAX = 1023
current_speed = 30
current_action = "stop"

# MQTT Client
mqtt_client = None

# ======================== WIFI CONNECTION ========================
def wifi_connect():
    """Connect to WiFi with auto-reconnect"""
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    
    if not sta.isconnected():
        print(f"Connecting to {WIFI_SSID}...")
        sta.connect(WIFI_SSID, WIFI_PASSWORD)
        
        for i in range(40):
            if sta.isconnected():
                break
            time.sleep(0.5)
            if i % 4 == 0:
                print(".", end="")
        print()
    
    if not sta.isconnected():
        raise RuntimeError("WiFi connect failed")
    
    ip = sta.ifconfig()[0]
    print(f"✓ WiFi Connected: {ip}")
    return ip, sta

# ======================== MQTT CONNECTION ========================
def mqtt_connect():
    """Connect to MQTT broker"""
    global mqtt_client
    
    try:
        mqtt_client = MQTTClient(
            client_id=MQTT_CLIENT_ID,
            server=MQTT_BROKER,
            port=MQTT_PORT,
            keepalive=60
        )
        mqtt_client.connect()
        print(f"✓ MQTT Connected: {MQTT_BROKER}:{MQTT_PORT}")
        return True
    except Exception as e:
        print(f"✗ MQTT Connection failed: {e}")
        mqtt_client = None
        return False

def mqtt_reconnect():
    """Reconnect to MQTT if disconnected"""
    global mqtt_client
    
    if mqtt_client is None:
        return mqtt_connect()
    
    try:
        mqtt_client.ping()
        return True
    except:
        print("⚠️  MQTT disconnected, reconnecting...")
        try:
            mqtt_client.disconnect()
        except:
            pass
        return mqtt_connect()

# ======================== DATA LOGGING TO MQTT ========================
def log_to_mqtt(action, speed):
    """Send motor control data to MQTT broker"""
    global mqtt_client
    
    try:
        # Ensure MQTT is connected
        if not mqtt_reconnect():
            print("  ✗ Cannot log - MQTT not connected")
            return False
        
        # Create JSON payload
        timestamp = time.time()
        data = {
            "action": action,
            "speed": speed,
            "timestamp": timestamp,
            "device": "esp32_motor"
        }
        
        # Convert to JSON string
        payload = ujson.dumps(data)
        
        # Publish to MQTT
        mqtt_client.publish(MQTT_TOPIC, payload)
        print(f"  📊 MQTT Published: {action}, speed={speed}")
        return True
        
    except Exception as e:
        print(f"  ✗ Failed to publish to MQTT: {e}")
        mqtt_client = None  # Force reconnect on next attempt
        return False

# ======================== MOTOR CONTROL ========================
def set_speed(pct):
    """Set motor speed percentage"""
    global current_speed
    pct = int(max(0, min(100, pct)))
    current_speed = pct
    ENA.duty(int(PWM_MAX * (current_speed / 100.0)))
    print(f"⚡ Speed: {current_speed}%")

def motor_forward():
    """Move motor forward"""
    global current_action
    current_action = "forward"
    set_speed(current_speed)
    IN1.on()
    IN2.off()
    print("⬆️  Forward")
    log_to_mqtt("forward", current_speed)

def motor_backward():
    """Move motor backward"""
    global current_action
    current_action = "backward"
    set_speed(current_speed)
    IN1.off()
    IN2.on()
    print("⬇️  Backward")
    log_to_mqtt("backward", current_speed)

def motor_stop():
    """Stop motor"""
    global current_action
    current_action = "stop"
    IN1.off()
    IN2.off()
    ENA.duty(0)
    print("⏹️  Stop")
    log_to_mqtt("stop", 0)

# ======================== HTTP RESPONSES ========================
HEAD_OK_TEXT = (
    "HTTP/1.1 200 OK\r\n"
    "Content-Type: text/plain\r\n"
    "Access-Control-Allow-Origin: *\r\n"
    "Connection: close\r\n\r\n"
)

HEAD_OK_HTML = (
    "HTTP/1.1 200 OK\r\n"
    "Content-Type: text/html\r\n"
    "Access-Control-Allow-Origin: *\r\n"
    "Connection: close\r\n\r\n"
)

HEAD_404 = (
    "HTTP/1.1 404 Not Found\r\n"
    "Content-Type: text/plain\r\n"
    "Access-Control-Allow-Origin: *\r\n"
    "Connection: close\r\n\r\nNot Found"
)

HOME_HTML = """<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ESP32 Motor Control</title>
<style>
body { font-family: Arial; padding: 20px; max-width: 500px; margin: 0 auto; background: #f5f5f5; }
h3 { color: #333; text-align: center; }
.container { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
button { 
  width: 100%;
  padding: 15px; 
  margin: 8px 0; 
  font-size: 18px; 
  border: none; 
  border-radius: 8px; 
  cursor: pointer;
  transition: all 0.3s;
  font-weight: bold;
}
.forward { background: #4CAF50; color: white; }
.forward:active { background: #45a049; transform: scale(0.98); }
.backward { background: #2196F3; color: white; }
.backward:active { background: #0b7dda; transform: scale(0.98); }
.stop { background: #f44336; color: white; }
.stop:active { background: #da190b; transform: scale(0.98); }
input[type="range"] { 
  width: 100%; 
  height: 8px;
  border-radius: 5px;
  outline: none;
  margin: 10px 0;
}
.speed-display {
  text-align: center;
  font-size: 24px;
  font-weight: bold;
  color: #2196F3;
  margin: 10px 0;
}
.status { 
  background: #e3f2fd; 
  padding: 15px; 
  border-radius: 8px; 
  margin-top: 20px;
  text-align: center;
  font-weight: bold;
}
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

# ======================== HTTP ROUTING ========================
def route(path):
    """Route HTTP requests to appropriate handlers"""
    print(f"\n📱 Request: {path}")
    
    if path == "/" or path.startswith("/index"):
        return HEAD_OK_HTML + HOME_HTML
    
    if path.startswith("/favicon.ico"):
        return HEAD_OK_TEXT
    
    if path.startswith("/forward"):
        motor_forward()
        return HEAD_OK_TEXT + "Forward"
    
    if path.startswith("/backward"):
        motor_backward()
        return HEAD_OK_TEXT + "Backward"
    
    if path.startswith("/stop"):
        motor_stop()
        return HEAD_OK_TEXT + "Stop"
    
    if path.startswith("/speed"):
        m = ure.search(r"value=(\d+)", path)
        if m:
            new_speed = int(m.group(1))
            set_speed(new_speed)
            # Log speed change with current action
            if current_action != "stop":
                log_to_mqtt(current_action, new_speed)
            return HEAD_OK_TEXT + f"Speed {new_speed}%"
        return HEAD_OK_TEXT + "speed?value=0..100"
    
    if path.startswith("/status"):
        status = f"action={current_action},speed={current_speed}"
        return HEAD_OK_TEXT + status
    
    print("⚠️  Unknown path:", path)
    return HEAD_404

# ======================== WEB SERVER ========================
def start_server(ip, sta):
    """Start HTTP server and handle requests"""
    addr = socket.getaddrinfo(ip, 80)[0][-1]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(3)
    
    print("\n" + "="*60)
    print("🚀 ESP32 Motor Control Server with MQTT Logging")
    print("="*60)
    print(f"\n📍 Web Interface: http://{ip}/")
    print(f"\n📋 API Endpoints:")
    print(f"   • http://{ip}/forward")
    print(f"   • http://{ip}/backward")
    print(f"   • http://{ip}/stop")
    print(f"   • http://{ip}/speed?value=50")
    print(f"   • http://{ip}/status")
    print(f"\n📡 MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"📊 MQTT Topic: {MQTT_TOPIC}")
    print(f"\n" + "="*60 + "\n")

    last_check = time.time()
    
    while True:
        try:
            # Check WiFi every 30 seconds
            if time.time() - last_check > 30:
                if not sta.isconnected():
                    print("⚠️  WiFi disconnected, reconnecting...")
                    sta.connect(WIFI_SSID, WIFI_PASSWORD)
                    time.sleep(5)
                last_check = time.time()
            
            cl, _ = s.accept()
            cl.settimeout(2)
            
            try:
                req = cl.recv(1024)
                if not req:
                    cl.close()
                    continue

                text = req.decode("utf-8", "ignore")
                first = text.split("\r\n")[0] if "\r\n" in text else text.split("\n")[0]
                parts = first.split(" ")
                path = parts[1] if len(parts) >= 2 else "/"

                resp = route(path)
                cl.sendall(resp)
                
            except OSError as e:
                if getattr(e, "errno", None) != 116:
                    print("⚠️  Socket error:", e)
            except Exception as e:
                print("⚠️  Handler error:", e)
            finally:
                try:
                    cl.close()
                except:
                    pass
                    
        except KeyboardInterrupt:
            print("\n\n⚠️  Server stopped by user")
            motor_stop()
            try:
                mqtt_client.disconnect()
            except:
                pass
            s.close()
            break
        except Exception as e:
            print("⚠️  Server error:", e)
            time.sleep(0.1)

# ======================== MAIN PROGRAM ========================
if __name__ == "__main__":
    print("\n" + "="*60)
    print("ESP32 Motor Control with MQTT + Node-RED + InfluxDB")
    print("Lab 5 - IoT Systems")
    print("="*60 + "\n")
    
    # Initialize motor
    motor_stop()
    
    # Connect to WiFi
    ip, sta = wifi_connect()
    
    # Connect to MQTT
    print("\n🔍 Connecting to MQTT broker...")
    if mqtt_connect():
        print("✓ MQTT connection successful!\n")
        # Send startup message
        log_to_mqtt("startup", 0)
    else:
        print("⚠️  MQTT connection failed - check if Mosquitto is running")
        print("   Run: brew services start mosquitto\n")
    
    # Start web server
    start_server(ip, sta)
