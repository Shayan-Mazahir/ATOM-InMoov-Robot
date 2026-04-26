import math
import time
import cv2
import mediapipe as mp
import serial
from collections import deque
import json

'''
# future wifi implementation
import socket
from dotenv import load_dotenv
import os

load_dotenv()
'''
last_send_time = 0

# ------- Config Loading -------------------------------------------------------
# Load serial port, smoothing settings, servo map, and send interval from file
with open('protocol.json') as f:
    protocol = json.load(f)

SERVO_MAP = protocol['servo_map']         # Maps joint keys (e.g. "index_6") to servo slot indices
ser = serial.Serial(protocol['serial']['port'], protocol['serial']['baud'], timeout=1)
'''
# future wifi implementation
ESP32_IP = os.getenv('ESP32_IP')
UDP_PORT = protocol['udp']['port']
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
'''

# smooth_buffer = deque(maxlen = protocol['smoothing']['buffer_size'])
SEND_INTERVAL = protocol['send_interval'] # Minimum seconds between serial transmissions

# ------- MediaPipe Tasks API Setup --------------------------------------------
# Aliases for cleaner code
BaseOptions = mp.tasks.BaseOptions
HandLandmarker = mp.tasks.vision.HandLandmarker
HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
HandLandmarkerResult = mp.tasks.vision.HandLandmarkerResult
VisionRunningMode = mp.tasks.vision.RunningMode

# Shared state between the MediaPipe callback and the main loop.
# MediaPipe runs detection asynchronously, so we store the latest result here.
latest_landmarks = []

# Joint triplets (A, B, C) per finger, where B is the vertex of the angle.
# Indices map to MediaPipe's 21-point hand landmark model.
FINGER_JOINTS = {
    "thumb":  [(1,2,3),   (2,3,4)],
    "index":  [(5,6,7),   (6,7,8)],
    "middle": [(9,10,11), (10,11,12)],
    "ring":   [(13,14,15),(14,15,16)],
    "pinky":  [(17,18,19),(18,19,20)],
}


def calculate_angle(A, B, C):
    """
    Calculate the angle at joint B, formed by points A-B-C.

    Uses the dot product formula:
        cos(θ) = (BA · BC) / (|BA| * |BC|)

    Args:
        A, B, C: MediaPipe landmark objects with .x and .y attributes.

    Returns:
        Angle in degrees (float).
    """
    # Vectors from B toward A and B toward C
    V1 = (A.x - B.x, A.y - B.y)
    V2 = (C.x - B.x, C.y - B.y)

    dot_product = (V1[0] * V2[0]) + (V1[1] * V2[1])

    V1_magnitude = math.sqrt(V1[0]**2 + V1[1]**2)
    V2_magnitude = math.sqrt(V2[0]**2 + V2[1]**2)

    angle_radians = math.acos(dot_product / (V1_magnitude * V2_magnitude))

    return math.degrees(angle_radians)


