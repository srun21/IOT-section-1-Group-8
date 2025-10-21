# main_consolidated.py - ESP32 Smart Parking System with Colorful Dashboard & Timeout Records

import utime
import time
import math
import urequests
import network
import socket
from machine import Pin, PWM, I2C, time_pulse_us
from time import sleep_ms

# --- 1. CONFIGURATION ---
WIFI_SSID = "Robotic WIFI"
WIFI_PASS = "rbtWIFI@2025"

TELEGRAM_BOT_TOKEN = "7714304901:AAEAav5D5Xoxlx3y8snjFFyNWcuFJ0lTJI4"
CHAT_ID = "1049178074"

PIN_ULTRASONIC_TRIG = 27
PIN_ULTRASONIC_ECHO = 26
PIN_SERVO = 14
PIN_IR_S1 = 32
PIN_IR_S2 = 35
PIN_IR_S3 = 34
I2C_SCL = 19
I2C_SDA = 18
I2C_FREQ = 400000

NUM_SLOTS = 3
ENTRY_DEBOUNCE_MS = 300
EXIT_GRACE_MS = 1000
ULTRASONIC_DETECT_CM = 10
FEE_PER_MIN = 0.5
WEBSERVER_PORT = 80
DASHBOARD_REFRESH = 3
GATE_OPEN_TIME_MS = 2000
SERVO_STEP = 50

PIN_LED_GATE = 21
PIN_LED_FULL = 22

# --- 2. WIFI HELPER ---
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to WiFi...")
        wlan.connect(WIFI_SSID, WIFI_PASS)
        start = time.time()
        while not wlan.isconnected():
            if time.time() - start > 15:
                raise RuntimeError("WiFi connection failed")
            time.sleep(1)
    ip = wlan.ifconfig()[0]
    print("Connected, IP:", ip)
    return ip

# --- 3. TELEGRAM API ---
TELEGRAM_API_URL = "https://api.telegram.org/bot{}/sendMessage"

def format_ms_to_datetime(ms_since_boot):
    now_sec = utime.time()
    elapsed_ms = utime.ticks_ms()
    time_event_sec = now_sec - (elapsed_ms - ms_since_boot) // 1000
    t = utime.localtime(time_event_sec)
    return "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(*t[:6])

def send_message(text):
    try:
        url = TELEGRAM_API_URL.format(TELEGRAM_BOT_TOKEN)
        data = {'chat_id': CHAT_ID, 'text': text, 'parse_mode': 'Markdown'}
        r = urequests.post(url, json=data, timeout=5)
        r.close()
        return r.status_code == 200
    except:
        return False

def send_receipt_from_ticket(ticket):
    message = (
        f"Ticket CLOSED\n"
        f"ID: {ticket.id} Slot: {ticket.slot}\n"
        f"Duration: {ticket.duration_min} minutes\n"
        f"Fee: ${ticket.fee}"
    )
    send_message(message)

# --- 4. LCD API ---
class LcdApi:
    def __init__(self):
        self.num_lines = 2
        self.num_columns = 16
    def putchar(self, char): raise NotImplementedError
    def clear(self): raise NotImplementedError
    def move_to(self, col, row): raise NotImplementedError
    def putstr(self, string):
        for ch in string: self.putchar(ch)

MASK_RS = 0x01
MASK_RW = 0x02
MASK_E  = 0x04
SHIFT_BACKLIGHT = 3
BACKLIGHT = 1 << SHIFT_BACKLIGHT

