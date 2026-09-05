These notes aren't 100% guarentted to be correct,  there might be values, info things which may not make sense; there is a good chance that you aren't hallucinating and the values I found are infact wrong. In that case please open a PR/ISSUE or email me via: shayan.mazahir@uwaterloo.ca.

In the end please remember that I am not directly in an ENG, CS, Pure MATH, or SCIENCE degree, everything I am doing is purely for fun, learning and me just being stubborn on making things work. 

# EMG Sensor Debug Log

**Hardware:** Gravity: Analog EMG Sensor by OYMotion (DFRobot SKU **SEN0240**)
**Goal:** Sensor isn't reading muscle signal. Isolate hardware vs. code/filtering.

---

## CRITICAL SPEC (took me a while to fight the issues which were in the end me just not reading stuff properly)

From the DFRobot wiki + datasheet:

- Output is analog, **0 ~ 3.0V**, with **1.5V as the REFERENCE (resting) voltage**
- Detection range: +/- 1.5mV, amplified 1000x
- Supply: 3.3 ~ 5.5V, **>= 20mA**, stabilized DC recommended (ripple/disturbance low)
- Effective spectrum: 20Hz ~ 500Hz; >8-bit ADC @ 1kHz recommended
- Electrode connector: **PJ-342** (3.5mm audio-style jack)

### Expected analogRead values on a 5V Arduino (10-bit ADC)

| Sensor output        | analogRead |
|----------------------|------------|
| 0V (bottom rail)     | 0          |
| **1.5V (AT REST)**   | **~307**   |
| 3.0V (top rail)      | ~614       |

On a 3.3V board instead: rest ~465, top rail ~930.

---

## Step 0 - Original symptom

Original sketch (EMGFilters, notch/bandpass, squaring, Threshold=0) printing
"Squared Data: ...". Two code issues flagged before hardware debug:

- `Threshold` left at `0` - never calibrated, so no noise floor cut.
- Loop timing: sampleRate implies 1000us budget, but sketch does a flat
  `delayMicroseconds(500)` regardless of how long read/filter/Serial.print took.
  Serial at 115200 can eat >500us alone, so actual sample rate is NOT locked to
  1000Hz like the filter assumes.

NOTE: `humFreq` was changed to `NOTCH_FREQ_60HZ`. This is CORRECT for North
America. The DFRobot sample ships with 50Hz. Keep 60Hz.

Set filtering aside to confirm the sensor produces real signal at all.

---

## Step 1 - Raw ADC test (no filtering)

Ran a bare `analogRead(A0)` loop, 50ms delay, arm at rest.

### Observed data pattern (repeating, highly regular):

    0,0,0,0 ... (long flat run at exactly 0)
    12, 8, 25, 34, 39, 52, 48, 58, 69, 75, 85, 94, 100   <- smooth ramp up
    303, 445, 608                                         <- fast jump
    608, 608, 608, 609, 608, 608 ... (long flat plateau)  <- pinned at top
    490, 219, 0                                           <- ramp back down
    0,0,0,0 ... (repeat)

Cycle repeats near-identically over and over.

### DIAGNOSIS

Signal is swinging **RAIL TO RAIL**: 0 (=0V) up to ~608 (=~3.0V, the top rail).

**It never rests at ~307**, which is where a relaxed muscle MUST sit given the
1.5V reference. The amplifier is **saturating / clipping**, not reporting muscle
activity.

Max of 608 (vs theoretical 614) also confirms this is a **5V board**.

This matches DFRobot's documented FAQ failure mode verbatim:
> "The sensor reading is abnormally large or unchanged."

DFRobot's official fix order:
1. Check whether the power supply of the sensor is stable
2. Check electrode patch direction is consistent with muscle direction, and the
   patch is tied to a large area of exposed skin
3. **Try pulling out the connector of the sensor electrode to see if the reading
   is normal**  <- decisive test

**Result:** Signal saturating rail-to-rail. Not muscle signal. Proceed to Step 2.

---

## Step 2 - Windowed min/max/avg test  (COMPLETE)

Board confirmed: **Arduino Mega** (5V, 10-bit ADC). So 307 / 614 targets are correct.

### Result: electrodes CONNECTED to board, pads floating in AIR (not on body)

    min  max  avg   %low  %high  %rail
    0    616  360   38    56     94      (steady, ~94-97% throughout)

avg settles ~337-364, in the neighbourhood of the 307 reference.
%rail pinned at **94-97%**.

### CORRECTION to Step 1 interpretation

Two errors in earlier reasoning, both now corrected:

