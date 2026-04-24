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

2. ## Known Issue - Servo Jitter & Smoothing

**Status:** Partially implemented - needs tuning with actual hardware

**Issue:**
Raw angle values sent to servo every frame cause jitter and erratic movement.
Even small natural hand movements create rapid value changes the servo tries to follow.

**Current State:**
Rolling average buffer implemented (deque maxlen=5) but buffer size not tuned.

**What needs tuning when hand is printed:**
- Buffer size (currently 5) - increase if jittery, decrease if too laggy
- Send rate - currently sending every frame, may need rate limiting
- Deadband - ignore changes smaller than X degrees to prevent hunting

**Expected behavior after tuning:**
- Smooth servo movement that follows intentional finger movement
- Ignores tiny natural hand tremors
- No noticeable lag between finger movement and servo response

**Priority:** High - test immediately when hand is printed