# Hand Mechanics for Someone Who Came Into CS Because They Hate Biology

---

## Disclaimer

This document contains biology. I know. I'm sorry. But it turns out understanding how your hand works is kind of important when you're trying to build one. Bear with me — I'll keep it as engineering-flavoured as possible.

---

## 1. Your Hand is Just a Robot

Genuinely. Your hand is a tendon-driven robotic manipulator that runs on electrochemical signals. The only difference between your hand and InMoov is the actuators and the power source.

Let's break it down like an engineer would.

---

## 2. The Hardware

Your hand has:

```
Actuators:    Muscles (in your FOREARM, not your hand)
Transmission: Tendons (biological cables running from forearm → fingertips)
Structure:    Bones (the rigid frame)
Joints:       Cartilage + ligaments (the pivot points)
Sensors:      Nerve endings (position, pressure, temperature feedback)
Controller:   Your brain (running on ~20 watts somehow)
Power:        ATP (adenosine triphosphate — basically biological battery)
```

InMoov has:
```
Actuators:    Servo motors (in the forearm/palm)
Transmission: Fishing line (running from servo → fingertips)
Structure:    PLA plastic (the rigid frame)
Joints:       Printed pivot points
Sensors:      MPU6050, cameras, EMG (eventually)
Controller:   ESP32 + your Python pipeline
Power:        LiPo battery
```

Same architecture. Different materials.

---

## 3. The Tendon System — How Your Fingers Actually Work

Here's the part that will blow your mind.

**Your finger muscles are not in your fingers.**

Go ahead, squeeze your fist tight and feel your hand. Nothing much moving under the skin of your fingers right? Now feel your forearm while doing the same thing.

THERE it is. That's where the action is.

```
FOREARM
┌─────────────────────┐
│  Flexor muscles     │ ← these contract when you curl fingers
│  Extensor muscles   │ ← these contract when you straighten fingers
└──────────┬──────────┘
           │
           │  tendons (biological cables)
           │
           ▼
        WRIST
           │
           │  tendons continue through carpal tunnel
           │
           ▼
         PALM
           │
           │  tendons split toward each finger
           │
           ▼
       FINGERS
    ┌──────────────┐
    │  MCP joint   │ ← tendon pulls here first
    │  PIP joint   │ ← then here
    │  DIP joint   │ ← then here
    └──────────────┘
```

One muscle contraction in your forearm → tendon pulls → all three finger joints curl simultaneously. That's it. That's the whole mechanism.

---

## 4. The Three Finger Joints

Each finger (except thumb) has 3 joints. Here's what they're called and what they do:

```
    [TIP]
      |
   [DIP] ← Distal Interphalangeal — top joint, small range
      |
   [PIP] ← Proximal Interphalangeal — middle joint, LARGEST range ✅
      |
   [MCP] ← Metacarpophalangeal — base joint, connects to palm
      |
  [PALM]
```

**Why PIP is the most useful for us:**

| Joint | Range of Motion | Sensitivity | Usefulness |
|-------|----------------|-------------|------------|
| MCP   | ~90°           | Low         | ⭐⭐       |
| PIP   | ~120°          | High        | ⭐⭐⭐⭐⭐  |
| DIP   | ~80°           | Low         | ⭐⭐       |

PIP has the largest angular change between straight and fully bent. When you curl your finger, PIP moves the most. That makes it the best proxy for overall finger state.

DIP basically just follows PIP anyway — they're mechanically linked. Reading DIP would be redundant.

---

## 5. Why All Joints Move Together

This is the key insight for why 1 servo can control a whole finger.

The tendons don't attach to just one joint. They run along the entire length of the finger, threading through pulley-like structures (called tendon sheaths) at each joint.

When the tendon is pulled:
```
Tendon pulled ──► MCP begins to flex
                ──► PIP begins to flex  (slightly delayed, mechanically)
                ──► DIP begins to flex  (follows PIP)
```

All three joints curl in a coordinated, natural sequence. You don't consciously control each joint — the mechanical design does it automatically.

**InMoov replicates this exactly:**
- Fishing line = tendon
- Servo pulling fishing line = forearm muscle contracting
- All finger joints curl together = same result

The elastic band or spring returning the finger = your extensor tendons on the back of your hand.

---

## 6. The EMG Connection

This is why EMG is so powerful and why it's our north star for ATOM.

EMG (electromyography) reads the electrical signals from your forearm muscles — the actual source of the movement, not the result.

```
Brain sends signal
      ↓
Forearm muscle receives signal → fires electrically
      ↓                              ↑
Muscle contracts                  EMG reads THIS
      ↓
Tendon pulls
      ↓
Finger curls
```

By reading the muscle signal directly, we get the intent before the movement is even fully complete. The robot reacts faster than if it was watching the finger move.

That's why professional prosthetics use EMG. That's why it's the endgame for ATOM.

Camera tracking reads the result.
IMU reads the motion.
EMG reads the intent.

Each phase gets closer to the source. 🎯

---

## 7. Mapping This to Our Code

So here's how all this biology translates to what we built:

```python
FINGER_JOINTS = {
    "thumb":  [(1,2,3),   (2,3,4)],
    "index":  [(5,6,7),   (6,7,8)],    # (5,6,7) = MCP-PIP-DIP for index
    "middle": [(9,10,11), (10,11,12)],
    "ring":   [(13,14,15),(14,15,16)],
    "pinky":  [(17,18,19),(18,19,20)],
}
```

We calculate angle at B (the middle point) for each triplet.

For index finger: `calculate_angle(hand[5], hand[6], hand[7])`
- hand[5] = MCP (A)
- hand[6] = PIP (B) ← the joint we measure
- hand[7] = DIP (C)

The angle at PIP tells us how bent the whole finger is.

That angle → `map_to_servo()` → servo angle → servo pulls fishing line → all three InMoov finger joints curl.

**One measurement. One servo. Whole finger moves.**

Just like your forearm muscle → tendon → whole finger.

---

## 8. The Full Comparison

| Biological System | ATOM / InMoov |
|------------------|---------------|
| Forearm flexor muscle | MG996R servo |
| Tendon | Fishing line |
| Tendon sheath / pulley | Printed guides in finger |
| Extensor muscle | Elastic band / spring |
| MCP, PIP, DIP joints | Printed pivot points |
| Nerve signal from brain | Serial data from ESP32 |
| Brain motor cortex | Your Python pipeline |
| EMG signal | MyoWare 2.0 sensor (Phase 7) |
| Proprioception | IMU sensors (Phase 6) |

---

## 9. The Thumb is Weird

The thumb has a different joint structure and moves in more directions than the other fingers (opposition — the ability to touch all other fingers). 

This is why thumb control in robotics is notoriously difficult. InMoov's thumb is simplified — it handles basic flexion but not full opposition.

For now, don't overthink the thumb. Get the four fingers working first.

---

## 10. Summary — The Three Things to Remember

```
1. Muscles are in your forearm, not your fingers
   → Servo goes in forearm/palm, not in finger joints

2. One tendon controls multiple joints simultaneously  
   → One servo controls whole finger via fishing line

3. PIP is the best measurement of overall finger bend
   → We track PIP angle and map it to servo position
```

That's all the biology you need. You can go back to hating it now.

---

*"Biology is just slow hardware engineering."*