1. **The Step 1 "ramp + plateau" pattern was an ALIASING ARTIFACT.**
   Step 1 sampled at delay(50) = ~20Hz. EMG spectrum is 20-500Hz and mains hum
   is 60Hz. Sampling 60Hz content at 20Hz produces a slow phantom wave that does
   not exist in the real signal. The tidy repeating ramps were undersampling,
   not a real periodic signal. Do NOT sample this sensor below ~1kHz.
   (DFRobot spec: >8-bit ADC @ 1kHz recommended.)

2. **"Unplugged should sit quietly at ~307" was WRONG.**
   A 1000x-gain differential bioamp with a floating input and 50cm of electrode
   wire attached acts as an ANTENNA. It picks up ambient 60Hz mains and
   saturates both rails. This is normal and universal to EMG front-ends.
   Floating-input saturation is EXPECTED, not a fault.

### What Step 2 actually establishes

- Board is alive, powered, and DC-biased correctly (avg near reference).
- Nothing yet about whether it can read muscle.
- The 94% rail figure with pads in air is **not diagnostic of a fault.**

### Why on-skin should differ

The sensor is a DIFFERENTIAL amp with a reference electrode. On skin, the body
becomes the reference, common-mode rejection engages, and the 60Hz currently
swamping the input gets subtracted out. Saturation should collapse. That is the
design intent, and it is the actual test.

---

## Step 3 - RESULTS (BREAKTHROUGH)

### Comparison table

| Condition                          | min   | avg   | %rail   |
|------------------------------------|-------|-------|---------|
| Jack OUT, laptop charging          | 0     | ~340  | 95-99%  |
| Jack OUT, laptop charging (rerun)  | 0     | ~283  | 93-100% |
| **Electrodes ON ARM, laptop UNPLUGGED** | **~115** | **~300** | **13-21%** |

### What this establishes

**The sensor works. It was never broken.**

Three simultaneous improvements on the on-arm + battery run:

1. **%rail collapsed 97% -> ~15%.** Amp came out of saturation.
2. **min lifted off 0 for the FIRST TIME in the whole session** (0 -> ~110-125).
   Bottom rail no longer touched at all. Every prior run had min pinned at 0.
3. **avg settled at 297-307** = the 1.5V reference, essentially exact. Signal now
   centered where the datasheet says it should be.

### Remaining issue: asymmetric clipping

The residual ~15% is now **entirely TOP-rail**. min never reaches 0 anymore, so
all rail hits are max pinning at exactly 614 (3.0V ceiling). Signal still
overshoots upward occasionally but no longer bottoms out.

Swing is asymmetric: ~190 counts below avg, ~314 counts above.

### CONFOUND - two variables changed at once

Electrodes were placed on body AND laptop was unplugged in the same step.
Contribution of each is currently unknown. Must isolate (see Test A below).


---

## Step 4 - RESULTS

### Test A - charger isolation: CONCLUSIVE

Sensor position unchanged on arm. Only variable = laptop charger.

| Condition (sensor unmoved) | %rail   |
|----------------------------|---------|
| Laptop on BATTERY          | 13-21%  |
| Laptop PLUGGED IN          | 94-98%  |

**The laptop charger is the dominant noise source.** Confound from Step 3 is now
resolved: placement helped, but the charger is what drives saturation.

**Mechanism:** most laptop chargers are 2-prong switch-mode supplies with no
earth ground. Chassis floats at ~half mains voltage via internal Y-capacitors,
coupling directly into the body and into a 1000x-gain bioamp. Classic biosignal
problem, well documented.

### Test B - muscle response: INVALID RUN

Test B was executed with the charger STILL PLUGGED IN (%rail column shows 91-98%,
matching the plugged state, not the 15% battery state).

Result: MAD sat flat at ~290-303 regardless of activity. No clench response.

**Why MAD showed nothing - MAD was PEGGED AT ITS CEILING:**

With avg ~300 and signal slamming 0 <-> 614:
  |0 - 300|   = 300
  |614 - 300| = 314
Mean absolute deviation of a perfect rail-to-rail square wave centred at 307 is
**~307**. Measured value was 298 = ~97% of theoretical maximum.

MAD cannot rise further, so muscle activity cannot move it. Analogous to
measuring shout volume on a meter that is already redlined.

**Test B must be re-run on battery.** The measurement is meaningless under
saturation. But for some absurd reason nothing seems to be working now, all I'm getting is like 4000000+ values.

---

## Step 5 - Test B RETRY (on battery)