def calibrate(cap, landmarker):
    """
    Collect baseline joint angles for a flat hand and a closed fist.

    Runs two 3-second capture phases while displaying a countdown on screen.
    Averages all detected angles per joint across frames to get stable
    reference values used later for servo mapping.

    Args:
        cap:        OpenCV VideoCapture object (webcam feed).
        landmarker: MediaPipe HandLandmarker instance.

    Returns:
        calibration_max (dict): Average angles for a fully extended hand.
        calibration_min (dict): Average angles for a fully closed fist.
    """
    calibration_max = {}  # Reference angles for open/straight hand
    calibration_min = {}  # Reference angles for closed fist

    phases = [
        ("Straighten your hand fully!", calibration_max),
        ("Make a fist!", calibration_min),
    ]

    for message, calib_dict in phases:
        angle_sums = {}   # Running total of angles per joint key
        frame_count = 0   # Number of frames where a hand was detected

        start_time = time.time()

        while time.time() - start_time < 3:
            ret, frame = cap.read()
            if not ret:
                break

            # Overlay instruction text and countdown on the camera frame
            elapsed = time.time() - start_time
            remaining = int(3 - elapsed) + 1
            cv2.putText(frame, message, (30, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(frame, str(remaining), (30, 120),
                        cv2.FONT_HERSHEY_SIMPLEX, 3, (0, 255, 255), 3)
            cv2.imshow("Calibration", frame)
            cv2.waitKey(1)

            # Convert frame to RGB and send to MediaPipe asynchronously
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            global timestamp
            timestamp += 1
            landmarker.detect_async(mp_image, timestamp)

            # Accumulate joint angles across all detected hands
            if latest_landmarks:
                for hand in latest_landmarks:
                    for finger_name, joints in FINGER_JOINTS.items():
                        for (a, b, c) in joints:
                            angle = calculate_angle(hand[a], hand[b], hand[c])
                            key = f"{finger_name}_{b}"  # e.g. "index_6"

                            if key not in angle_sums:
                                angle_sums[key] = 0
                            angle_sums[key] += angle

                frame_count += 1

        # Average each joint's accumulated angles over all captured frames
        for key, total in angle_sums.items():
            calib_dict[key] = total / frame_count

        print(f"Calibration phase done: {message}")
        print(calib_dict)

    return calibration_max, calibration_min


def map_to_servo(angle, min_angle, max_angle):
    """
    Map a joint angle to a servo motor position (0-180°).

    Linearly scales the measured angle from the calibrated [min, max] range
    to the servo's [0, 180] range, then clamps the result to stay in bounds.

    Args:
        angle:     Current measured joint angle (degrees).
        min_angle: Calibrated minimum (closed fist angle).
        max_angle: Calibrated maximum (open hand angle).

    Returns:
        Servo angle in degrees, clamped to [0, 180].
    """
    servo_angle = ((angle - min_angle) / (max_angle - min_angle)) * 180

    # Clamp to valid servo range - prevents out-of-bound commands
    return max(0, min(180, servo_angle))


def print_result(result: HandLandmarkerResult, output_image: mp.Image, timestamp_ms: int):
    """
    MediaPipe async callback - fires every time hand detection completes.

    Stores the latest landmarks globally so the main loop can read them
    without blocking. Replaces the previous result each frame.
    """
    global latest_landmarks
    latest_landmarks = result.hand_landmarks


# ------- Landmarker Configuration ---------------------------------------------
# LIVE_STREAM mode processes frames asynchronously - results arrive via callback
options = HandLandmarkerOptions(
    base_options=BaseOptions(model_asset_path='./models/hand_landmarker.task'),
    running_mode=VisionRunningMode.LIVE_STREAM,
    num_hands=1,                  # Track one hand at a time
    result_callback=print_result
)

cap = cv2.VideoCapture(0)  # 0 = default webcam

# MediaPipe requires a strictly increasing timestamp (in ms) for LIVE_STREAM mode
timestamp = 0

# One deque per joint key - lazily initialized in the main loop
smooth_buffers = {}

# ------- Main Loop ------------------------------------------------------------
with HandLandmarker.create_from_options(options) as landmarker:

    # Collect calibration data before starting tracking
    calibration_max, calibration_min = calibrate(cap, landmarker)

    while True:
        ret, frame = cap.read()
        if not ret:
            break  # Camera disconnected or failed

        # Convert to RGB for MediaPipe (OpenCV uses BGR by default)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        # Submit frame for async detection; result arrives via print_result()
        timestamp += 1
        landmarker.detect_async(mp_image, timestamp)

        if latest_landmarks:
            for hand in latest_landmarks:

                # Draw green dots only on the three landmark points of each
                # active joint (i.e. joints present in SERVO_MAP)
                h, w, _ = frame.shape
                for finger_name, joints in FINGER_JOINTS.items():
                    for (a, b, c) in joints:
                        key = f"{finger_name}_{b}"
                        if key in SERVO_MAP:
                            for idx in [a, b, c]:
                                cx, cy = int(hand[idx].x * w), int(hand[idx].y * h)
                                cv2.circle(frame, (cx, cy), 5, (0, 255, 0), -1)

                # One slot per servo channel; order matches protocol.json
                servo_values = [0] * 5

                for finger_name, joints in FINGER_JOINTS.items():
                    for (a, b, c) in joints:
                        key = f"{finger_name}_{b}"

                        # Skip joints not wired to a servo
                        if key not in SERVO_MAP:
                            continue

                        angle = calculate_angle(hand[a], hand[b], hand[c])
                        servo = map_to_servo(angle, calibration_min[key], calibration_max[key])

                        # Create a smoothing buffer for this joint on first encounter,
                        # pre-filled with 90° so it doesn't start from zero
                        if key not in smooth_buffers:
                            smooth_buffers[key] = deque(
                                [90] * protocol['smoothing']['buffer_size'],
                                maxlen=protocol['smoothing']['buffer_size']
                            )

                        # Append latest value and compute rolling average
                        smooth_buffers[key].append(servo)
                        smoothed = sum(smooth_buffers[key]) / len(smooth_buffers[key])

                        # Write smoothed angle into the correct serial slot
                        slot = SERVO_MAP[key]
                        servo_values[slot] = int(smoothed)

                        print(f"{key}: {angle:.1f}° → servo slot {slot}: {int(smoothed)}°")

                # Rate-limited serial send - transmit all 5 slots as "a,b,c,d,e\n"
                current_time = time.time()
                if current_time - last_send_time >= SEND_INTERVAL:
                    message = ",".join(map(str, servo_values)) + "\n"
                    ser.write(message.encode()) 
                    # sock.sendto(message.encode(), (ESP32_IP, UDP_PORT)) # future wifi implementation
                    last_send_time = current_time

        cv2.imshow("Hand Tracking", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break  # Press Q to exit

# ------- Cleanup --------------------------------------------------------------
cap.release()
cv2.destroyAllWindows()
# sock.close() # future wifi implementation