class I2cLcd(LcdApi):
    def __init__(self, i2c, addr, rows, cols):
        super().__init__()
        self.i2c = i2c
        self.addr = addr
        self.num_lines = rows
        self.num_columns = cols
        self.backlight = BACKLIGHT
        self._init_lcd()

    def _write_byte(self, data):
        self.i2c.writeto(self.addr, bytes([data | self.backlight]))
    def _pulse(self, data):
        self._write_byte(data | MASK_E)
        sleep_ms(1)
        self._write_byte(data & ~MASK_E)
        sleep_ms(1)
    def _write_nibble(self, nibble):
        self._write_byte(nibble)
        self._pulse(nibble)
    def _cmd(self, cmd):
        hi = cmd & 0xF0
        lo = (cmd << 4) & 0xF0
        self._write_nibble(hi)
        self._write_nibble(lo)
    def _init_lcd(self):
        sleep_ms(50)
        self._write_byte(0x30); self._pulse(0x30); sleep_ms(5)
        self._pulse(0x30); sleep_ms(1); self._pulse(0x20); sleep_ms(1)
        self._cmd(0x28); self._cmd(0x0C); self._cmd(0x01); sleep_ms(2); self._cmd(0x06)
    def clear(self):
        self._cmd(0x01); sleep_ms(2)
    def move_to(self, col, row):
        row_offsets = [0x00,0x40,0x14,0x54]
        self._cmd(0x80 | (col + row_offsets[row]))
    def putchar(self, char):
        val = ord(char)
        hi = val & 0xF0
        lo = (val <<4)&0xF0
        self._write_nibble(hi|MASK_RS)
        self._write_nibble(lo|MASK_RS)

# --- 5. PARKING LOGIC ---
class Slot:
    def __init__(self,name):
        self.name = name
        self.occupied = False
        self.assigned_id = None
        self.time_in_ms = None
        self.ir_state_ms = utime.ticks_ms()

class Ticket:
    def __init__(self,id_,slot_name,time_in_ms):
        self.id = id_
        self.slot = slot_name
        self.time_in_ms = time_in_ms
        self.time_out_ms = None
        self.duration_min = None
        self.fee = None
    def close(self,time_out_ms):
        self.time_out_ms = time_out_ms
        duration_min = max(math.ceil(utime.ticks_diff(self.time_out_ms,self.time_in_ms)/60000),0)
        self.duration_min = duration_min
        self.fee = duration_min*FEE_PER_MIN

class ParkingManager:
    def __init__(self):
        self.slots = [Slot(f"S{i+1}") for i in range(NUM_SLOTS)]
        self.open_tickets = {}
        self.closed_tickets = []
        self.next_ids = list(range(1,NUM_SLOTS+1))
        self.recently_occupied = {}  # track recent entries

    def assign_lowest_id(self):
        return min(self.next_ids) if self.next_ids else None

    def mark_occupied(self, idx):
        s = self.slots[idx]
        if s.occupied: return None
        assigned = self.assign_lowest_id()
        if assigned is None: return None
        self.next_ids.remove(assigned)
        s.assigned_id = assigned; s.occupied=True; s.time_in_ms=utime.ticks_ms()
        t = Ticket(assigned, s.name, s.time_in_ms)
        self.open_tickets[assigned] = t
        self.recently_occupied[s.name] = utime.ticks_ms()
        print("Assigned ID", assigned, "to", s.name)
        return assigned

    def mark_free(self, idx):
        s = self.slots[idx]
        if not s.occupied: return None
        assigned = s.assigned_id
        t = self.open_tickets.pop(assigned, None)
        if t:
            t.close(utime.ticks_ms())
            self.closed_tickets.insert(0, t)
            send_receipt_from_ticket(t)
        s.occupied=False; s.assigned_id=None; s.time_in_ms=None
        if assigned not in self.next_ids:
            self.next_ids.append(assigned); self.next_ids.sort()
        print("Ticket closed ID", assigned, "slot", s.name)
        return t

    def process_ir_states(self, ir_states):
        changed = False
        now = utime.ticks_ms()
        for i, raw_state in enumerate(ir_states):
            s = self.slots[i]
            is_blocked = s.ir_state_ms > 0
            elapsed = utime.ticks_diff(now, abs(s.ir_state_ms))
            if raw_state != is_blocked:
                s.ir_state_ms = now if raw_state else -now
            if raw_state and not s.occupied and elapsed >= ENTRY_DEBOUNCE_MS:
                self.mark_occupied(i); changed=True; s.ir_state_ms=now
            elif not raw_state and s.occupied and elapsed >= EXIT_GRACE_MS:
                self.mark_free(i); changed=True; s.ir_state_ms=-now

        # cleanup recently_occupied older than 60s
        to_remove=[]
        for slot_name, ts in self.recently_occupied.items():
            if utime.ticks_diff(now, ts) > 60000:
                to_remove.append(slot_name)
        for slot_name in to_remove:
            del self.recently_occupied[slot_name]
        return changed

    def get_status(self):
        total=len(self.slots)
        free=sum(1 for s in self.slots if not s.occupied)
        occupied=total-free
        slots_info=[]
        now=utime.ticks_ms()
        for s in self.slots:
            elapsed_min=None
            if s.occupied and s.time_in_ms:
                elapsed_min=utime.ticks_diff(now,s.time_in_ms)/60000.0
            slots_info.append({"name":s.name,"occupied":s.occupied,"id":s.assigned_id,"elapsed_min":elapsed_min})
        return {
            "total":total,
            "free":free,
            "occupied":occupied,
            "slots":slots_info,
            "open_tickets":list(self.open_tickets.values()),
            "recent_closed":self.closed_tickets[:10],
            "recently_occupied": self.recently_occupied
        }