Same sketch, no code changes. Procedure:

1. **Unplug laptop charger from wall.** VERIFY %rail drops to ~15% BEFORE
   collecting any clench data. If it does not drop, stop and re-diagnose.
2. Sensor on **forearm flexor** - underside of forearm, ~1/3 down from elbow,
   strapped firm, pads pointing wrist-to-elbow.
3. Sequence: 10s relaxed (note MAD) -> clench hard 3s (note MAD) -> relax.
   Repeat 2x.

- %rail on battery (gate check): __________
- MAD at rest:   __________
- MAD on clench: __________

With %rail at ~15% instead of 96%, MAD has headroom to actually respond.

---

## Longer-term: living with the charger problem

The build cannot depend on "laptop unplugged" forever. Options, roughly in order
of effort:

1. **Run laptop on battery during capture** - works now, zero cost, but limits
   session length.
2. **Power the Mega from a USB power bank** instead of laptop USB - decouples the
   Arduino rail from mains entirely.
3. **USB isolator** (e.g. ADuM3160-based) between laptop and Arduino - proper fix,
   ~$20-40, standard practice for biosignal work.
4. **Grounded (3-prong) laptop supply** - if one exists for the machine, removes
   the floating-chassis coupling.
5. **Physical distance** from mains wiring, power strips, monitors, and other SMPS
   devices during capture.


---

## Step 6 - Once muscle response confirmed

Return to the original EMGFilters sketch and run DFRobot's calibration:
1. `Threshold = 0`, upload
2. Relax arm, record MAX printed value while relaxed
3. If that max >1000, fine-tune electrode position first
4. Set `Threshold` = recorded max, re-upload
5. Serial Plotter: relaxed = flat line at 0 (occasional peaks normal),
   fist clench = obvious waveform

Also apply the loop timing fix:

    timeStamp = micros() - timeStamp;
    int remaining = timeBudget - timeStamp;
    if (remaining > 0) delayMicroseconds(remaining);

Keep `humFreq = NOTCH_FREQ_60HZ` (North America).
Recalibrate every session - EMG differs by position and by day.

---

## Step 6 - Cross-validation: TWO SENSORS, TWO MACHINES

### Setup varied
- **Sensor A:** DFRobot SEN0240 (OYMotion) - the original unit, using OYMotion's
  supplied code
- **Sensor B:** a second EMG sensor, same dry-electrode style, **different
  manufacturer**
- **Machine 1:** laptop (2-prong SMPS charger, floating chassis)
- **Machine 2:** desktop (3-prong, earthed chassis, USB from motherboard ports)

### Result
**Same failure mode across all combinations.** Signal saturates; no distinguishable
muscle response.

### What this ELIMINATES

This is the strongest single result in the log. Two independent sensors from two
different companies, on two computers with fundamentally different grounding
topologies, all failing identically rules out:

- [x] Defective sensor unit (two units, two manufacturers)
- [x] Manufacturer-specific design flaw
- [x] Board-specific fault
- [x] Machine-specific fault
- [x] Laptop's floating 2-prong supply as the SOLE cause (desktop is earthed and
      still fails)
- [x] Code / library / sketch (already ruled out at Step 1 with bare analogRead)
- [x] Wiring (already ruled out - baseline sits at correct reference)

### What REMAINS as possible cause

1. **Ambient electromagnetic environment** - the room itself. Mains wiring in
   walls, other appliances, monitors, power strips. Earthing the chassis (desktop)
   removed one coupling path but not ambient pickup.
2. **Dry-electrode contact technique** - the pads are simply not achieving low
   enough skin impedance, and/or not holding it. Consistent with the observed
   drift from 15% -> 67% over ~20 min with nothing moved.
3. **Something in the measurement approach** not yet identified.

### Caveat on the desktop run
Desktop test was conducted using an on-screen keyboard (no physical keyboard
available), which limited how carefully data could be collected and pasted.
Desktop numbers were not captured in detail - only the qualitative "same issue."
Worth re-running properly if a keyboard becomes available.

### Note
The two-sensor result should be included in any request for outside help. It
pre-empts the most common first suggestion ("try a different sensor") and saves a
round trip.

---

## Current status: FREE OPTIONS EXHAUSTED

Everything achievable without new hardware has been tried:

- [x] Electrode placement: forearm flexors, bicep, hand
- [x] Fibre alignment (wrist-to-elbow / shoulder-to-elbow)
- [x] Contact pressure, including pressing pads by hand
- [x] Skin prep: clean, alcohol, damp
- [x] Re-seating the PJ-342 3.5mm jack
- [x] Laptop on battery vs mains
- [x] Desktop (earthed) vs laptop (floating)
- [x] Two different sensors, two manufacturers
- [x] Sampling rate corrected 20Hz -> 1kHz
- [x] Bare analogRead with all filtering removed

Remaining paths all require either hardware or outside expertise:
- USB isolator (ADuM3160-based), ~$20-40, needs ordering
- Wet/gel electrodes instead of dry
- Expert diagnosis (2 threads currently out - see below)

### Outstanding help requests
1. **Prof. Jack Callaghan** (UW Kinesiology) - emailed. Teaches KIN 612
   "Instrumentation and Signal Processing in Biophysical Research", cross-appointed
   to Mechanical & Mechatronics Engineering. Strongest topical match on campus.
   https://uwaterloo.ca/kinesiology-health-sciences/people-profiles/jack-callaghan


---

## Step 7 - Literature check: how research labs actually acquire sEMG

Source: Kumar, Arjunan & Singh (2013), "Towards identification of finger flexions
using single channel surface electromyography - able bodied and amputee subjects",
*J NeuroEng Rehabil* 10:50. Bio-signals Lab, RMIT University.
Open access: https://pmc.ncbi.nlm.nih.gov/articles/PMC3680228/

Note: this paper is about CLASSIFICATION (decoding which finger moved) - i.e. the
step AFTER the one we are stuck on. It assumes acquisition already works. Its
value here is the Methods section, which documents what a funded lab uses.

### Rig comparison

| Parameter    | Kumar et al. 2013                                   | This project              |
|--------------|-----------------------------------------------------|---------------------------|
| Electrodes   | DELSYS bipolar, **electrolyte gel applied**          | Dry pads, no gel          |
| Type         | **ACTIVE** - preamp built into electrode unit        | Passive pads, 50cm cable  |
| Geometry     | 2 silver bars, 1mm thick, 10mm long, 10mm spacing    | 3 pads on small board     |
| CMRR         | **92 dB**                                            | Unspecified               |
| Bandwidth    | 20-450 Hz hardware, 12 dB/octave rolloff             | Software filtering only   |
| Resolution   | 16 bits/sample                                       | 10 bits (Arduino ADC)     |
| Sampling     | 1024 Hz                                              | 1000 Hz  [MATCH]          |
| Gain         | 1000                                                 | 1000  [MATCH]             |
| Skin prep    | **Shaved if needed, exfoliated, then 70% alcohol**   | Wiped, sometimes damp     |
| Ground elec. | Volar aspect of the wrist                            | On-board third pad        |
| Muscle       | Flexor digitorum superficialis (FDS), forearm        | Forearm flexors, bicep    |

### The two differences that matter most

**1. ACTIVE vs PASSIVE electrodes.** Their preamplifier sits at the skin, so the
cable carries an already-amplified, low-impedance signal. Ours carries raw
microvolts across 50cm of wire before any amplification - and that cable was
identified at Step 2 as behaving like an antenna. This is an ARCHITECTURAL
difference, not something tunable by placement or pressure.

**2. Gel + aggressive skin prep.** They shaved, exfoliated dead skin, cleaned with
70% alcohol, THEN applied electrolyte gel. Contact impedance is not comparable to
wiping and dampening dry pads.

### Reality check

The paper notes that at low contraction levels the noise magnitude becomes
comparable to the signal itself, and that background spectra varied enough between
sessions that stationary filtering was unsuitable - they needed adaptive spectral
subtraction. This is a funded bio-signals lab with active gel electrodes and 92 dB
CMRR, and they still had to fight background noise.

**Conclusion: the difficulty encountered in this project is expected given the
hardware, not a result of poor method.** The gap is instrumentation.

### Two references worth chasing (from this paper's bibliography)

- **[29] Hermens, Freriks, Disselhorst-Klug & Rau (2000)**, "Development of
  recommendations for SEMG sensors and sensor placement procedures",
  *J Electromyogr Kinesiol* 10:361-374. This is the **SENIAM standard** - the
  actual reference for electrode placement.
- **[28] Merletti, Botter, Troiano, Merlo & Minetto (2009)**, "Technology and
  instrumentation for detection and conditioning of the surface electromyographic
  signal: state of the art", *Clin Biomech* 24:122-134. A review of exactly this
  problem domain - the closest thing in the literature to a direct answer.

### Other papers collected (classification-stage, for later)

