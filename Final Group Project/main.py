from machine import Pin, PWM, I2C
import time
import network
import utime
import gc
import ujson
from umqtt.simple import MQTTClient

# ==================== WIFI CREDENTIALS ====================
WIFI_SSID = "...."
WIFI_PASSWORD = "......"

# ==================== MQTT CONFIGURATION ====================
MQTT_BROKER = "......"  # CHANGE TO YOUR PC'S LOCAL IP
MQTT_PORT = 1883
MQTT_TOPIC_STATUS = "smartbox/status"
MQTT_TOPIC_EVENT = "smartbox/event"
MQTT_TOPIC_PACKAGE = "smartbox/package"
MQTT_TOPIC_COMMAND = "smartbox/command"  
MQTT_CLIENT_ID = "smartbox_esp32"

# Global MQTT client
mqtt_client = None

# ==================== PIN CONFIGURATION ====================
TRIG_PIN_1 = 27             # Ultrasonic 1 trigger (Package Slot 1)
ECHO_PIN_1 = 26             # Ultrasonic 1 echo
TRIG_PIN_2 = 25             # Ultrasonic 2 trigger (Package Slot 2)
ECHO_PIN_2 = 33             # Ultrasonic 2 echo
IR_PIN = 32                 # IR sensor (detects door open/close)
DOOR_SERVO_PIN = 14         # Servo for door
LOCK_SERVO_PIN = 12         # Servo for lock
BUTTON_PIN = 19             # Push button
BUZZER_PIN = 13             # Buzzer
LED_PIN = 2                 # LED
I2C_SDA = 21                # LCD SDA
I2C_SCL = 22                # LCD SCL

# ==================== SERVO ANGLES ====================
DOOR_OPEN_ANGLE = 80        # Door open
DOOR_CLOSE_ANGLE = -22        # Door closed
LOCK_LOCKED_ANGLE = 145      # Lock engaged
LOCK_UNLOCKED_ANGLE = 55     # Lock released

# ==================== DISTANCE THRESHOLD ====================
PACKAGE_THRESHOLD = 7     # cm - package present if distance < 10cm

# ==================== LCD I2C ADDRESS ====================
LCD_ADDR = 0x27

# ==================== SYSTEM STATE ====================
class BoxState:
    def __init__(self):
        self.package_count = 0
        self.package_ids = []
        self.package_timestamps = []
        self.door_locked = False
        self.door_open = False
        self.retrieval_mode = False
        self.total_packages_received = 0
        self.event_log = []
        self.last_update_id = 0
        
    def add_package(self, pkg_id, timestamp):
        self.package_count += 1
        self.package_ids.append(pkg_id)
        self.package_timestamps.append(timestamp)
        self.total_packages_received += 1
        self.log_event("PACKAGE_RECEIVED", pkg_id, timestamp)
        
    def remove_all_packages(self):
        for i, pkg_id in enumerate(self.package_ids):
            self.log_event("PACKAGE_RETRIEVED", pkg_id, get_timestamp())
        self.package_count = 0
        self.package_ids = []
        self.package_timestamps = []
        
    def log_event(self, event_type, pkg_id, timestamp):
        event = {
            "type": event_type,
            "package_id": pkg_id,
            "timestamp": timestamp,
            "package_count": self.package_count
        }
        self.event_log.append(event)
        if len(self.event_log) > 50:  # Keep only last 50 events
            self.event_log.pop(0)

# ==================== HARDWARE SETUP ====================
# Ultrasonic Sensors
trig1 = Pin(TRIG_PIN_1, Pin.OUT)
echo1 = Pin(ECHO_PIN_1, Pin.IN)
trig2 = Pin(TRIG_PIN_2, Pin.OUT)
echo2 = Pin(ECHO_PIN_2, Pin.IN)

# IR Sensor
ir_sensor = Pin(IR_PIN, Pin.IN)

# Button
button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)

# Buzzer
buzzer = Pin(BUZZER_PIN, Pin.OUT)
buzzer.off()

# Servos
door_servo = PWM(Pin(DOOR_SERVO_PIN), freq=50)
lock_servo = PWM(Pin(LOCK_SERVO_PIN), freq=50)