# --- 6. WEBSERVER ---
def render_dashboard_html(status):
    # Count slots
    free_count = status["free"]
    occupied_count = status["occupied"]
    status_text = "Available" if free_count > 0 else "FULL"
    
    # Build slot panels
    slot_html = ""
    now = utime.ticks_ms()
    for s in status["slots"]:
        slot_name = s["name"]
        if s["occupied"]:
            elapsed_min = s["elapsed_min"] or 0
            hours = int(elapsed_min // 60)
            minutes = int(elapsed_min % 60)
            seconds = int((elapsed_min * 60) % 60)
            elapsed = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            
            # Check if recently occupied for flash effect
            if slot_name in status.get('recently_occupied', {}):
                slot_class = "slot occupied flash"
            else:
                slot_class = "slot occupied"
            
            slot_html += f"""
            <div class="{slot_class}">
                <h3>{slot_name}</h3>
                <p class="status">OCCUPIED</p>
                <p>ID: {s["id"]}</p>
                <p>Elapsed: {elapsed}</p>
            </div>
            """
        else:
            slot_html += f"""
            <div class="slot free">
                <h3>{slot_name}</h3>
                <p class="status">FREE</p>
            </div>
            """
    
    # Build active tickets table
    active_html = ""
    for ticket in status["open_tickets"]:
        elapsed_min = utime.ticks_diff(now, ticket.time_in_ms) / 60000.0
        hours = int(elapsed_min // 60)
        minutes = int(elapsed_min % 60)
        seconds = int((elapsed_min * 60) % 60)
        elapsed = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        time_in_str = format_ms_to_datetime(ticket.time_in_ms)
        
        active_html += f"""
        <tr>
            <td>{ticket.id}</td>
            <td>{ticket.slot}</td>
            <td>{time_in_str}</td>
            <td>{elapsed}</td>
        </tr>
        """
    
    # Build closed tickets table
    closed_html = ""
    for ticket in status["recent_closed"]:
        closed_html += f"""
        <tr>
            <td>{ticket.id}</td>
            <td>{ticket.slot}</td>
            <td>{ticket.duration_min} min</td>
            <td>${ticket.fee:.2f}</td>
            <td>{format_ms_to_datetime(ticket.time_out_ms)}</td>
        </tr>
        """
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="{DASHBOARD_REFRESH}">
    <title>Smart Parking System</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: Arial, sans-serif; background: #f5f5f5; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ text-align: center; color: #333; margin-bottom: 20px; }}
        .status-bar {{ background: #2196F3; color: white; padding: 15px; border-radius: 8px; margin-bottom: 20px; display: flex; justify-content: space-around; }}
        .status-bar div {{ text-align: center; }}
        .status-bar h2 {{ font-size: 24px; }}
        .slots {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 30px; }}
        .slot {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }}
        .slot h3 {{ font-size: 24px; margin-bottom: 10px; }}
        .slot.free {{ border: 3px solid #4CAF50; }}
        .slot.occupied {{ border: 3px solid #f44336; }}
        .slot.flash {{ animation: flash-border 1s ease-in-out 3; }}
        @keyframes flash-border {{ 0%{{border-color:#f44336;}} 50%{{border-color:#ff9999;}} 100%{{border-color:#f44336;}} }}
        .slot .status {{ font-size: 18px; font-weight: bold; margin: 10px 0; }}
        .slot.free .status {{ color: #4CAF50; }}
        .slot.occupied .status {{ color: #f44336; }}
        .section {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .section h2 {{ color: #333; margin-bottom: 15px; border-bottom: 2px solid #2196F3; padding-bottom: 10px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #2196F3; color: white; }}
        tr:hover {{ background: #f5f5f5; }}
        .empty {{ text-align: center; color: #999; padding: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🅿️ Smart Parking System</h1>
        
        <div class="status-bar">
            <div><p>Total Slots</p><h2>{status["total"]}</h2></div>
            <div><p>Free</p><h2>{free_count}</h2></div>
            <div><p>Occupied</p><h2>{occupied_count}</h2></div>
            <div><p>Status</p><h2>{status_text}</h2></div>
        </div>
        
        <div class="slots">
            {slot_html}
        </div>
        
        <div class="section">
            <h2>🚗 Active Tickets</h2>
            <table>
                <tr>
                    <th>ID</th>
                    <th>Slot</th>
                    <th>Time-In</th>
                    <th>Elapsed</th>
                </tr>
                {active_html if active_html else '<tr><td colspan="4" class="empty">No active tickets</td></tr>'}
            </table>
        </div>
        
        <div class="section">
            <h2>📋 Recent Tickets</h2>
            <table>
                <tr>
                    <th>ID</th>
                    <th>Slot</th>
                    <th>Duration</th>
                    <th>Fee</th>
                    <th>Time-Out</th>
                </tr>
                {closed_html if closed_html else '<tr><td colspan="5" class="empty">No recent tickets</td></tr>'}
            </table>
        </div>
    </div>
</body>
</html>"""
    return html

class WebServer:
    def __init__(self, port=WEBSERVER_PORT):
        self.addr=socket.getaddrinfo("0.0.0.0",port)[0][-1]
        self.sock=socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        self.sock.bind(self.addr)
        self.sock.listen(1)
        self.sock.settimeout(0.1)
        print("Web server listening on port",port)
    def poll(self,parking):
        try:
            cl,addr=self.sock.accept()
        except: return
        try:
            cl.recv(1024)
            html=render_dashboard_html(parking.get_status())
            cl.send(b"HTTP/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n")
            cl.send(html.encode())
        finally:
            cl.close()

# --- 7. HARDWARE SETUP ---
TRIG=Pin(PIN_ULTRASONIC_TRIG,Pin.OUT)
ECHO=Pin(PIN_ULTRASONIC_ECHO,Pin.IN)
SERVO_PIN=Pin(PIN_SERVO,Pin.OUT)
IR_PINS=[Pin(PIN_IR_S1,Pin.IN),Pin(PIN_IR_S2,Pin.IN),Pin(PIN_IR_S3,Pin.IN)]
LED_GATE=Pin(PIN_LED_GATE,Pin.OUT)
LED_FULL=Pin(PIN_LED_FULL,Pin.OUT)
servo=PWM(SERVO_PIN,freq=50)
servo_angle=0
target_angle=0
servo_last_update=utime.ticks_ms()
gate_close_time=0

def servo_write(angle):
    min_us=500; max_us=2500
    pulse_us=min_us+(angle/180)*(max_us-min_us)
    duty=int((pulse_us/20000)*1023)
    servo.duty(duty)

def update_servo():
    global servo_angle,target_angle,servo_last_update
    now=utime.ticks_ms()
    if utime.ticks_diff(now,servo_last_update)>=20:
        if servo_angle<target_angle:
            servo_angle+=SERVO_STEP
            if servo_angle>target_angle: servo_angle=target_angle
        elif servo_angle>target_angle:
            servo_angle-=SERVO_STEP
            if servo_angle<target_angle: servo_angle=target_angle
        servo_write(servo_angle)
        servo_last_update=now

def open_gate(parking_manager):
    """Open gate only if slots are available"""
    global target_angle, gate_close_time
    
    status = parking_manager.get_status()
    if status["free"] == 0:
        print("Gate blocked - parking full")
        return False
    
    if target_angle == 0:
        target_angle = 90
        LED_GATE.value(1)
        gate_close_time = utime.ticks_add(utime.ticks_ms(), GATE_OPEN_TIME_MS)
        print("Gate opened - {} slots available".format(status["free"]))
        return True
    return False

def close_gate():
    global target_angle,gate_close_time
    if target_angle!=0:
        target_angle=0
        LED_GATE.value(0)
        gate_close_time=0
        print("Gate closed")

def read_ultrasonic():
    TRIG.value(0)
    time.sleep_us(2)
    TRIG.value(1)
    time.sleep_us(10)
    TRIG.value(0)
    dur=time_pulse_us(ECHO,1,30000)
    return dur/58.3 if dur>=0 else 999

def update_lcd_display(parking, lcd_):
    if not lcd_: 
        return
    
    status = parking.get_status()
    free_slots = [s["name"] for s in status["slots"] if not s["occupied"]]
    
    lcd_.clear()
    
    # Line 0: Parking Status
    lcd_.move_to(0, 0)
    lcd_.putstr("Parking Status")
    
    # Line 1: Free slots or FULL
    lcd_.move_to(0, 1)
    if len(free_slots) == 0:
        lcd_.putstr("FULL")
        LED_FULL.value(1)
    else:
        lcd_.putstr("Free: " + " ".join(free_slots))
        LED_FULL.value(0)

# --- INITIALIZATION ---
try: IP_ADDRESS=connect_wifi()
except: IP_ADDRESS=None

lcd=None
try:
    i2c=I2C(0,scl=Pin(I2C_SCL),sda=Pin(I2C_SDA),freq=I2C_FREQ)
    dev=i2c.scan()
    if not dev: raise Exception("No LCD found")
    lcd=I2cLcd(i2c,dev[0],2,16)
    lcd.clear()
    lcd.putstr(f"IP:{IP_ADDRESS or 'N/A'}")
except: print("LCD init failed")

parking=ParkingManager()
webserver=WebServer()
servo_write(0)
LED_GATE.value(0); LED_FULL.value(0)
update_lcd_display(parking,lcd)

# --- MAIN LOOP ---
while True:
    update_servo()
    
    # Auto-close gate after timeout
    if gate_close_time and utime.ticks_diff(utime.ticks_ms(), gate_close_time) >= 0:
        close_gate()
    
    # Ultrasonic detection - open gate only if slots available
    if read_ultrasonic() <= ULTRASONIC_DETECT_CM and target_angle == 0:
        if open_gate(parking):  # Pass parking manager to check availability
            update_lcd_display(parking, lcd)
    
    # Process IR sensors and update parking status
    raw_ir = [pin.value() == 0 for pin in IR_PINS]
    if parking.process_ir_states(raw_ir):
        update_lcd_display(parking, lcd)
        
        # If parking just became full while gate is open, close it immediately
        status = parking.get_status()
        if status["free"] == 0 and target_angle != 0:
            close_gate()
            print("Gate closed - parking now full")
    
    webserver.poll(parking)
    time.sleep(0.05)