- Tenore et al. (2009), "Decoding of individuated finger movements using surface
  electromyography", IEEE TBME 56(5) - https://pubmed.ncbi.nlm.nih.gov/19473933/
- Englehart & Hudgins (2003), "A robust real-time control scheme for multifunction
  myoelectric control", IEEE TBME 50:848
- Mallat & Zhong (1992), "Characterization of signals from multiscale edges"

### Result headline (for later writeup)
Kumar et al. achieved 93.4% accuracy identifying four individual finger flexions
from a SINGLE sEMG channel - relevant because it shows one channel is sufficient
in principle, if the signal is clean.


---

---

# 4 September - Day 2

Everything above this line is from the first session. This section is a separate
day. Read the two together: several Step 1-7 conclusions get overturned here, and
one Day 1 result becomes an unexplained contradiction rather than a settled fact.

---

## Step 8 - Two real defects in DFRobot's own example code

### Defect 1: `sq()` overflows 16-bit `int` on AVR

The older single-channel example does:

    int DataAfterFilter = myFilter.update(Value);
    int envlope = sq(DataAfterFilter);

On the Mega, `int` is 16-bit (max 32767). Any filtered value above ~181 overflows
and wraps negative, printing as `4294936729`, `4294951145` and similar. That
explains the "4000000+ values" noted at the end of Step 4 - it was never a sensor
fault, it was integer overflow in the vendor sketch.

Fix:

    long DataAfterFilter = myFilter.update(Value);
    long envlope = DataAfterFilter * DataAfterFilter;

**Consequence:** every large reading from the stock sketch was garbage, including
the "~25000 at rest" figure that DFRobot's calibration procedure (Step 6) tells
you to use as your threshold. That calibration cannot be performed correctly on an
AVR board with the shipped code.

### Defect 2: `CYCLE_BUF_MEAN` truncates the entire signal

The 2019 two-channel example computes its envelope as:

    uint16_t envelope = CYCLE_BUF_MEAN(cb) * 2;    // (rectSum / 64) * 2

Integer division by 64. Once mains coupling is removed (see Step 9) the noise
floor is low enough that **the whole signal is smaller than the divisor** and gets
truncated away. Real dumps read literally:

    8 8 8 8 6 6 6 6 4 4 4 4 2 2 2 2 4 4 4 4 ...

Fix - store the running sum, keep 64x the resolution:

    uint16_t envelope = (rectSum > 65535) ? 65535 : (uint16_t)rectSum;

Same data, same filter. Flat "2 to 8" became traces spanning 2300-9300 with
visible structure.

Both defects are worth reporting upstream.

---

## Step 9 - The laptop USB rail (overturns part of Step 4)

Step 4 concluded the laptop *charger* was the dominant noise source. That was
correct but incomplete.

Another builder posted side-by-side FFTs of the same rig powered two ways. Their
"not touching the chassis" plot is a solid filled 0-3V block - **identical to the
saturation in Step 1** - with a 50Hz spike and harmonics at 100/150/200/250/300/
350/400 Hz. Their battery-powered plot is a flat baseline with clean contraction
bursts and no mains spikes at all. Critically, they noted this held *even with the
laptop running on battery*.

**Laptop-on-battery is NOT the same as board-on-battery.** The Arduino was still
being fed through the laptop's USB rail and referenced to a floating laptop.

DFRobot's own 2019 example states this outright, and it was missed on Day 1:

> "Please unplug any power adapters when using sEMG sensors. Only battery powered
> systems can be connected directly/indirectly to sEMG sensors."

**Result:** Arduino run from a USB power bank with the laptop fully disconnected
gave the first unsaturated trace of the project - **293 to 338, centred ~312**,
never touching either rail. Compare every prior run pinned at 0 and 614.

### The tradeoff this creates
No USB means no serial. Workarounds used:
- **EEPROM buffering** - record on battery, dump over serial afterwards. The Mega
  has 4KB, enough for 500 samples at 2 bytes.
- **LED on pin 13 as a live saturation indicator** - solid = under 20% railed,
  off = saturated. Readable across the room with no data connection.

Proper fixes, not yet acquired: a USB isolator (ADuM3160-based, ~$20-40) gives
live serial *and* isolation simultaneously; an HC-05/HC-06 Bluetooth module gives
wireless serial and is the simpler swap since existing sketches work unchanged.

---

## Step 10 - Overturns Step 7's hardware-tier conclusion

Step 7 concluded the gap was instrumentation - that dry passive electrodes at this
tier could not resolve EMG.

