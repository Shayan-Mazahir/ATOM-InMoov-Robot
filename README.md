# Work halted due to EMG sensor not working

> Works has been on pause for a few months now due to EMG sensor not making any sense, I've tried researching about it but am unable to do so. I've tried contacting various people on Discord (servers) and Reddit but have no luck so far. Project isn't abandoned just hella slow... Any and all my research is linked here: 

# ATOM

> A humanoid robot that mirrors your movement in real time, built on the open-source [InMoov](https://inmoov.fr) platform.
>
> Inspired by ATOM from *Real Steel*.

Hold your hand in front of a webcam and the robot hand copies it. No gloves, no sensors strapped to you, just a camera, some math, and five servos.

**Update:** I'll be switching from ESP32 to Arduino, I somehow burnt my ESP32, don't even know how, plugged it in yesterday ma guy starting smoking. Will probably jump from Arduino to RasberryPI or STM32, it's not like I am taking baby steps, I am jumping and burning up components as I go lol (help, my budget..)


**Status:** Phase 0 -> ~~prototype hand, tethered over USB serial. The software pipeline works end to end.~~ Done, and works

> ### ⚠️ This README lags behind the build
>
> The hardware moves faster than the docs do. If something here looks out of date, it probably is.
>
> I try to update this file **every Sunday**. If the last commit is older than that and you can see major changes in the repo, trust the code and the commit history over this page.

---

## How It Works

```
[Webcam]
   |  frames
[Python + MediaPipe]        detects 21 hand landmarks
   |  x/y coordinates
[Angle calculation]         dot product -> joint angle in degrees
   |  0 to 180 per finger
[Smoothing + rate limit]    rolling average, 20 Hz
   |  CSV "90,45,120,60,80\n"
[USB Serial @ 921600 baud]
   |
[ESP32]                     parses CSV, clamps to 0-180
   |  PWM
[5x MG996R servos]
   |  fishing-line tendons
[3D-printed hand]
```

The core idea: every finger joint is three landmarks (A, B, C). The angle at **B** comes from the dot product, then gets mapped from your calibrated open/closed range onto the servo's 0-180 range.

The math is worked through from scratch in [notes/finger-angle/context.md](notes/finger-angle/context.md).

---

## Quickstart

### 1. Hardware

| Component | Model | Qty |
|---|---|---|
| Microcontroller | ESP32 DevKit V1 | 1 |
| Servos | MG996R (180°) | 5 |
| Power supply | 5V, **3A minimum** | 1 |

Wire each servo signal line to the ESP32, and **connect a common ground** between the ESP32 and the servo power supply. Without it the servos won't respond properly.

| GPIO | Servo | Joint |
|---|---|---|
| 18 | 0 | Index (`index_6`) |
| 19 | 1 | Middle (`middle_10`) |
| 21 | 2 | Ring (`ring_14`) |
| 22 | 3 | Pinky (`pinky_18`) |
| 23 | 4 | Thumb (`thumb_3`) |

> ⚠️ Five servos under load can pull around 2.5A. Do **not** power them off the ESP32's VIN pin.

Full pinout, power budget and wiring diagrams are in [notes/hardware_documentation.md](notes/hardware_documentation.md).

### 2. Flash the ESP32

Open [sketch_apr24b/sketch_apr24b.ino](sketch_apr24b/sketch_apr24b.ino) in the Arduino IDE, install the **ESP32Servo** library, pick your ESP32 board, and upload.

### 3. Run the tracker

```bash
# Set up the Python environment
python3 -m venv ~/atom_env
source ~/atom_env/bin/activate
pip install -r requirements.txt

# Give yourself access to the serial port (Linux)
sudo chmod 666 /dev/ttyUSB0

# Start tracking
python hand_track.py
```

On launch it runs a **3 second calibration** for each pose:

1. **Straighten your hand fully** -> records your open-hand maximum
2. **Make a fist** -> records your closed minimum

Tracking starts right after. Press **`q`** to quit.

### 4. Configure

Everything tunable lives in [protocol.json](protocol.json), so you shouldn't need to touch the code:

| Key | Default | What it does |
|---|---|---|
| `serial.port` | `/dev/ttyUSB0` | Serial device for the ESP32 |
| `serial.baud` | `921600` | Has to match the firmware |
| `smoothing.buffer_size` | `3` | Rolling average window. Raise it if jittery, lower it if laggy |
| `send_interval` | `0.05` | Seconds between sends (20 Hz) |
| `servo_map` | | Maps joint keys to servo slots |

---

## Repository Layout

| Path | Contents |
|---|---|
| [hand_track.py](hand_track.py) | Python pipeline: capture, landmarks, angles, smoothing, serial |
| [sketch_apr24b/](sketch_apr24b/) | ESP32 firmware: serial parsing and servo control |
| [protocol.json](protocol.json) | Shared config (ports, servo map, tuning) |
| [models/](models/) | MediaPipe `hand_landmarker.task` model |
| [stl-files/](stl-files/) | 3D print files, sorted by part and support requirement |
| [notes/](notes/) | Hardware docs and background notes |
| [docs/](docs/) | Source for the web-based STL browser |
| [potential_bugs.md](potential_bugs.md) | Known issues and where they stand |

### How the STLs are sorted

Parts are split into `support/` and `no support/` folders. That split is **what actually worked on a Flashforge Adventurer 5M**, not the official InMoov recommendation. A few parts listed upstream as needing no supports would not print here without manually drawn tree supports.

Browse them online: **[shayan-mazahir.github.io/ATOM-InMoov-Robot](https://shayan-mazahir.github.io/ATOM-InMoov-Robot)**

---

## 3D Printing

**Print the [calibrator](stl-files/hands/Calibrator.stl) first. Always.** It tells you whether screw holes and joint pins come out the right size on *your* printer, and saves you from reprinting real parts later.

The full guide, covering hole compensation per slicer, support strategy and a troubleshooting table, is in [stl-files/printing_setting_and_notes.txt](stl-files/printing_setting_and_notes.txt).

> Using a servo other than the recommended JX PDI-6225MG-300? Some parts will need their hole compensation adjusted to fit the horn. See the notes inside the `no support/` folders.

---

## Roadmap

| Phase | Milestone |
|---|---|
| **0** | Prototype hand, validate the software pipeline 🔄 |
| **1** | Right arm: hand -> forearm -> bicep -> shoulder, custom PCB, wireless |
| **2** | Left arm, dual-hand tracking |
| **3** | Torso, backbone movement, IMU integration |
| **4** | Neck and head tracking |
| **5** | Walking. Done when one foot lifts 1mm off the ground 🎯 |

Upgrades planned along the way: **PCA9685** servo driver, **MPU6050** IMUs for tracking that doesn't depend on the camera, and **MyoWare EMG** for muscle-intent control.

WiFi UDP transport is scaffolded but commented out in both `hand_track.py` and the firmware. Serial is the active path for now.

---

## Known Issues

- **Ambiguous angles** -> some partially curled finger poses read close to a closed fist, which could cause servo hunting. Untested until the hand is assembled.
- **Servo jitter** -> mostly handled in software with a rolling average and rate limiting. Final tuning needs hardware.
- **Open loop** -> the servos have no position feedback.

Details and proposed fixes in [potential_bugs.md](potential_bugs.md).

---

## Credits

Built on **[InMoov](https://inmoov.fr)** by Gael Langevin, the open-source 3D-printed humanoid robot project. Every STL here originates there and is redistributed under InMoov's **Creative Commons BY-NC** terms. This project is non-commercial.

- InMoov hand build guide: <https://inmoov.fr/inmoov-hand/>
- InMoov community forum: <https://inmoov.fr/forum/>
