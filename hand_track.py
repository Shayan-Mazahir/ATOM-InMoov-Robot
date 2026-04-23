import math
import time
import cv2
import mediapipe as mp

# MediaPipe Tasks API setup
BaseOptions = mp.tasks.BaseOptions
HandLandmarker = mp.tasks.vision.HandLandmarker
HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
HandLandmarkerResult = mp.tasks.vision.HandLandmarkerResult
VisionRunningMode = mp.tasks.vision.RunningMode

# Stores the latest detected landmarks - shared between callback and main loop
latest_landmarks = []

# Finger anatomy doesn't change, hence hardcoded
FINGER_JOINTS = {
    "thumb":  [(1,2,3),   (2,3,4)],
    "index":  [(5,6,7),   (6,7,8)],
    "middle": [(9,10,11), (10,11,12)],
    "ring":   [(13,14,15),(14,15,16)],
    "pinky":  [(17,18,19),(18,19,20)],
}

# add comment here
def calculate_angle(A, B, C):
    # Vectors from B to A and B to C
    V1 = (A.x - B.x, A.y - B.y)
    V2 = (C.x - B.x, C.y - B.y)

    # Dot product
    dot_product = (V1[0] * V2[0]) + (V1[1] * V2[1])

    # Magnitudes
    V1_magnitude = math.sqrt(V1[0]**2 + V1[1]**2)
    V2_magnitude = math.sqrt(V2[0]**2 + V2[1]**2)

    # Cosine rule
    angle_radians = math.acos(dot_product / (V1_magnitude * V2_magnitude))

    # Radians to degrees
    angle_final = math.degrees(angle_radians)
    
    return angle_final

# add comment here
def calibrate(cap, landmarker):
    
    # We'll store the final averaged angles here
    calibration_max = {}  # straight hand
    calibration_min = {}  # fist
    
    # We do this twice - once for max, once for min
    phases = [
        ("Straighten your hand fully!", calibration_max),
        ("Make a fist!", calibration_min),
    ]
    
    for message, calib_dict in phases:
        
        # These collect running sum and frame count per joint
        angle_sums = {}
        frame_count = 0
        
        # Countdown for 3 seconds
        start_time = time.time()
        
        while time.time() - start_time < 3:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Show instruction and countdown on screen
            elapsed = time.time() - start_time
            remaining = int(3 - elapsed) + 1
            cv2.putText(frame, message, (30, 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(frame, str(remaining), (30, 120), 
                       cv2.FONT_HERSHEY_SIMPLEX, 3, (0, 255, 255), 3)
            cv2.imshow("Calibration", frame)
            cv2.waitKey(1)
            
            # Send frame to MediaPipe
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            # landmarker.detect_async(mp_image, int((time.time() - start_time) * 1000))
            global timestamp
            timestamp += 1
            landmarker.detect_async(mp_image, timestamp)
            
            # If hand detected, calculate and accumulate angles
            if latest_landmarks:
                for hand in latest_landmarks:
                    for finger_name, joints in FINGER_JOINTS.items():
                        for (a, b, c) in joints:
                            angle = calculate_angle(hand[a], hand[b], hand[c])
                            key = f"{finger_name}_{b}"
                            
                            # Add to running sum
                            if key not in angle_sums:
                                angle_sums[key] = 0
                            angle_sums[key] += angle
                
                frame_count += 1
        
        # Average everything and store in the dict
        for key, total in angle_sums.items():
            calib_dict[key] = total / frame_count
        
        print(f"Calibration phase done: {message}")
        print(calib_dict)
    
    return calibration_max, calibration_min

# Mapping the angles for servo motors
def map_to_servo(angle, min_angle, max_angle):

    servo_angle = ((angle - min_angle) / (max_angle - min_angle)) * 180

    # max(0, min(180, servo_angle)) is clipping it so if it falls below 0, it remains 0; if above 180, remainds 180
    return max(0, min(180, servo_angle))

# Callback function - called by MediaPipe every time it detects a hand
# Stores landmarks globally so the main loop can access them
def print_result(result: HandLandmarkerResult, output_image: mp.Image, timestamp_ms: int):
    global latest_landmarks
    latest_landmarks = result.hand_landmarks

# Configure the hand landmarker
# LIVE_STREAM mode = processes frames in real time from camera
options = HandLandmarkerOptions(
    base_options=BaseOptions(model_asset_path='./models/hand_landmarker.task'),
    running_mode=VisionRunningMode.LIVE_STREAM,
    num_hands=1,                    # track one hand only
    result_callback=print_result    # call this function when hand is detected
)

# Open the default webcam (0 = first camera)
cap = cv2.VideoCapture(0)

# Timestamp counter - MediaPipe needs increasing timestamps for LIVE_STREAM mode
timestamp = 0

# calibration_max, calibration_min = calibrate(cap, landmarker)

# Create the landmarker and start the main loop
with HandLandmarker.create_from_options(options) as landmarker:

    calibration_max, calibration_min = calibrate(cap, landmarker)

    while True:
        # Read one frame from the camera
        ret, frame = cap.read()

        # If camera fails, exit the loop
        if not ret:
            break

        # Convert BGR (OpenCV format) to RGB (MediaPipe format)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Wrap frame in MediaPipe Image object
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        # Send frame to MediaPipe for async processing
        # Result comes back via print_result callback
        timestamp += 1
        landmarker.detect_async(mp_image, timestamp)

        # If landmarks are available, draw them on the frame
        if latest_landmarks:
            for hand in latest_landmarks:
                for lm in hand:
                    # Convert normalized coordinates (0-1) to pixel coordinates
                    h, w, _ = frame.shape
                    cx, cy = int(lm.x * w), int(lm.y * h)

                    # Draw a green circle at each landmark
                    cv2.circle(frame, (cx, cy), 5, (0, 255, 0), -1)

                # Angle calculation for fingers
                for finger_name, joints in FINGER_JOINTS.items():
                    for (a, b, c) in joints:
                        # angle = calculate_angle(hand[a], hand[b], hand[c])
                        # print(f"{finger_name} joint {b}: {angle:.1f}°")
                        angle = calculate_angle(hand[a], hand[b], hand[c])
                        key = f"{finger_name}_{b}"
                        servo = map_to_servo(angle, calibration_min[key], calibration_max[key])
                        print(f"{finger_name} joint {b}: {angle:.1f}° → servo: {servo:.1f}°")

        # Show the camera feed with landmarks drawn
        cv2.imshow(" Hand Tracking", frame)

        # Press Q to quit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

# Release camera and close all windows
cap.release()
cv2.destroyAllWindows()