**That was overstated.** The SEN0240 ships with dry electrodes, DFRobot documents
it working with them, and other builders get it working. The blockers were the two
code defects in Step 8 and the power path in Step 9 - not electrode tier.

Kumar et al. remains a useful reference for what a funded lab uses, but it was
used here to justify near-abandonment of a solvable problem. Worth remembering as
a reasoning failure, not just a hardware note.

---

## Step 11 - Component isolation (all clean)

Run after Day 2 opened with the signal fully saturated again (96-100% railed).

| Component | Test | Result |
|---|---|---|
| Arduino A4 / ADC | jumper to GND, then to 5V | 0 and 1023, steady. **Good.** |
| Sensor board | read with electrode jack REMOVED | oscillates ~205-393, **centred ~300**, not saturated. **Good.** |
| A4 floating | nothing connected | ~284-297. Expected ambient. |

**Key comparison:**
- Electrodes connected, pads in AIR -> rails 0 <-> 614
- Electrodes connected, pads ON SKIN -> rails 0 <-> 614, **identical**

On proper skin contact the differential amp should come out of saturation via
common-mode rejection. It did not change at all between air and skin.

### Variables eliminated on Day 2
Marked placement reproduced exactly; hard contact pressure; skin wetted to visibly
damp; laptop unplugged; moved to a different room; 8-hour cold start; **a second
independent electrode set**; jack re-seated repeatedly. None changed anything.

---

## Step 12 - The reference electrode lead, and why it is NOT closed

Observed on laptop USB power:
- Touching the laptop chassis dropped the reading from ~60 to 5-8
- Touching the **reference** pad dropped it
- Touching the **signal** pads did nothing

That pointed cleanly at the reference electrode not making skin contact - the body
floating with no reference, and a fingertip (lower impedance than forearm skin)
substituting for it.

**Then it reversed.** On battery power, holding the reference pad caused **full
saturation, 0 <-> 627 hard clipping** - dramatically worse.

Plausible reading: on USB the body was already coupled to the laptop, so touching
the pad tied the sensor reference to that same potential. On battery the system is
floating and isolated, so a finger injects ambient hum instead of providing a
reference.

**This is an open lead, not a closed one.** The reversal was never explained. Do
not treat the reference/ground question as ruled out.

---

## Step 13 - Community input, and one suggestion that should NOT be followed

Two suggestions received:

**"Add a voltage divider before the ADC to stop the clipping."**
**Do not do this.** The clipping happens *inside the sensor's amplifier*, before
its output. The SEN0240 outputs 0-3V into a 0-5V ADC and physically cannot
over-range it. A divider would scale down an already-clipped square wave and
recover nothing.

**"Ground the circuit to mains earth (PE) to stop it floating."**
**Do not do this either.** Biosignal equipment is deliberately *isolated* from
mains earth - that is why USB isolators and battery power are the standard
recommendations. With electrodes on the body, bonding the circuit to earth creates
a fault path through the user. Isolation is the correct direction, not earthing.

The genuinely useful community input was the USB-rail diagnosis in Step 9 and the
signal-reference observation in Step 12.

---

## Step 14 - A retracted result (and why the control mattered)

Three recordings, battery power, 60Hz notch, storing `rectSum`:

| Condition | peak | trough | shape |
|---|---|---|---|
| Repeated fast open/close | 8123 | 2738 | repeating peaks |
| Single sustained fist | 9265 | 2581 | ramp, plateau, decay |
| **REST - no motion** | **8109** | **~2300** | **ramp, peak, decay** |

The first two were initially read as real muscle activity - different shapes,
each apparently matching the motion performed.

**The rest control produces the same shape and nearly the same peak.** Both peak
around sample 55. 9265 vs 8109 is not a meaningful separation. The
ramp-plateau-decay shape is a settling transient present on every run regardless
of what the arm does.

### How that error happened
No control was run before the claim was made; the interpretation was not blind
(the motion was known in advance); two runs, no replication. Day 1's result was
explicitly protected against exactly this with a null control. That safeguard was
skipped here and the claim did not survive first contact with one.

### Follow-up: the transient is not filter settling
Warm-up extended 500 -> 5000 samples (5 seconds). **The transient survives.** Five
seconds is far more than an IIR chain and a 64-entry ring buffer need, so the
filter is not the cause. Remaining candidates, unconfirmed: the sensor's own
analog front end settling after power-up, or the electrode-skin interface
stabilising.

Useful by-product: after ~sample 100 the resting trace holds a **stable 3300-3700**
for the rest of the window. First stable resting reference obtained.

### Rest vs clench on the steady-state region only