# I2C for LCD
i2c = I2C(0, scl=Pin(I2C_SCL), sda=Pin(I2C_SDA), freq=100000)

# System State
state = BoxState()

# ==================== LCD FUNCTIONS ====================
class LCD:
    def __init__(self, i2c, addr=LCD_ADDR):
        self.i2c = i2c
        self.addr = addr
        self.init_lcd()
        
    def init_lcd(self):
        try:
            time.sleep_ms(50)
            self.write_cmd(0x33)
            self.write_cmd(0x32)
            self.write_cmd(0x28)
            self.write_cmd(0x0C)
            self.write_cmd(0x06)
            self.write_cmd(0x01)
            time.sleep_ms(2)
        except:
            print("LCD init failed")
            
    def write_cmd(self, cmd):
        try:
            self.i2c.writeto(self.addr, bytearray([cmd & 0xF0 | 0x0C]))
            time.sleep_us(1)
            self.i2c.writeto(self.addr, bytearray([cmd & 0xF0 | 0x08]))
            time.sleep_us(1)
            self.i2c.writeto(self.addr, bytearray([(cmd << 4) & 0xF0 | 0x0C]))
            time.sleep_us(1)
            self.i2c.writeto(self.addr, bytearray([(cmd << 4) & 0xF0 | 0x08]))
            time.sleep_us(50)
        except:
            pass
            
    def write_data(self, data):
        try:
            self.i2c.writeto(self.addr, bytearray([data & 0xF0 | 0x0D]))
            time.sleep_us(1)
            self.i2c.writeto(self.addr, bytearray([data & 0xF0 | 0x09]))
            time.sleep_us(1)
            self.i2c.writeto(self.addr, bytearray([(data << 4) & 0xF0 | 0x0D]))
            time.sleep_us(1)
            self.i2c.writeto(self.addr, bytearray([(data << 4) & 0xF0 | 0x09]))
            time.sleep_us(50)
        except:
            pass
            
    def clear(self):
        self.write_cmd(0x01)
        time.sleep_ms(2)
        
    def set_cursor(self, row, col):
        pos = 0x80 if row == 0 else 0xC0
        self.write_cmd(pos + col)
        
    def print(self, text, row=0, col=0):
        self.set_cursor(row, col)
        for char in text:
            self.write_data(ord(char))
            
    def display_status(self, line1, line2):
        self.clear()
        self.print(line1[:16], 0, 0)
        self.print(line2[:16], 1, 0)

try:
    lcd = LCD(i2c)
except:
    lcd = None
    print("LCD not available")

# ==================== HELPER FUNCTIONS ====================
def get_timestamp():
    t = utime.localtime()
    return "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
        t[0], t[1], t[2], t[3], t[4], t[5])

def generate_package_id():
    return "PKG{}".format(state.total_packages_received + 1)

def set_servo_angle(servo, angle):
    duty = int((angle / 180.0) * 102.4 + 25.6)
    servo.duty(duty)
    time.sleep_ms(300)

def measure_distance(trig, echo):
    trig.off()
    time.sleep_us(2)
    trig.on()
    time.sleep_us(10)
    trig.off()
    
    timeout = 30000
    start = utime.ticks_us()
    while echo.value() == 0:
        if utime.ticks_diff(utime.ticks_us(), start) > timeout:
            return -1
    pulse_start = utime.ticks_us()
    
    start = utime.ticks_us()
    while echo.value() == 1:
        if utime.ticks_diff(utime.ticks_us(), start) > timeout:
            return -1
    pulse_end = utime.ticks_us()
    
    pulse_duration = utime.ticks_diff(pulse_end, pulse_start)
    distance = (pulse_duration * 0.0343) / 2
    return distance

def is_package_present(slot):
    if slot == 1:
        dist = measure_distance(trig1, echo1)
    else:
        dist = measure_distance(trig2, echo2)
    
    if dist < 0:
        return False
    return dist < PACKAGE_THRESHOLD

def is_door_physically_closed():
    return ir_sensor.value() == 1

