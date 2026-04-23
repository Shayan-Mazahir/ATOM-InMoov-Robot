## Known Issue - Angle Calculation Edge Case

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