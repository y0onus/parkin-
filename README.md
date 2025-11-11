# Smart Parking System - Raspberry Pi
This project implements a smart parking-gate and display system using a Raspberry Pi, infrared sensors, servos, an I2C LCD and a Firebase realtime database.  
It also includes a public website where users can check free/occupied parking slots in real-time.

## Overview

### Hardware & Raspberry Pi Side

- Uses a Raspberry Pi running a Python script to  
  - Monitor entry sensor (`IR_ENTRY`) and entry-verification sensor (`IR_ENTRY_VERIFY`)  
  - Control two servos: one for the entry gate (`SERVO_ENTRY`), and one for the exit gate (`SERVO_EXIT`)  
  - Display live counts of parked and free slots on a 16×2 I2C LCD (via the `CharLCD1602` class)  
  - Communicate with a Firebase Realtime Database to fetch and update parking-slot data

- The `CharLCD1602` class handles low-level I2C commands to the LCD, including initialization, clearing, writing commands and sending characters.

- When a car is detected at entry and verified:  
  1. The entry gate servo opens (90°) for up to 3 seconds, waits for verification.  
  2. If verification succeeds, the first available slot is assigned, the database is updated, and the LCD displays the assigned slot.  
  3. If no slots are available, the LCD displays “Parking Full!”.

- Meanwhile, a background thread refreshes the LCD display every ~2 seconds with the total parked vs free slots, unless temporarily paused during assignment display.

- For the exit gate: the database contains a flag `exit_gate`. A separate thread monitors this flag, and when it becomes `1`, the exit gate servo opens and after 3 seconds auto-closes the gate and resets the flag.

### Database Schema (Firebase)

The Firebase data for all floors and slot states is structured in this JSON shape:

```json
{
  "A": {
    "parked_slots": [],
    "free_slots": [],
    "parked_count": 0,
    "free_count": 0
  },
  "B": {
    "parked_slots": [],
    "free_slots": [],
    "parked_count": 0,
    "free_count": 0
  },
  "C": {
    "parked_slots": [],
    "free_slots": [],
    "parked_count": 0,
    "free_count": 0
  },
  "exit_gate": 0
}
````

* Each floor (A, B, C) has arrays of `parked_slots` and `free_slots`, and counts for each.
* `exit_gate` is a numeric flag (0 or 1) triggered by the website (or other interface) to open the exit gate.

### Public Website

A companion website allows users (visitors) to view the current parking slot status—free vs occupied—on the different floors. Features include:

* Real-time (or frequently refreshed) display of each floor’s free slot count and maybe a visual map of slot codes (optional).
* When a slot is assigned by the Pi script, that reflectively updates on the website via the shared database.
* The website thus serves as a *public front-end* to the backend system, giving transparency to users and enabling them to decide where to park.
* Optionally: the site could allow users to reserve a slot (if you add that feature), or trigger the exit gate (via `exit_gate` flag) when they pay and leave.

### Setup & Usage

1. **Hardware wiring & connections**

   * Connect IR sensors at GPIO 21 (`IR_ENTRY`) and GPIO 16 (`IR_ENTRY_VERIFY`).
   * Connect servos to GPIO 26 (`SERVO_ENTRY`) and GPIO 19 (`SERVO_EXIT`) using PWM @ 50 Hz.
   * Connect I2C LCD at address `0x27` on I2C bus 1.
   * Ensure correct power supply, servo power separate if needed, sensor calibration.

2. **Software & dependencies**

   * Run on Raspberry Pi OS (or any Linux with GPIO & I2C support).
   * Install dependencies:

     ```bash
     sudo apt-get update
     sudo apt-get install python3-pip i2c-tools
     pip3 install smbus2 RPi.GPIO requests
     ```
   * Enable I2C interface via `raspi-config`, and ensure `i2cdetect -y 1` shows address `0x27`.

3. **Firebase setup**

   * Create Firebase Realtime Database, set rules appropriately (read/write as required).
   * Replace the placeholder URL `https://parkin-50303-default-rtdb.asia-southeast1.firebasedatabase.app/parking.json` in the script with *your own database URL*.
   * **Important:** Remove or secure any private keys or secrets from version control.

4. **Deploy the website**

   * Create a frontend (HTML/CSS/JS) to fetch and display the JSON database and show slot/parking status.
   * Host the site (e.g., GitHub Pages, Netlify, or your own server).
   * On the site, include visual mapping or simple lists: e.g., Floor A free slots: X, Floor B free slots: Y.

5. **Running the system**

   * Start the script: `python3 parking_system.py`.
   * On start, it initializes database (if empty) to a default state via `initialize_parking_data()`.
   * Ensure the LCD displays “System started.” and begins refreshing.
   * On entry detection/verification, slot assignment and display happen.
   * On website/other interface trigger setting `exit_gate: 1`, the exit gate opens & resets automatically.

## Code Structure

* `CharLCD1602` class: handles LCD commands and data.
* Global variables: floors list (`['C','B','A']`), slot order, locks, servo state holders.
* `initialize_parking_data()`: sets initial state for database with full/partial occupancy.
* `fetch_parking_data()` / `update_firebase(data)`: GET and PUT to Firebase.
* `build_slot_lists()` / `compute_totals()`: utilities to compute assigned vs available.
* `lcd_refresh_loop()`: background thread refreshing the LCD display.
* `handle_entry()`: entry logic triggered on IR sensor event.
* `monitor_exit_gate()` + `update_exit_servo(state)`: exit gate logic via database flag.
* Main loop: monitors `IR_ENTRY`, spawning entry handler thread as needed.

## Usage Tips

* If servos jitter or behave erratically, adjust the duty cycle calculation (the `2.5 + (angle / 18.0)` formula) or add calibration delays.
* Ensure the IR sensors are stable (debounced) and mounted so false positives are minimized.
* For the website, use a polling interval (e.g., every 2–5 seconds) or Firebase real-time listeners if you switch to WebSockets/SDK for live updates.
* Protect your Firebase URL and database rules if you expand to allow users to reserve or trigger gates.
* Label your slot codes clearly: the script uses codes like “A01”, “B05”, “C24” etc.

## JSON Example

Here’s a sample JSON entry you can include in the README for clarity:

```json
{
  "A": {
    "parked_slots": ["A01","A02","A03"],
    "free_slots": ["A04","A05", "..."],
    "parked_count": 3,
    "free_count": 21
  },
  "B": {
    "parked_slots": ["B01","B02"],
    "free_slots": ["B03","B04", "..."],
    "parked_count": 2,
    "free_count": 22
  },
  "C": {
    "parked_slots": ["C01","C02","C03","C04"],
    "free_slots": ["C05","C06", "..."],
    "parked_count": 4,
    "free_count": 20
  },
  "exit_gate": 0
}
```

## Screenshots / Visuals

![Slot Layout Preview](https://github.com/JeffIsEpik/Jeffisepik.github.io/blob/main/assets/s8.jpg?raw=true)
![Entrance / Gate Preview](https://github.com/JeffIsEpik/Jeffisepik.github.io/blob/main/assets/s9.jpg?raw=true)

---

## License

MIT License – feel free to reuse, modify and share.

---
