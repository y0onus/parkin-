#!/usr/bin/env python3
import time
import threading
import RPi.GPIO as GPIO
import smbus
import requests

# =====================================================
# FIREBASE CONFIG uh add your own firbase ig 
# =====================================================
FIREBASE_PARKING_URL = "-"

# =====================================================
# LCD CLASS
# =====================================================
class CharLCD1602:
    def __init__(self):
        self.bus = smbus.SMBus(1)
        self.BLEN = 1
        self.LCD_ADDR = 0x27

    def write_word(self, addr, data):
        if self.BLEN == 1:
            data |= 0x08
        else:
            data &= 0xF7
        self.bus.write_byte(addr, data)

    def send_command(self, comm):
        buf = comm & 0xF0 | 0x04
        self.write_word(self.LCD_ADDR, buf)
        time.sleep(0.002)
        buf &= 0xFB
        self.write_word(self.LCD_ADDR, buf)
        buf = (comm & 0x0F) << 4 | 0x04
        self.write_word(self.LCD_ADDR, buf)
        time.sleep(0.002)
        buf &= 0xFB
        self.write_word(self.LCD_ADDR, buf)

    def send_data(self, data):
        buf = data & 0xF0 | 0x05
        self.write_word(self.LCD_ADDR, buf)
        time.sleep(0.002)
        buf &= 0xFB
        self.write_word(self.LCD_ADDR, buf)
        buf = (data & 0x0F) << 4 | 0x05
        self.write_word(self.LCD_ADDR, buf)
        time.sleep(0.002)
        buf &= 0xFB
        self.write_word(self.LCD_ADDR, buf)

    def init_lcd(self):
        try:
            self.send_command(0x33)
            self.send_command(0x32)
            self.send_command(0x28)
            self.send_command(0x0C)
            self.send_command(0x01)
        except Exception as e:
            print("LCD init error:", e)

    def clear(self):
        try:
            self.send_command(0x01)
        except:
            pass

    def write(self, x, y, text):
        if x < 0: x = 0
        if x > 15: x = 15
        if y < 0: y = 0
        if y > 1: y = 1
        addr = 0x80 + 0x40 * y + x
        try:
            self.send_command(addr)
            for ch in text:
                self.send_data(ord(ch))
        except:
            pass

# =====================================================
# GPIO SETUP
# =====================================================
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

IR_ENTRY = 21
IR_ENTRY_VERIFY = 16
SERVO_ENTRY = 26
SERVO_EXIT = 19

GPIO.setup(IR_ENTRY, GPIO.IN)
GPIO.setup(IR_ENTRY_VERIFY, GPIO.IN)
GPIO.setup(SERVO_ENTRY, GPIO.OUT)
GPIO.setup(SERVO_EXIT, GPIO.OUT)

servo_entry = GPIO.PWM(SERVO_ENTRY, 50)
servo_exit = GPIO.PWM(SERVO_EXIT, 50)
servo_entry.start(0)
servo_exit.start(0)

# =====================================================
# GLOBAL VARIABLES
# =====================================================
floors = ['C', 'B', 'A']
slots_order = [f"{f}{i:02}" for f in floors for i in range(1, 25)]
display_lock = threading.Lock()
lcd = CharLCD1602()
lcd.init_lcd()
display_paused = False

# Servo angles to prevent jitter
entry_angle = [0]  # 0 = closed, 90 = open
exit_angle = [0]   # 0 = closed, 90 = open

# Exit gate control
exit_lock = threading.Lock()
current_exit_state = 0
auto_close_thread = None

# =====================================================
# SERVO HELPER
# =====================================================
def set_servo_angle(servo, angle, current_angle_holder):
    if current_angle_holder[0] != angle:
        duty = 2.5 + (angle / 18.0)
        servo.ChangeDutyCycle(duty)
        time.sleep(0.5)
        servo.ChangeDutyCycle(0)
        current_angle_holder[0] = angle

# =====================================================
# HELPER FUNCTIONS
# =====================================================
def initialize_parking_data():
    data = {}
    for f in floors:
        floor_slots = [f"{f}{i:02}" for i in range(1, 25)]
        if f in ['C', 'B']:
            parked = floor_slots[:]  # full
        else:
            parked = floor_slots[:15]  # first 15
        free = [s for s in floor_slots if s not in parked]
        data[f] = {
            'parked_slots': parked,
            'free_slots': free,
            'parked_count': len(parked),
            'free_count': len(free)
        }
    data['exit_gate'] = 0
    return data

def fetch_parking_data():
    try:
        res = requests.get(FIREBASE_PARKING_URL, timeout=3)
        if res.status_code == 200:
            data = res.json()
            if not data:
                data = initialize_parking_data()
                update_firebase(data)
            return data
    except Exception as e:
        print("Firebase fetch error:", e)
    return None

