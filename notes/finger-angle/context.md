# Made with AI (Claude)

# Finger Angle Calculation — Lecture Notes

---

## 1. The Coordinate System

MediaPipe gives you 21 landmarks. Each one is a point in 3D space:

```
Landmark 8 (Index tip): x=0.426, y=0.345, z=-0.106
```

Think of it like this on your camera frame:

```
(0.0, 0.0) -------- (1.0, 0.0)
    |                    |
    |                    |
    |      YOUR HAND     |
    |                    |
(0.0, 1.0) -------- (1.0, 1.0)
```

- x increases left → right
- y increases top → bottom
- z is depth (negative = closer to camera)

So if your index fingertip is at x=0.426, y=0.345 — it's roughly in the upper middle of the frame.

---

## 2. The 21 Landmarks

MediaPipe tracks exactly 21 points on your hand:

```
                    8   12  16  20
                    |   |   |   |
                    7   11  15  19
                    |   |   |   |
                    6   10  14  18
                    |   |   |   |
                5   9   13  17
                 \  |   |   |
                  \ |   |   |
        4          \|   |   |
        |           \---+---+
        3            \  |
        |             \ |
        2              \|
        |               0 (WRIST)
        1
```

**Finger landmark groups:**
| Finger | Landmarks |
|--------|-----------|
| Thumb | 1, 2, 3, 4 |
| Index | 5, 6, 7, 8 |
| Middle | 9, 10, 11, 12 |
| Ring | 13, 14, 15, 16 |
| Pinky | 17, 18, 19, 20 |
| Wrist | 0 |

Each finger has 4 landmarks = 3 joints between them.

---

## 3. What is a Joint Angle?

Look at your index finger. It has 3 joints:

```
    [8] TIP
     |
    [7] ← JOINT 2 (DIP joint)
     |
    [6] ← JOINT 1 (PIP joint)
     |
    [5] BASE
```

When your finger is **straight**:
```
[5] --- [6] --- [7] --- [8]
         angle ≈ 180°
```

When your finger is **bent**:
```
[5] --- [6]
         \
          [7]
           \
            [8]
         angle ≈ 60°
```

The angle at landmark [6] tells you how bent that joint is.

**This angle is what we send to the servo.**
- 180° finger = servo at 180°
- 90° finger = servo at 90°
- 30° finger = servo at 30°

---

## 4. How Do We Calculate the Angle?

To find the angle at a joint (point B), we need 3 points:
- **A** = the point before the joint
- **B** = the joint itself  
- **C** = the point after the joint

### Step 1 — Create two vectors

A **vector** is just a direction. From B, we draw two lines:
- Vector 1: B → A (pointing backward along the finger)
- Vector 2: B → C (pointing forward along the finger)

```python
# Vector from B to A
vector1 = (A.x - B.x, A.y - B.y)

# Vector from B to C  
vector2 = (C.x - B.x, C.y - B.y)
```

### Step 2 — Dot product

The **dot product** of two vectors gives us a number that relates to the angle between them:

```
dot = (v1.x × v2.x) + (v1.y × v2.y)
```

```python
dot = (vector1[0] * vector2[0]) + (vector1[1] * vector2[1])
```

### Step 3 — Magnitudes

The **magnitude** is the length of a vector:

```
|v| = √(x² + y²)
```

```python
import math
mag1 = math.sqrt(vector1[0]**2 + vector1[1]**2)
mag2 = math.sqrt(vector2[0]**2 + vector2[1]**2)
```

### Step 4 — Cosine rule

The relationship between dot product, magnitudes, and angle:

```
cos(θ) = dot / (|v1| × |v2|)
```

So:
```python
cos_angle = dot / (mag1 * mag2)
```

### Step 5 — Get the actual angle

Use arccos (inverse cosine) to get the angle in radians, then convert to degrees:

```python
angle = math.degrees(math.acos(cos_angle))
```

---

## 5. Full Function

Putting it all together:

```python
import math

def calculate_angle(A, B, C):
    """
    Calculate the angle at point B, between lines A-B and B-C
    A, B, C are landmark objects with .x and .y attributes
    Returns angle in degrees
    """
    
    # Vectors from B to A and B to C
    vector1 = (A.x - B.x, A.y - B.y)
    vector2 = (C.x - B.x, C.y - B.y)
    
    # Dot product
    dot = (vector1[0] * vector2[0]) + (vector1[1] * vector2[1])
    
    # Magnitudes
    mag1 = math.sqrt(vector1[0]**2 + vector1[1]**2)
    mag2 = math.sqrt(vector2[0]**2 + vector2[1]**2)
    
    # Avoid division by zero
    if mag1 * mag2 == 0:
        return 0
    
    # Clamp to valid range for acos (-1 to 1)
    cos_angle = max(-1, min(1, dot / (mag1 * mag2)))
    
    # Return angle in degrees
    return math.degrees(math.acos(cos_angle))
```

---

## 6. Using It For Each Finger

For the **index finger middle joint** (landmark 6):

```python
A = hand[5]   # base
B = hand[6]   # the joint we care about
C = hand[7]   # above the joint

angle = calculate_angle(A, B, C)
print(f"Index PIP joint: {angle:.1f}°")
```

For all finger joints at once:

```python
finger_joints = {
    "thumb":  [(1,2,3),  (2,3,4)],
    "index":  [(5,6,7),  (6,7,8)],
    "middle": [(9,10,11),(10,11,12)],
    "ring":   [(13,14,15),(14,15,16)],
    "pinky":  [(17,18,19),(18,19,20)],
}

for finger_name, joints in finger_joints.items():
    for (a, b, c) in joints:
        angle = calculate_angle(hand[a], hand[b], hand[c])
        print(f"{finger_name} joint {b}: {angle:.1f}°")
```

---

## 7. Mapping Angle to Servo

The MG996R servo moves from 0° to 180°.

Your finger angle ranges roughly from 30° (fully bent) to 180° (fully straight).

We need to map finger angle → servo angle:

```python
def map_to_servo(finger_angle):
    """
    Map finger angle (30-180) to servo angle (0-180)
    """
    finger_min = 30    # fully bent
    finger_max = 180   # fully straight
    servo_min = 0
    servo_max = 180
    
    servo_angle = (finger_angle - finger_min) / (finger_max - finger_min) * (servo_max - servo_min)
    
    # Clamp to valid servo range
    return max(0, min(180, servo_angle))
```

---

## 8. The Full Pipeline So Far

```
Camera frame
    ↓
MediaPipe detects 21 landmarks (x, y, z per point)
    ↓
calculate_angle(A, B, C) for each finger joint
    ↓
map_to_servo(angle) converts to 0-180 range
    ↓
[Next step] Send to ESP32 via serial
    ↓
ESP32 moves MG996R servo to that angle
    ↓
ATOM's finger mirrors yours 🤖
```

---

## 9. Quick Reference

| Symbol | Meaning |
|--------|---------|
| A, B, C | Three consecutive landmarks |
| Vector | Direction from one point to another |
| Dot product | Measures how aligned two vectors are |
| Magnitude | Length of a vector |
| arccos | Inverse cosine — gives you the angle |
| degrees() | Converts radians to degrees |

---

## 10. Why 2D and Not 3D?

We use only x and y for now, ignoring z (depth).

Reason: z from a standard webcam is estimated not measured precisely. It's noisy and unreliable for angle calculation. A depth camera (like Intel RealSense) would give accurate z.

For now — x and y give us accurate enough finger angles for servo control.

When we add IMU sensors in Phase 6, those will give us precise 3D orientation for the full arm. But for the hand — 2D landmark angles work great.

---
