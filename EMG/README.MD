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