def alarm_buzzer(duration_ms=2000):
    for _ in range(duration_ms // 200):
        buzzer.on()
        time.sleep_ms(100)
        buzzer.off()
        time.sleep_ms(100)

# ==================== SERVO CONTROL ====================
def lock_door():
    set_servo_angle(lock_servo, LOCK_LOCKED_ANGLE)
    state.door_locked = True
    print("Door LOCKED")

def unlock_door():
    set_servo_angle(lock_servo, LOCK_UNLOCKED_ANGLE)
    state.door_locked = False
    print("Door UNLOCKED")

def open_door():
    if not state.door_locked:
        set_servo_angle(door_servo, DOOR_OPEN_ANGLE)
        state.door_open = True
        print("Door OPENED")
        return True
    else:
        print("Cannot open - door is locked")
        return False

def close_door():
    set_servo_angle(door_servo, DOOR_CLOSE_ANGLE)
    state.door_open = False
    print("Door CLOSED")

# ==================== WIFI CONNECTION ====================
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    if not wlan.isconnected():
        print("Connecting to WiFi...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        
        timeout = 20
        while not wlan.isconnected() and timeout > 0:
            print(".", end="")
            time.sleep(1)
            timeout -= 1
            
    if wlan.isconnected():
        print("\nWiFi Connected!")
        print("IP:", wlan.ifconfig()[0])
        return True
    else:
        print("\nWiFi connection failed")
        return False

# ==================== MQTT FUNCTIONS ====================
def mqtt_callback(topic, msg):
    """Handle incoming MQTT commands from Node-RED/Telegram"""
    try:
        command = msg.decode('utf-8').lower().strip()
        print("📩 Received command:", command)
        
        if command == "status":
            publish_mqtt_status()
        elif command == "open":
            if open_door():
                print("✅ Door opened via MQTT")
        elif command == "close":
            close_door()
            print("✅ Door closed via MQTT")
        elif command == "lock":
            lock_door()
            print("✅ Door locked via MQTT")
        elif command == "unlock":
            unlock_door()
            print("✅ Door unlocked via MQTT")
        elif command == "retrieve" or command == "retrieval":
            activate_retrieval_mode()
            print("✅ Retrieval mode activated via MQTT")
        else:
            print("❓ Unknown command:", command)
    except Exception as e:
        print("❌ Error processing command:", e)

def connect_mqtt():
    global mqtt_client
    try:
        print("Connecting to MQTT broker:", MQTT_BROKER)
        mqtt_client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER, port=MQTT_PORT)
        mqtt_client.connect()
        print("✅ MQTT Connected!")
        
        # Subscribe to command topic to receive commands from Node-RED/Telegram
        mqtt_client.set_callback(mqtt_callback)
        mqtt_client.subscribe(MQTT_TOPIC_COMMAND)
        print("📥 Subscribed to:", MQTT_TOPIC_COMMAND)
        
        return True
    except OSError as e:
        print("❌ MQTT connection failed:", e)
        print("   Check: 1) Mac's IP is correct")
        print("         2) Mosquitto is running on Mac")
        print("         3) Mac and ESP32 on same WiFi")
        mqtt_client = None
        return False
    except Exception as e:
        print("❌ MQTT connection failed:", e)
        mqtt_client = None
        return False

def publish_mqtt(topic, message):
    global mqtt_client
    try:
        if mqtt_client is None:
            if not connect_mqtt():
                return False
        
        if isinstance(message, dict):
            message = ujson.dumps(message)
        
        mqtt_client.publish(topic, message)
        print("📤 MQTT published to", topic)
        return True
    except Exception as e:
        print("❌ MQTT publish error:", e)
        mqtt_client = None
        return False

def publish_mqtt_status():
    status = {
        "timestamp": get_timestamp(),
        "package_count": state.package_count,
        "door_locked": state.door_locked,
        "door_open": state.door_open,
        "package_ids": state.package_ids,
        "total_received": state.total_packages_received
    }
    publish_mqtt(MQTT_TOPIC_STATUS, status)

def publish_mqtt_event(event):
    event_data = {
        "timestamp": get_timestamp(),
        "event_type": event.get("type", "UNKNOWN"),
        "package_id": event.get("package_id", ""),
        "package_count": state.package_count,
        "slot": event.get("slot", 0)
    }
    publish_mqtt(MQTT_TOPIC_EVENT, event_data)

def publish_mqtt_package(pkg_id, action, slot):
    package_data = {
        "timestamp": get_timestamp(),
        "package_id": pkg_id,
        "action": action,  # "RECEIVED" or "RETRIEVED"
        "slot": slot,
        "total_count": state.package_count
    }
    publish_mqtt(MQTT_TOPIC_PACKAGE, package_data)

def check_mqtt_commands():
    """Check for incoming MQTT commands"""
    global mqtt_client
    try:
        if mqtt_client:
            mqtt_client.check_msg()
    except Exception as e:
        print("❌ MQTT check error:", e)

# ==================== LCD UPDATE ====================
def update_lcd_display():
    if lcd is None:
        return
        
    if state.retrieval_mode:
        lcd.display_status("RETRIEVAL MODE", "TAKE PACKAGES")
    elif state.package_count == 0:
        lcd.display_status("BOX STATUS", "BOX EMPTY")
    elif state.package_count == 1:
        lcd.display_status("BOX STATUS", "1 PACKAGE")
    elif state.package_count == 2:
        lcd.display_status("BOX STATUS", "2 PACKAGES FULL")

# ==================== OPERATING MODES ====================
def idle_mode():
    unlock_door()
    close_door()
    update_lcd_display()
    print("=== IDLE MODE ===")

def receiving_mode_package1():
    print("=== RECEIVING PACKAGE 1 ===")
    
    # Wait for door to open (button, telegram, or web)
    # Door opening is handled by button/telegram handlers
    
    # Wait for package insertion
    print("Waiting for package 1...")
    while not is_package_present(1):
        time.sleep_ms(100)
        
    print("Package 1 detected!")
    pkg_id = generate_package_id()
    timestamp = get_timestamp()
    state.add_package(pkg_id, timestamp)
    
    # Auto close after 10 seconds or manual close
    print("Door will auto-close in 10 seconds...")
    start_time = utime.ticks_ms()
    while utime.ticks_diff(utime.ticks_ms(), start_time) < 5000:
        if not state.door_open:  # Manual close
            break
        time.sleep_ms(100)
    
    if state.door_open:
        close_door()
    
    # Auto lock
    lock_door()
    
    # Publish to MQTT (Node-RED will send Telegram)
    publish_mqtt_status()
    publish_mqtt_package(pkg_id, "RECEIVED", 1)
    publish_mqtt_event({"type": "PACKAGE_RECEIVED", "slot": 1, "id": pkg_id})
    
    update_lcd_display()

def receiving_mode_package2():
    print("=== RECEIVING PACKAGE 2 ===")
    print("Waiting for unlock command...")
    
    # Owner must unlock via telegram/web
    # This will be handled by command handlers
    # When unlocked, door will open automatically in the handler
    
    # Check for package 1 theft
    if not is_package_present(1):
        print("⚠️ PACKAGE 1 STOLEN!")
        alarm_buzzer(3000)
        
        # Publish theft alert (Node-RED will send Telegram)
        theft_event = {
            "type": "PACKAGE_STOLEN",
            "package_id": state.package_ids[0] if state.package_ids else "UNKNOWN",
            "timestamp": get_timestamp(),
            "alert": "Package #1 has been removed (THEFT DETECTED)!"
        }
        publish_mqtt_event(theft_event)
        
        close_door()
        lock_door()
        state.log_event("PACKAGE_STOLEN", state.package_ids[0] if state.package_ids else "UNKNOWN", get_timestamp())
        state.package_count = 0
        state.package_ids = []
        state.package_timestamps = []
        idle_mode()
        return
    
    # Wait for package 2 insertion
    print("Waiting for package 2...")
    while not is_package_present(2):
        time.sleep_ms(100)
        # Continuous theft check
        if not is_package_present(1):
            print("⚠️ PACKAGE 1 STOLEN!")
            alarm_buzzer(3000)
            
            # Publish theft alert
            theft_event = {
                "type": "PACKAGE_STOLEN",
                "package_id": state.package_ids[0] if state.package_ids else "UNKNOWN",
                "timestamp": get_timestamp(),
                "alert": "Package #1 removed during delivery!"
            }
            publish_mqtt_event(theft_event)
            
            close_door()
            lock_door()
            state.log_event("PACKAGE_STOLEN", state.package_ids[0] if state.package_ids else "UNKNOWN", get_timestamp())
            idle_mode()
            return
    
    print("Package 2 detected!")
    pkg_id = generate_package_id()
    timestamp = get_timestamp()
    state.add_package(pkg_id, timestamp)
    
    # Auto close
    print("Door will auto-close in 10 seconds...")
    start_time = utime.ticks_ms()
    while utime.ticks_diff(utime.ticks_ms(), start_time) < 5000:
        if not state.door_open:
            break
        time.sleep_ms(100)
    
    if state.door_open:
        close_door()
    
    # Auto lock
    lock_door()
    
    # Publish to MQTT (Node-RED will send Telegram)
    publish_mqtt_status()
    publish_mqtt_package(pkg_id, "RECEIVED", 2)
    publish_mqtt_event({"type": "PACKAGE_RECEIVED", "slot": 2, "id": pkg_id})
    
    update_lcd_display()

def activate_retrieval_mode():
    print("=== RETRIEVAL MODE ===")
    state.retrieval_mode = True
    unlock_door()
    open_door()
    update_lcd_display()
    
    # Wait for owner to take packages
    print("Waiting for package retrieval...")
    while True:
        slot1_empty = not is_package_present(1)
        slot2_empty = not is_package_present(2)
        
        if slot1_empty and slot2_empty and state.package_count > 0:
            print("All packages retrieved!")
            state.remove_all_packages()
            
            # Publish retrieval success
            publish_mqtt_event({"type": "ALL_PACKAGES_RETRIEVED", "timestamp": get_timestamp()})
            publish_mqtt_status()
            break
            
        time.sleep_ms(500)
    
    state.retrieval_mode = False
    close_door()
    idle_mode()

# ==================== BUTTON HANDLER ====================
last_button_state = 1
button_press_time = 0

def handle_button():
    global last_button_state, button_press_time
    
    current_state = button.value()
    
    # Detect button press (falling edge with debounce)
    if last_button_state == 1 and current_state == 0:
        current_time = utime.ticks_ms()
        if utime.ticks_diff(current_time, button_press_time) > 300:  # 300ms debounce
            button_press_time = current_time
            
            if not state.door_locked:
                # Toggle door
                if state.door_open:
                    close_door()
                    print("Button: Door closed")
                else:
                    open_door()
                    print("Button: Door opened")
                update_lcd_display()
            else:
                print("Button ignored - door is locked")
    
    last_button_state = current_state

# ==================== MAIN SYSTEM LOOP ====================
def main():
    print("\n" + "="*40)
    print("  SMART PACKAGE BOX SYSTEM")
    print("="*40 + "\n")
    
    # Connect to WiFi
    if not connect_wifi():
        print("❌ Running without WiFi!")
        return
    
    print("✅ WiFi connected")
    
    # Connect MQTT
    if connect_mqtt():
        print("✅ MQTT connected successfully")
        publish_mqtt_status()
    else:
        print("⚠️ MQTT connection failed, will retry later")
    
    # Initialize to IDLE mode
    idle_mode()
    
    last_mqtt_check = utime.ticks_ms()
    mqtt_check_interval = 100  # Check every 100ms
    
    print("\n🟢 System Ready!")
    
    while True:
        try:
            # Handle button press
            handle_button()
            
            # Check MQTT commands frequently
            if utime.ticks_diff(utime.ticks_ms(), last_mqtt_check) > mqtt_check_interval:
                check_mqtt_commands()
                last_mqtt_check = utime.ticks_ms()
            
            # State machine logic
            if not state.retrieval_mode:
                if state.package_count == 0:
                    # Check if package 1 inserted
                    if is_package_present(1) and state.door_open:
                        time.sleep_ms(500)
                        if is_package_present(1):
                            receiving_mode_package1()
                            
                elif state.package_count == 1:
                    # THEFT MONITORING - Package 1 stolen
                    if state.door_locked and not is_package_present(1):
                        print("⚠️ PACKAGE 1 STOLEN!")
                        alarm_buzzer(5000)  # 5 seconds
                        
                        theft_event = {
                            "type": "PACKAGE_STOLEN",
                            "package_id": state.package_ids[0],
                            "timestamp": get_timestamp(),
                            "alert": "Package #1 stolen!"
                        }
                        publish_mqtt_event(theft_event)
                        
                        state.package_count = 0
                        state.package_ids = []
                        state.package_timestamps = []
                        update_lcd_display()
                    
                    # Check if package 2 inserted (when unlocked and open)
                    elif not state.door_locked and state.door_open:
                        if is_package_present(2):
                            time.sleep_ms(500)
                            if is_package_present(2):
                                # Check package 1 still there during delivery
                                if not is_package_present(1):
                                    print("⚠️ PACKAGE 1 STOLEN DURING DELIVERY!")
                                    alarm_buzzer(5000)  # 5 seconds
                                    
                                    theft_event = {
                                        "type": "PACKAGE_STOLEN",
                                        "package_id": state.package_ids[0],
                                        "timestamp": get_timestamp(),
                                        "alert": "Package #1 stolen during delivery!"
                                    }
                                    publish_mqtt_event(theft_event)
                                    
                                    close_door()
                                    lock_door()
                                    state.package_count = 0
                                    state.package_ids = []
                                    state.package_timestamps = []
                                    idle_mode()
                                else:
                                    # Package 2 received successfully
                                    print("Package 2 detected!")
                                    pkg_id = generate_package_id()
                                    timestamp = get_timestamp()
                                    state.add_package(pkg_id, timestamp)
                                    
                                    time.sleep(3)
                                    close_door()
                                    lock_door()
                                    
                                    publish_mqtt_status()
                                    publish_mqtt_package(pkg_id, "RECEIVED", 2)
                                    publish_mqtt_event({"type": "PACKAGE_RECEIVED", "slot": 2, "id": pkg_id})
                                    update_lcd_display()
                
                elif state.package_count == 2:
                    # THEFT MONITORING - Both packages locked
                    if state.door_locked:
                        pkg1_present = is_package_present(1)
                        pkg2_present = is_package_present(2)
                        
                        if not pkg1_present or not pkg2_present:
                            stolen_pkg = []
                            if not pkg1_present:
                                stolen_pkg.append(state.package_ids[0])
                            if not pkg2_present:
                                stolen_pkg.append(state.package_ids[1] if len(state.package_ids) > 1 else "PKG2")
                            
                            print("⚠️ PACKAGE(S) STOLEN:", stolen_pkg)
                            alarm_buzzer(5000)  # 5 seconds
                            
                            theft_event = {
                                "type": "PACKAGE_STOLEN",
                                "package_id": ", ".join(stolen_pkg),
                                "timestamp": get_timestamp(),
                                "alert": f"Package(s) stolen: {', '.join(stolen_pkg)}"
                            }
                            publish_mqtt_event(theft_event)
                            
                            # Update package count based on what's left
                            if not pkg1_present and not pkg2_present:
                                state.package_count = 0
                                state.package_ids = []
                                state.package_timestamps = []
                            elif not pkg1_present:
                                state.package_count = 1
                                state.package_ids = [state.package_ids[1]]
                                state.package_timestamps = [state.package_timestamps[1]]
                            else:  # not pkg2_present
                                state.package_count = 1
                                state.package_ids = [state.package_ids[0]]
                                state.package_timestamps = [state.package_timestamps[0]]
                            
                            update_lcd_display()
            
            time.sleep_ms(50)
            gc.collect()
            
        except KeyboardInterrupt:
            print("\n\n❌ System stopped by user")
            if mqtt_client:
                publish_mqtt_event({"type": "SYSTEM_STOPPED", "timestamp": get_timestamp()})
            break
        except Exception as e:
            print("Error in main loop:", e)
            time.sleep(1)
# ==================== START SYSTEM ====================
if __name__ == "__main__":
    main()
