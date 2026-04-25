1. ## Known Issue - Angle Calculation Edge Case

**Status:** Unconfirmed - cannot be tested until hand is printed

**Issue:**
When the hand is in a "duck face" position (fingers partially curled in a specific way), 
the calculated angle may read the same as a fully closed fist (~ 0°).

**Potential Impact:**
- Servo jitter from ambiguous angle readings
- Motor confusion from identical values for two different positions
- Possible rapid back-and-forth servo movement ("hunting")

**Possible Fix: (theoretical)**
- Add deadband filtering - ignore changes smaller than a threshold (e.g. +-5°)
- Smooth angles over multiple frames before sending to servo
- Investigate if the issue is in angle calculation or servo mapping

**Priority:** Medium - test when hand is printed

------------------------------------------------------------------------------------------------------------------------------

## Known Issue — Servo Jitter & Smoothing

**Status:** Mostly resolved in software — final tuning needs hardware

**Issue:**
Raw angle values sent to servo every frame caused jitter and erratic movement.
Even small natural hand movements created rapid value changes the servo tried to follow.

**What was fixed:**
- Rolling average buffer implemented (deque, configurable via protocol.json)
- Send rate limited to 50ms intervals (20Hz) via SEND_INTERVAL in protocol.json
- Pre-filled buffer with neutral value (90°) to prevent cold start jumping
- Reduced to single joint calculation in main loop for performance

**What still needs hardware tuning:**
- Buffer size (currently 3 in protocol.json) — increase if jittery, decrease if laggy
- Deadband — ignore changes smaller than X degrees to prevent hunting
- Send rate — may need further adjustment based on servo response time

**Expected behavior after tuning:**
- Smooth servo movement following intentional finger movement
- Ignores tiny natural hand tremors
- No noticeable lag between finger and servo response

**Priority:** Low until hand is printed - test when hand is printed