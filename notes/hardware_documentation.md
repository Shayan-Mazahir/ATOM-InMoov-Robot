# ATOM Hardware Documentation
> Version 1.0 — Prototype (Breadboard)
> For future PCB/Schematic design reference

---

## System Overview

```
[Laptop Camera]
      ↓
[Laptop - Python]
      ↓ Serial (USB / future: WiFi UDP)
[ESP32 Main Controller]
      ↓
[PCA9685 Servo Driver] ← future upgrade
      ↓
[MG996R Servos x5]
      ↓
[InMoov Hand - Tendon Driven]
```

---

## Components List

### Microcontroller
| Component | Model | Qty | Notes |
|-----------|-------|-----|-------|
| Microcontroller | ESP32 DevKit V1 | 1 | Main brain, handles serial + servo PWM |

### Actuators
| Component | Model | Qty | Notes |
|-----------|-------|-----|-------|
| Servo Motor | MG996R 180° | 5 | One per finger, metal gear, high torque |

### Power
| Component | Spec | Qty | Notes |
|-----------|------|-----|-------|
| Power Supply | 5V DC | 1 | Powers servos — separate from ESP32 logic power |

### Future Components (Phase 3+)
| Component | Model | Purpose |
|-----------|-------|---------|
| Servo Driver | PCA9685 | I2C servo control — replaces direct PWM pins |
| IMU Sensor | MPU6050 | Arm joint tracking (Phase 6) |
| EMG Sensor | MyoWare 2.0 | Muscle signal control (Phase 7) |
| LiPo Battery | TBD | Wireless power when USB removed |

---

## ESP32 Pin Assignments

### Current (Prototype)
| GPIO Pin | Connected To | Signal Type | Notes |
|----------|-------------|-------------|-------|
| GPIO 18 | Servo 0 (Index) | PWM | index_6 joint |
| GPIO 19 | Servo 1 (Middle) | PWM | middle_10 joint |
| GPIO 21 | Servo 2 (Ring) | PWM | ring_14 joint |
| GPIO 22 | Servo 3 (Pinky) | PWM | pinky_18 joint |
| GPIO 23 | Servo 4 (Thumb) | PWM | thumb_3 joint |
| USB | Laptop Serial | UART | /dev/ttyUSB0 @ 921600 baud |
| VIN (5V) | Servo Power Rail | Power | Shared with external supply GND |
| GND | Common Ground | GND | Shared with servo power supply |

### Future (PCB with PCA9685)
| GPIO Pin | Connected To | Signal Type | Notes |
|----------|-------------|-------------|-------|
| GPIO 21 | PCA9685 SDA | I2C Data | Replaces direct PWM |
| GPIO 22 | PCA9685 SCL | I2C Clock | Replaces direct PWM |
| GPIO XX | MPU6050 SDA | I2C Data | Shared I2C bus |
| GPIO XX | MPU6050 SCL | I2C Clock | Shared I2C bus |
| GPIO XX | MyoWare Signal | Analog | EMG muscle signal |

> Note: When moving to PCA9685, GPIO 21 and 22 will be repurposed for I2C.
> Reassign servo control to PCA9685 channels 0-4.

---

## Wiring Diagram (Prototype)

### Servo Wiring (per servo)
```
MG996R          ESP32 / Power Supply
------          -------------------
Brown (GND) --> Common GND
Red (VCC)   --> 5V Power Supply (+)
Orange (SIG)--> GPIO Pin (18/19/21/22/23)
```

### Power Setup
```
[5V Power Supply]
      +5V ──────────────────── Servo Red wires (all 5)
      GND ──────────────────── Servo Brown wires (all 5)
                    └────────── ESP32 GND (common ground)

[ESP32]
      VIN ── (optional, if powering ESP32 from same supply)
      GND ── Common GND
      GPIO ── Servo signal wires
```

> ⚠️ IMPORTANT: Always connect GND between ESP32 and power supply.
> Without common ground, servo signals won't work correctly.

---

## Serial Communication Protocol

### Current (USB Serial)
| Parameter | Value |
|-----------|-------|
| Port | /dev/ttyUSB0 (Linux) |
| Baud Rate | 921600 |
| Format | CSV: `"90,45,120,60,80\n"` |
| Send Rate | 50ms interval (20Hz) |

### Message Format
```
"index,middle,ring,pinky,thumb\n"
 0-180, 0-180, 0-180, 0-180, 0-180
```

Example:
```
"180,90,45,120,60\n"
 ↑    ↑   ↑   ↑    ↑
 idx  mid rng pky  thm
```

### Future (WiFi UDP)
| Parameter | Value |
|-----------|-------|
| Protocol | UDP |
| Port | TBD |
| Format | Same CSV format |
| Send Rate | 50ms interval (20Hz) |

---

## Power Budget (Prototype)

| Component | Voltage | Current (idle) | Current (load) |
|-----------|---------|----------------|----------------|
| ESP32 | 3.3V | ~80mA | ~240mA |
| MG996R x1 | 5V | ~10mA | ~500mA |
| MG996R x5 | 5V | ~50mA | ~2500mA |
| **Total** | | **~130mA** | **~2740mA** |

> ⚠️ 5 servos under load can draw up to 2.5A.
> Use a power supply rated for at least 3A at 5V.
> Do NOT power all 5 servos from ESP32 VIN — insufficient current.

---

## PCB Design Notes (Future)

### Requirements for V2 PCB
- ESP32 footprint or ESP32 module header
- PCA9685 I2C servo driver (16 channel — future expansion)
- 5V voltage regulator or LiPo charging circuit
- Servo connectors x16 (3-pin JST or standard servo header)
- I2C headers for MPU6050 expansion
- Analog input for MyoWare EMG sensor
- USB-C for programming and serial
- Status LEDs (power, serial activity, servo active)
- Reset button
- decoupling capacitors on power rails

### Recommended PCB Tool
- **KiCad** (free, open source, industry standard)

### Key Design Considerations
- Separate power planes for logic (3.3V) and servo (5V)
- Thick traces on servo power rails (minimum 1mm for 2.5A)
- Common ground plane
- Keep PWM signal traces away from power traces
- Add TVS diodes on servo power input for spike protection

---

## Known Issues & Limitations

See `potential_bugs.md` for full list.

| Issue | Impact | Status |
|-------|--------|--------|
| Servo jitter | Medium | Smoothing implemented, needs hardware tuning |
| Single joint per finger | Low | Mechanical tendon handles second joint |
| USB tethered | Medium | WiFi UDP planned for Phase 5 |
| No position feedback | Medium | Servos are open loop, no encoder |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025 | Initial prototype — 5 servos, USB serial, breadboard |
| 2.0 | TBD | PCA9685, custom PCB, WiFi |
| 3.0 | TBD | IMU sensors added |
| 4.0 | TBD | EMG muscle control |

---