| Condition | steady-state (samples 100+) |
|---|---|
| Rest | ~3300 - 3700 |
| Clench | ~2600 - 4500, wandering |

**Negative.** Clench does not settle higher, and spends much of the later
recording *below* the resting range. Between-run baseline drift exceeds the effect
being looked for, so comparing two separate recordings cannot resolve this.

**Better design, not yet run:** rest and clench *within a single recording* -
still for the first half, hard clench for the second, compare halves of the same
trace. Same session, same drift, same electrode state.

---

## Status as of 4 September

### Established, well evidenced
1. **Laptop USB power saturates the input; battery power removes it.** Confirmed
   directly, independently by another builder's FFTs, and stated in DFRobot's own
   example comment.
2. **`CYCLE_BUF_MEAN` integer division destroys the signal** on a low-noise input.
3. **`sq()` overflows 16-bit `int` on AVR** in the older example.

(2) and (3) are genuine defects in published vendor example code.

### NOT established - open contradictions

**A. The reference/ground question is open.** Touching the reference helped on USB
and hurt on battery. Never explained. See Step 12.

**B. Day 1's result contradicts the Day 2 explanation.** Day 1 produced a 7/8
rest-vs-clench result **on laptop USB power**, with a matched null control (4/8), a
cross-placement replication, and a physical-disconnection control (4/8, 4/8, 5/8).
If USB power makes measurement impossible, that should not have been achievable.

Either the Day 1 result was spurious despite its controls, or the USB-power
explanation is incomplete. **This contradiction is unresolved and is the most
likely location of the real answer.** It is the thing to lead with when asking for
help.

**C. No muscle signal has been demonstrated on Day 2.** Every attempt to show a
rest/clench difference has failed or been retracted.

### Working configuration so far
- Arduino Mega, sensor on **A4**
- **USB power bank, laptop disconnected entirely**
- OYMotion EMGFilters, `SAMPLE_FREQ_1000HZ`, **`NOTCH_FREQ_60HZ`**
- 64-sample rectified ring buffer, **store `rectSum`, never `rectSum / 64`**
- EEPROM capture during battery operation, serial dump afterwards
- LED on pin 13 as a live saturation indicator
- Warm-up is currently insufficient - a settling transient dominates the window

### Next steps
- Within-recording rest/clench comparison (halves of one trace)
- USB isolator or HC-05 Bluetooth for live data without the EEPROM round-trip
- Report both vendor defects upstream
- Second channel for flexor/extensor discrimination
- Post this log, leading with contradiction **B**

### A note on method
On Day 2 hypotheses were generated faster than they were tested, and several were
wrong: the warm-up theory, the reference-electrode conclusion, Step 7's
hardware-tier argument, and a "working" claim that a rest control demolished
immediately. Every one of those was caught by running a control rather than by
reasoning harder. Treat any untested hypothesis in this log with suspicion.

---

## Interpreting %rail

| %rail   | Meaning                                                          |
|---------|------------------------------------------------------------------|
| < 2%    | Healthy. Occasional peaks are normal per DFRobot docs.           |
| 2-10%   | Usable, minor pickup.                                             |
| 10-40%  | Significant hum pickup. Fixable via grounding/placement/power.    |
| > 50%   | Amp clipping more than measuring. Nothing downstream will work.   |
| > 90%   | Fully saturated. Expected ONLY for floating/unattached input.     |

---

## Reference links

- Wiki (main): https://wiki.dfrobot.com/sen0240
- Calibration + waveform example: https://wiki.dfrobot.com/sen0240/docs/20737
- Fist count example: https://wiki.dfrobot.com/sen0240/docs/20736
- Electrode placement reference: https://wiki.dfrobot.com/sen0240/docs/20735
- EMGFilters library (GitHub): https://github.com/oymotion/EMGFilters
- DFRobot troubleshooting video:
  https://drive.google.com/file/d/1ANKqwHs0pEY-TzOjP-e0kYbKdSF-vMTM/view

---

## Findings Log

- **Step 1:** Signal railing 0 <-> 608, never resting at expected ~307 midpoint.
  Confirmed 5V board. Amplifier saturating - this is a contact/power issue, not a
  code or filter issue. All DSP debugging deferred until raw signal is sane.
- **Step 2:** Pads floating in air -> 94-97% railed, avg near reference. This is
  EXPECTED antenna pickup for a floating 1000x bioamp input, NOT a fault. Board
  confirmed alive and correctly biased. Also retroactively identified Step 1's
  "periodic ramp" pattern as an aliasing artifact from 20Hz undersampling.
  Real diagnostic test (electrodes on skin) still pending.