def update_firebase(data):
    try:
        requests.put(FIREBASE_PARKING_URL, json=data, timeout=3)
    except Exception as e:
        print("Firebase update error:", e)

def build_slot_lists(parking_data):
    assigned = []
    for f in floors:
        floor_data = parking_data.get(f, {})
        assigned += floor_data.get('parked_slots', [])
    available = [s for s in slots_order if s not in assigned]
    return assigned, available

def compute_totals(parking_data):
    total_parked = sum(len(parking_data.get(f, {}).get('parked_slots', [])) for f in floors)
    total_free = sum(len(parking_data.get(f, {}).get('free_slots', [])) for f in floors)
    return total_parked, total_free

# =====================================================
# LCD REFRESH THREAD
# =====================================================
def lcd_refresh_loop():
    global display_paused
    while True:
        if not display_paused:
            parking_data = fetch_parking_data()
            if parking_data:
                total_parked, total_free = compute_totals(parking_data)
                with display_lock:
                    lcd.clear()
                    lcd.write(0, 0, f"Parked: {total_parked}")
                    lcd.write(0, 1, f"Free: {total_free}")
        time.sleep(2)

threading.Thread(target=lcd_refresh_loop, daemon=True).start()

# =====================================================
# ENTRY HANDLER
# =====================================================
def handle_entry():
    global display_paused
    set_servo_angle(servo_entry, 90, entry_angle)  # Open
    start = time.time()
    detected = False

    while time.time() - start < 3:  # Wait max 3s
        if GPIO.input(IR_ENTRY_VERIFY) == 0:  # Car detected
            detected = True
            break
        time.sleep(0.05)

    # Close servo after detection or 3s
    set_servo_angle(servo_entry, 0, entry_angle)

    if detected:
        parking_data = fetch_parking_data()
        if not parking_data:
            return
        assigned_slots, available_slots = build_slot_lists(parking_data)
        if available_slots:
            slot = available_slots[0]
            floor = slot[0]
            parked_slots = parking_data[floor].get('parked_slots', [])
            free_slots = parking_data[floor].get('free_slots', [])
            parked_slots.append(slot)
            if slot in free_slots:
                free_slots.remove(slot)
            parking_data[floor]['parked_slots'] = parked_slots
            parking_data[floor]['free_slots'] = free_slots
            parking_data[floor]['parked_count'] = len(parked_slots)
            parking_data[floor]['free_count'] = len(free_slots)
            update_firebase(parking_data)

            display_paused = True
            with display_lock:
                lcd.clear()
                lcd.write(0, 0, "Assigned Slot:")
                lcd.write(0, 1, f"   {slot}")
            time.sleep(4)
            display_paused = False
        else:
            display_paused = True
            with display_lock:
                lcd.clear()
                lcd.write(0, 0, "Parking Full!")
            time.sleep(3)
            display_paused = False

# =====================================================
# EXIT SERVO MONITOR (BOOLEAN BASED, AUTO CLOSE 3s)
# =====================================================
def auto_close_gate():
    global current_exit_state, auto_close_thread
    time.sleep(3)
    set_servo_angle(servo_exit, 0, exit_angle)
    current_exit_state = 0
    auto_close_thread = None
    data = fetch_parking_data()
    if data:
        data['exit_gate'] = 0
        update_firebase(data)

def update_exit_servo(state):
    global current_exit_state, auto_close_thread
    with exit_lock:
        if state == 1 and current_exit_state == 0:
            set_servo_angle(servo_exit, 90, exit_angle)
            current_exit_state = 1
            if auto_close_thread is None:
                auto_close_thread = threading.Thread(target=auto_close_gate, daemon=True)
                auto_close_thread.start()

def monitor_exit_gate():
    while True:
        parking_data = fetch_parking_data()
        if parking_data and 'exit_gate' in parking_data:
            update_exit_servo(parking_data['exit_gate'])
        time.sleep(0.5)

threading.Thread(target=monitor_exit_gate, daemon=True).start()

# =====================================================
# MAIN LOOP
# =====================================================
try:
    update_firebase(initialize_parking_data())
    set_servo_angle(servo_entry, 0, entry_angle)
    set_servo_angle(servo_exit, 0, exit_angle)
    print("System started.")

    while True:
        if GPIO.input(IR_ENTRY) == 0:
            threading.Thread(target=handle_entry, daemon=True).start()
            time.sleep(0.6)
        time.sleep(0.1)

except KeyboardInterrupt:
    print("Stopping...")

finally:
    servo_entry.stop()
    servo_exit.stop()
    GPIO.cleanup()
    lcd.clear()
    print("Program stopped.")
