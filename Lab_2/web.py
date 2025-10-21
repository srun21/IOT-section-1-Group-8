import socket
import dht
from machine import Pin, SoftI2C, time_pulse_us
from time import sleep, sleep_us
from machine_i2c_lcd import I2cLcd

# Hardware setup
sensor = dht.DHT22(Pin(4))  # DHT22 connected to GPIO pin 4
led = Pin(2, Pin.OUT)       # LED connected to GPIO pin 2

# LCD setup
I2C_ADDR = 0x27
i2c = SoftI2C(sda=Pin(21), scl=Pin(22), freq=100000)
lcd = I2cLcd(i2c, I2C_ADDR, 2, 16)

# Ultrasonic sensor setup
TRIG = Pin(27, Pin.OUT)
ECHO = Pin(26, Pin.IN)

# Global variables for sensor data
temp = 0
hum = 0
distance = 0
alpha = 0.35  # EMA smoothing factor for distance
filtered_distance = None
lcd_mode = "default"  # "default", "ultrasonic", "temp", "none" (for custom text)
lcd_custom_text = ""  # For Task 4
scroll_index = 0
scroll_delay = 0.1  # seconds per scroll step

# LCD helper functions
LCD_COLS = 16
SPACES16 = " " * LCD_COLS

def _fit16(text):
    s = "" if text is None else str(text)
    n = len(s)
    if n < LCD_COLS:
        return s + SPACES16[:LCD_COLS - n]
    return s[:LCD_COLS]

def lcd_line(row, text=""):
    lcd.move_to(0, row)
    lcd.putstr(_fit16(text))

def read_sensor():
    global temp, hum
    temp = hum = 0
    try:
        sensor.measure()
        temp = sensor.temperature()
        hum = sensor.humidity()
        if (isinstance(temp, float) and isinstance(hum, float)) or (isinstance(temp, int) and isinstance(hum, int)):
            hum = round(hum, 2)
            return True
        else:
            return False
    except OSError:
        return False

def distance_cm(timeout_us=30000):
    TRIG.off()
    sleep_us(2)
    TRIG.on()
    sleep_us(10)
    TRIG.off()
    t = time_pulse_us(ECHO, 1, timeout_us)
    if t < 0:
        return None
    return (t * 0.0343) / 2.0

def read_distance():
    global distance, filtered_distance
    d = distance_cm()
    if d is not None:
        filtered_distance = d if filtered_distance is None else (alpha * d + (1 - alpha) * filtered_distance)
        distance = round(filtered_distance, 1)
        return True
    return False

def update_lcd():
    global lcd_mode, lcd_custom_text, scroll_index
    lcd.clear()

    # Task 4: custom text scrolling
    if lcd_custom_text:
        text = lcd_custom_text
        if len(text) <= LCD_COLS:
            lcd_line(0, text)
        else:
            display_text = text[scroll_index:scroll_index + LCD_COLS]
            lcd_line(0, display_text)
            scroll_index += 1
            if scroll_index > len(text) - LCD_COLS:
                scroll_index = 0
        return

    # LCD display based on mode
    if lcd_mode == "ultrasonic":
        if distance > 0:
            lcd_line(0, f"Distance: {distance}cm")
        else:
            lcd_line(0, "Distance: ---")
    elif lcd_mode == "temp":
        lcd_line(1, f"T:{temp}C H:{hum}%")
    else:
        lcd_line(0, "ESP32 Monitor")
        lcd_line(1, "Ready...")