- **Step 3:** ON-ARM + BATTERY -> %rail 97% to ~15%, min lifted off 0 for first
  time (~115), avg locked at ~300 = the 1.5V reference. **Sensor confirmed
  functional.** Root cause was floating/poor electrode contact plus mains noise,
  never a broken sensor or a code bug. Residual ~15% is top-rail only.
  Confound: two variables changed at once (placement + charger) - needs isolating.
- **Step 4:** Charger isolation CONCLUSIVE - battery 15% vs plugged 96% rail, same
  placement. Laptop charger is the dominant noise source (floating 2-prong SMPS
  chassis coupling via Y-caps). Test B invalid: run while still plugged in, so MAD
  was pegged at its ~307 ceiling and could not respond to muscle activity. Retry
  Test B on battery, gating on %rail ~15% before collecting clench data.
- **Step 6:** TWO sensors (different manufacturers) x TWO machines (floating laptop,
  earthed desktop) = identical failure. Eliminates defective unit, manufacturer
  flaw, and machine-specific cause. Remaining suspects: ambient EM environment and
  dry-electrode contact impedance. Free options now exhausted; remaining paths need
  hardware (isolator, gel electrodes) or outside expertise.
- **Step 7:** Literature comparison (Kumar et al. 2013, RMIT Bio-signals Lab).
  Research-grade acquisition uses ACTIVE gel electrodes with the preamp at the
  skin, 92 dB CMRR, 16-bit, hardware bandpass, and shaved/exfoliated skin prep.
  Sampling rate and gain match ours; everything else is a tier up. Confirms the
  remaining gap is INSTRUMENTATION, not technique. Key follow-up refs: Hermens
  et al. 2000 (SENIAM placement standard) and Merletti et al. 2009 (sEMG
  instrumentation state of the art).

- **[4 Sep] Step 8:** TWO defects found in DFRobot's own example code. `sq()`
  overflows 16-bit `int` on AVR (explains the "4000000+ values" at Step 4, and
  means the Step 6 calibration cannot be done correctly with the shipped sketch).
  `CYCLE_BUF_MEAN` integer-divides by 64 and truncates the entire signal once mains
  coupling is gone - dumps literally read "8 8 6 6 4 4 2 2". Store `rectSum`
  instead.
- **[4 Sep] Step 9:** Overturns part of Step 4. Not just the charger - the laptop
  USB RAIL itself. Laptop-on-battery is not board-on-battery. Arduino on a USB
  power bank with the laptop fully disconnected gave the first unsaturated trace of
  the project: 293-338, centred ~312, never railing. DFRobot's 2019 example states
  this requirement outright.
- **[4 Sep] Step 10:** Overturns Step 7. The hardware-tier conclusion was
  overstated - the SEN0240 ships with dry electrodes and is documented working with
  them. The blockers were code defects and the power path, not electrode tier.
- **[4 Sep] Step 11:** Component isolation all clean. A4 verified (GND->0, 5V->1023);
  sensor board verified with jack out (~300 centred, unsaturated). Pads in air vs
  on skin rail IDENTICALLY, so contact is not being made. Eliminated: marked
  placement, hard pressure, damp skin, different room, cold start, and a second
  independent electrode set.
- **[4 Sep] Step 12:** Reference-electrode lead is OPEN, not closed. Touching it
  helped on USB power (60 -> 5-8) but caused full 0<->627 saturation on battery.
  Reversal never explained.
- **[4 Sep] Step 13:** Two community suggestions rejected with reasons - a voltage
  divider (clipping is inside the amp, before its output) and earth-grounding the
  circuit (biosignal gear is deliberately isolated; bonding to earth with
  electrodes on the body creates a fault path through the user).
- **[4 Sep] Step 14:** A "working signal" claim was made and RETRACTED. A rest
  control produced the same ramp-peak-decay shape and nearly the same peak (8109)
  as a sustained fist (9265). The shape is a settling transient, and it survives a
  5-second warm-up so it is not the filter. Rest/clench compared on steady state:
  negative, clench often sits below rest. Between-run drift exceeds the effect;
  needs a within-recording design.
- **[4 Sep] STATUS:** Established - USB-rail saturation, and both vendor code
  defects. NOT established - the reference/ground question, and the central
  contradiction that Day 1's controlled 7/8 result was obtained ON laptop USB,
  which the Day 2 explanation says should have been impossible. That contradiction
  is the thing to lead with when asking for help.
