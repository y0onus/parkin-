# Smart Parking System with Raspberry Pi + Firebase + Web Interface

This project is a **Smart Parking and Slot Management System** designed to automate vehicle entry/exit and provide real-time parking availability both on-site and online. The system uses a Raspberry Pi to control IR sensors, servo gates, and an LCD, while a **Firebase Realtime Database** connects the hardware to two different websites:

1. **Admin Website** (for parking staff and security)
2. **Public Website** (for users to check free parking slots anytime)

---

## System Overview

### Hardware Functions (Raspberry Pi)
- Detects incoming vehicles using IR sensors.
- Opens entry gate automatically and assigns the **next available slot**.
- Displays assigned slot on LCD.
- Monitors exit gate state through Firebase and closes it automatically after 3 seconds.
- Continuously updates total parked and free slots.

### Cloud Backend (Firebase Realtime Database)
Stores:
- Which slots are taken
- Which slots are free
- Count of available spaces per floor
- Exit gate state

```json
{
  "A": { "parked_slots": [], "free_slots": [], "parked_count": 0, "free_count": 0 },
  "B": { ... },
  "C": { ... },
  "exit_gate": 0
}
```

The database updates **live** and is used by both websites.

---

## Web Interfaces

### 1. Admin Dashboard Website (Staff Use)
This website is designed for parking operators / reception / guards.

**Features:**
- Live display of parked and free slot counts.
- Floor-by-floor detailed status (green = free, red = taken).
- Button to **remotely open the exit gate** by setting `exit_gate = 1`.
- Auto refresh (no reload needed due to Firebase live event listeners).

**Purpose:**
- Enables staff to manage parking without manually checking floors.
- Removes the need for radio/walkie communication.

---

### 2. Public Parking Status Website (For Users)
A simpler, clean public-facing webpage that **anyone can check before arriving**.

**Features:**
- Shows:
  - Total available spaces
  - Floor availability
  - Visual slot map or simple count view (depends on UI version)
- No controls or admin access
- Works on mobile

**Purpose:**
- Helps users know **if parking is available before they come**.
- Reduces crowding and waiting at the parking entrance.

---

## Why This Matters

This project helps:
- Reduce traffic and waiting time at parking entrances.
- Improve organization of multi-floor parking systems.
- Give transparency and convenience to the public.
- Provide digital monitoring that can scale to malls, hospitals, schools, stadiums, or apartment complexes.

---

## Hardware Used

| Component | Purpose |
|---------|---------|
| Raspberry Pi | Core controller |
| IR Sensors (2×) | Vehicle detect & confirm entry |
| Servo Motors (2×) | Entry and Exit gate barriers |
| 16x2 I2C LCD | Displays assigned slot and live counts |
| Firebase Realtime DB | Cloud data synchronization |

---

## Running the System

Install dependencies:

```bash
sudo apt-get install python3-smbus python3-rpi.gpio
pip install requests