def web_page():
    # LED state
    gpio_state = "ON" if led.value() else "OFF"
    led_color = "#e7bd3b" if led.value() else "#4286f4"

    # Distance color
    if distance > 0:
        distance_status = f"{distance} cm"
        if distance < 10:
            distance_color = "#dc3545"
        elif distance < 30:
            distance_color = "#fd7e14"
        else:
            distance_color = "#28a745"
    else:
        distance_status = "No reading"
        distance_color = "#6c757d"

    html = """<!DOCTYPE HTML><html>
<head>
    <title>ESP32 Smart Monitor</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="icon" href="data:,">

    <style>
        html { font-family: Arial; display: inline-block; margin: 0px auto; text-align: center; background: white; min-height: 100vh; }
        body { margin: 0; padding: 20px; color: black; }
        h1 { color: black; padding: 2vh; font-size: 2.5rem; margin-bottom: 30px; }
        .container { background: white; padding: 30px; border: 2px solid black; margin: 20px auto; max-width: 700px; }
        .sensor-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 30px 0; }
        .sensor-card { background: white; padding: 25px; border: 2px solid black; transition: none; }
        .sensor-card:hover { transform: none; }
        .temp-card { border-left-color: black; }
        .humidity-card { border-left-color: black; }
        .distance-card { border-left-color: black; }
        .sensor-value { font-size: 2.2rem; font-weight: bold; margin: 10px 0; color: black; }
        .sensor-label { font-size: 1.1rem; color: black; margin-bottom: 5px; }
        .sensor-unit { font-size: 1.2rem; color: black; }
        
        .control-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin-top: 20px; }
        .control-card { background: white; padding: 20px; border: 2px solid black; }
        
        /* Simple text input section */
        .text-input-card { 
            background: white; 
            padding: 20px; 
            border: 2px solid black; 
            margin-top: 20px; 
        }
        .text-input { 
            width: 70%;
            padding: 10px; 
            border: 2px solid black; 
            margin-right: 10px;
            font-size: 16px;
            background: white;
            color: black;
        }
        .send-button { 
            background-color: black; 
            border: 2px solid black; 
            color: white; 
            padding: 10px 15px; 
            font-size: 16px; 
            cursor: pointer;
        }
        
        .button { display: inline-block; background-color: black; border: 2px solid black; color: white; padding: 15px 30px; text-decoration: none; font-size: 18px; margin: 10px; cursor: pointer; }
        .button-off { background-color: white; color: black; border: 2px solid black; }
        .button-distance-show { background-color: black; color: white; }
    </style>
</head>
<body>
    <h1>ESP32 Web Server</h1>
    <div class="container">
        <div class="sensor-grid">
            <div class="sensor-card temp-card">
                <div class="sensor-label">Temperature</div>
                <div class="sensor-value">""" + str(temp) + """<span class="sensor-unit">&deg;C</span></div>
            </div>
            <div class="sensor-card humidity-card">
                <div class="sensor-label">Humidity</div>
                <div class="sensor-value">""" + str(hum) + """<span class="sensor-unit">%</span></div>
            </div>
            <div class="sensor-card distance-card">
                <div class="sensor-label">Distance</div>
                <div class="sensor-value">""" + distance_status + """</div>
            </div>
        </div>
        
        <div class="control-grid">
            <div class="control-card">
                <h3>LED Control</h3>
                <div>
                    <a href="/?led=on"><button class="button">Turn ON</button></a>
                    <a href="/?led=off"><button class="button button-off">Turn OFF</button></a>
                </div>
            </div>
            <div class="control-card">
                <h3>LCD Data Mode</h3>
                <div>
                    <a href="/?lcd=ultrasonic"><button class="button button-distance-show">Ultrasonic Data</button></a>
                    <a href="/?lcd=temp"><button class="button button-off">Temp Data</button></a>
                </div>
            </div>
        </div>
        
        <div class="text-input-card">
            <h3>Custom LCD Text</h3>
            <form action="/" method="GET">
                <input type="text" name="lcdtext" class="text-input" placeholder="Enter custom message">
                <button type="submit" class="send-button">Send</button>
            </form>
        </div>
        
        <div style="margin-top:20px; font-size:0.9rem; color:black;">
            Auto-refresh every 15 seconds
        </div>
    </div>
    <script> setTimeout(function(){ window.location.reload(1); }, 15000); </script>
</body>
</html>"""
    return html

# Initialize LCD
lcd.clear()
lcd_line(0, "System Starting...")
lcd_line(1, "Please wait...")
sleep(2)

# Socket setup
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('', 80))
s.listen(5)

print("ESP32 Smart Monitor Started!")
lcd_line(0, "Server Ready!")
lcd_line(1, "Connect via WiFi")

# Main loop
while True:
    try:
        read_sensor()
        read_distance()
        update_lcd()
        sleep(scroll_delay)

        # Web connections
        s.settimeout(0.1)
        try:
            conn, addr = s.accept()
            print('Connection from %s' % str(addr))
            request = conn.recv(1024)
            request_str = str(request)

            # LED
            if '/?led=on' in request_str:
                led.value(1)
            if '/?led=off' in request_str:
                led.value(0)

            # LCD mode
            if '/?lcd=ultrasonic' in request_str:
                lcd_mode = "ultrasonic"
                lcd_custom_text = ""
            if '/?lcd=temp' in request_str:
                lcd_mode = "temp"
                lcd_custom_text = ""

            # Custom text
            if "lcdtext=" in request_str:
                try:
                    import ure
                    match = ure.search("lcdtext=([^& ]*)", request_str)
                    if match:
                        text = match.group(1)
                        text = text.replace("+", " ")
                        text = text.replace("%21", "!").replace("%3F", "?").replace("%2C", ",")
                        lcd_custom_text = text
                        lcd_mode = "none"
                        print("LCD Custom Text:", lcd_custom_text)
                except Exception as e:
                    print("Text decode error:", e)

            # Send web page
            response = web_page()
            conn.send(b'HTTP/1.1 200 OK\n')
            conn.send(b'Content-Type: text/html\n')
            conn.send(b'Connection: close\n\n')
            conn.sendall(response.encode('utf-8'))
            conn.close()
        except OSError:
            pass

    except KeyboardInterrupt:
        print("Server stopped")
        lcd.clear()
        lcd_line(0, "Server Stopped")
        break
    except Exception as e:
        print('Error:', e)
        lcd_line(0, "Error occurred")
        lcd_line(1, "Check connection")
