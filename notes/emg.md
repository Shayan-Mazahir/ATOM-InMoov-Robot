# EMG for ATOM - the physics and the logic, explained plainly

## Part 1 - What is EMG actually measuring, physically

### The source: motor units

A muscle is built from thousands of individual fibers, bundled into groups
called **motor units**. Each motor unit is wired to exactly one motor
neuron coming from your spinal cord. When your brain decides to contract a
muscle, it does not send a smooth dial-turn. It sends discrete electrical
pulses down these neurons. Each pulse arriving at a fiber causes a brief
voltage flip across the fiber's membrane (ions moving in and out), lasting
about a millisecond, and that voltage flip is the physical event that makes
the fiber contract. This single event is called a **motor unit action
potential**, MUAP for short.

Your brain controls how hard you contract two ways:

- **Recruitment** - activating more motor units. Light effort = few units
  firing. A hard clench = many more recruited.
- **Rate coding** - firing each active unit faster.

Both of these directly increase the amount of electrical activity happening
in the muscle. That is the entire physical reason EMG amplitude tracks
effort - there is no separate "strength sensor," the electricity itself
scales with force.

### Why a sensor on your skin can pick this up

A single MUAP is a tiny voltage, microvolts, generated deep inside the
muscle. It does not stay contained there - it spreads outward through
surrounding tissue (muscle, fat, skin) like a ripple through water, a
phenomenon called **volume conduction**. By the time that ripple reaches the
skin surface it is faint and smeared out, but it is still there, and an
electrode sitting on the skin can measure it as a tiny changing voltage.

This is why electrode placement matters so much. You want the electrode as
close as possible to where the strongest ripples originate (the muscle
belly, not the tendon), and aligned along the muscle fiber direction so you
catch the wave traveling along the fiber rather than several fibers'
opposing ripples cancelling each other sideways.

### Why the raw signal looks like noisy static, not a clean wave

You never see one MUAP in isolation. During even a mild contraction, dozens
to hundreds of motor units fire independently and their ripples overlap and
interfere on your electrode, like a crowd clapping instead of one person.
What you record is the sum of all of it, and summed independent events look
statistically like noise even though every part of it is a real
physiological signal. This is also why amplitude still tracks effort even
though it looks random: more motor units firing simultaneously and faster
means bigger overlapping ripples, i.e. higher average amplitude, even though
no single event got "louder."

### Why the signal is contaminated with things that are not muscle at all

Three things ride along with the real signal, each for a physical reason,
and none of them ever happened inside your muscle:

- **Motion artifact.** If the electrode shifts against your skin even
  slightly, that mechanical movement itself generates a spurious voltage at
  the contact point. Shows up as slow, large drift. This is the same
  problem a smartwatch has with heart rate readings during a workout, the
  sensor jostling against your wrist creates fake signal that has nothing
  to do with your actual heartbeat.
- **Mains hum, 50 Hz (60 Hz in North America).** Every AC-powered device and
  wire near you radiates a faint electric field at the frequency your wall
  power alternates at. Your arm is a crude antenna for it. This is the exact
  same buzz you hear if you plug a cheap guitar into an amp near a bad
  power supply, or the hum on a laptop mic recording near a charger.
- **Baseline drift.** The DC voltage at the electrode-skin contact wanders as
  your skin sweats or contact pressure shifts, because a dry electrode holds
  contact by pressure rather than conductive gel, so it is more sensitive to
  this than a sticky-pad electrode would be.

Removing these three is not optional polish. Skip it, and the model is not
classifying gestures - it is classifying how sweaty you are or whether your
laptop charger is plugged in nearby.

**Checkpoint 1.** In your own words: why does clenching harder produce a
bigger EMG signal, physically? What is actually changing at the muscle-fiber
level - and separately, why does the raw signal still look messy rather than
tracking that increase as a clean smooth line?

<details>
<summary>Answer, check after you've tried</summary>

Clenching harder recruits more motor units and makes each active one fire
faster, so more electrical events (MUAPs) are happening per second. The
electrode measures the sum of many independent, overlapping ripples, and
summed independent events look statistically noisy even as their combined
average energy rises, so amplitude trends upward with effort, but the raw
trace itself never becomes a clean line, because the underlying events are
still individually random in timing.
</details>

---

## Part 2 - The pipeline, top to bottom

```
forearm muscle
   |  MUAPs, volume-conducted to the skin, microvolts
dry electrode + ESP32 ADC
   |  digitized, streamed as integers over serial
EMGStream                    (stream.py)
   |  normalised, filtered, cut into overlapping windows
EMGFilterChain                (filter_chain.py, biquad.py)
   |  drift / hum / high-frequency noise removed
features.extract              (features.py)
   |  one window -> 16 numbers per channel
LDAClassifier                 (classifier.py)
   |  16 numbers -> gesture label + confidence
GestureSmoother                (smoother.py)
   |  20 raw decisions/sec -> one stable held gesture
AmplitudeTracker               (amplitude.py)
   |  how hard you're clenching, 0 to 1
HandDriver                     (driver.py)
   |  gesture + effort -> servo angles -> serial out
ESP32 -> servos
```

Every stage below is one box in that diagram, explained physically or
mathematically, then tied to its file.

---

## Part 3 - Filtering: removing what is not signal

Think of this the way you'd think about an audio equalizer, because that's
exactly what it is. A highpass filter is a bass cut, a lowpass filter is a
treble cut, a notch filter removes one specific pitch and leaves everything
else untouched, like a guitarist's noise gate cutting out a specific
feedback whine without muting the rest of the sound.

- **Highpass at 20 Hz** (`config.py:HIGHPASS_HZ`) removes anything that
  changes slower than 20 times a second - which is exactly the baseline
  drift and motion artifact described above, since those are slow by
  nature. Same idea as a podcast mic's "low cut" setting that removes the
  low rumble of wind or handling noise while leaving your voice intact.
- **Notch at 50 Hz** (`config.py:NOTCH_HZ`) is a scalpel cut that removes
  one specific frequency and leaves everything else alone. Same tool audio
  software uses to remove a single annoying hum tone from a recording
  without muffling the rest of the audio.
- **Lowpass at 450 Hz** (`config.py:LOWPASS_HZ`) discards anything faster
  than real muscle signal can physically be, the same way a lowpass filter
  in audio removes hiss above the range anything musical actually uses.

The building block for all three is one small math object called a
**biquad**, `biquad.py:16`. Don't let the name intimidate you: a biquad
looks at the last two input values and the last two output values it
already produced, and uses both to decide the next output. It's a fancier
version of a moving average, the same idea as a 7-day rolling average
smoothing a noisy stock price chart, except a biquad also remembers its own
recent *output*, not just recent input, which is what lets it do sharper
jobs like cutting one specific frequency instead of just smoothing
everything uniformly. The loop actually doing this, one sample at a time,
is `biquad.py:39`, the `process()` method.

`filter_chain.py:23` just runs your signal through three of these biquads in
a row: highpass, then notch, then lowpass, the same way you'd stack three
pedals or three EQ bands on a mixing desk.

**Checkpoint 2.** If you skipped the 50 Hz notch filter entirely, what would
show up in the recorded signal that has nothing to do with your muscle, and
why would that specifically be a problem for a classifier trying to tell
"rest" from "fist" apart?

<details>
<summary>Answer</summary>

A constant 50 Hz hum riding on top of every recording, regardless of
gesture, since it comes from ambient AC wiring, not your muscle. It would
inflate the measured amplitude and frequency-band features identically
during "rest" and "fist," partially masking the real amplitude difference
between them that the classifier depends on to tell the two apart, the same
way background hiss on a recording makes it harder to tell a quiet passage
from a slightly-less-quiet one.
</details>

---

## Part 4 - Windowing: from a continuous line to discrete chunks

A single instant of EMG, one sample, tells you nothing, it's just one noisy
number. You need to look at a short stretch and summarize it. This is
exactly why a smartwatch doesn't report your heart rate from one single
electrical tick, it looks at a short recent window of readings and
computes a rate from that window, the same way a 7-day moving average on a
stock chart tells you the trend without reacting to a single wild trading
day.

Here the window is 200 samples of signal (`config.py`, `WINDOW_SAMPLES` in
`emg_protocol.json`, which is 200 ms at 1000 Hz). It slides forward only
50 samples at a time (`HOP_SAMPLES`), not the full 200, so consecutive
windows overlap heavily. That overlap is what lets you get a fresh decision
every 50 ms, 20 times a second, without needing to collect any more raw
data than you already have, the same way a moving average recalculated
every single day (not just once a week) gives you a smoother, more
frequent trend line from the same underlying daily prices.

The code doing the sliding is `features.py:153`, `sliding_windows()`. Read
it, it is a two-line loop, and the fact that it is that short after
everything above is exactly the point: the physics justified *why* a
window of this size, the code itself is trivial once you know why.

**Checkpoint 3.** Sample rate is 1000 Hz and the window is 200 samples. In
milliseconds, how much history does each decision look at? And if you made
the window much bigger, say 1 full second, what would you gain and what
would you lose, using the moving-average comparison above?

<details>
<summary>Answer</summary>

200 samples at 1000 Hz = 200 ms of history per window. A bigger window
(like a 30-day moving average instead of a 7-day one) gives a smoother,
more stable read that's less thrown off by one noisy moment, but it reacts
slower to a genuine change, since it's still half full of old data even
after you've changed gesture. A smaller window reacts faster but is
noisier and more easily fooled by a single bad sample.
</details>

---

## Part 5 - Features: sixteen numbers instead of two hundred

A raw 200-sample window is still too messy and too large to hand a
classifier directly, and most of it is redundant, since consecutive EMG
samples are highly correlated. Instead, `features.py:56`, `extract()`,
reduces every window to **16 summary numbers**.

This is exactly what a fitness tracker does to your raw accelerometer data.
It doesn't feed a classifier the full wiggly line of your wrist's
acceleration every millisecond, it computes summary numbers first, step
count, average pace, how erratic the motion was, and classifies your
activity from those summaries. It's also what you do taking notes from a
lecture: you don't write down every word, you extract the handful of
points that actually distinguish one idea from another.

Grouped by what physical property they're sensitive to:

**Amplitude - how much electrical activity is present**
- `mav` mean absolute value - basically an average volume level
- `rms` root mean square - same idea as `mav` but weights big moments more,
  the way perceived loudness in audio is closer to RMS than a plain average
- `var` variance - how spread out the values are around the mean, which you
  already know from stats
- `logdet` log detector - similar role to `mav` but compresses very large
  spikes down, the same reason audio engineers use decibels (a log scale)
  instead of raw amplitude, because raw amplitude swings across too wide a
  range to compare usefully on a plain linear scale

**Complexity - how "busy" or jagged the waveform is**
- `wl` waveform length - literally the total up-and-down distance the trace
  travels. Picture two people pacing for the same 10 seconds: one walks
  steadily in a straight line, the other paces back and forth rapidly.
  Same average position, wildly different total distance covered, that
  total distance is waveform length.
- `zc` zero crossings - how often the signal flips from positive to negative,
  a rough proxy for how fast it's oscillating
- `ssc` slope sign changes - counts local peaks and valleys, another
  frequency proxy, like counting how many times a heart-rate line on a
  monitor changes from rising to falling within a window
- `wamp` Willison amplitude - counts big jumps between consecutive samples,
  a proxy for how many motor units are active at once, similar to counting
  how many sharp jolts a stock price makes in a day rather than smooth
  drifting

**Shape of the distribution**
- `skew` skewness - is the amplitude distribution lopsided (more values
  bunched on one side with a long tail on the other)
- `kurt` kurtosis - is it spiky (most values clustered tight, with a few
  big outliers) or flat (values spread fairly evenly)
  Both of these are exactly what you'd read off a histogram, like looking
  at a grading curve for a class: most students clustered around a B with
  a couple of outlier A's and F's looks very different from grades spread
  evenly from A to F, even if the average grade is identical in both cases.

**Frequency content - which frequencies dominate this window**

You know from stats that any signal can be broken into simpler repeating
patterns. Here, a window of EMG gets broken into how much of its energy
sits at different frequency ranges, the same operation your phone's music
equalizer display uses to show you a bass/mid/treble breakdown of a song
in real time.

- `bp_20_50`, `bp_50_100`, `bp_100_200`, `bp_200_450` - fraction of the
  window's total energy sitting in each of four frequency ranges, literally
  the same idea as an equalizer showing you how bass-heavy or treble-heavy
  a track currently sounds
- `mnf` mean frequency, `mdf` median frequency - the average and the
  midpoint of where that energy sits. Both of these drop as a muscle
  fatigues, a documented physiological effect, similar to how a singer's
  voice noticeably drops in pitch and clarity near the end of holding a
  long note as their vocal muscles tire

**Checkpoint 4.** If two gestures produced windows with identical `mav`
(same average amplitude) but very different `wl` (waveform length), what
would that tell you about how the muscle activity differs between them,
even though the "loudness" looks the same on paper?

<details>
<summary>Answer</summary>

Similar overall activity level, but very different behavior over time, the
higher-`wl` gesture is oscillating faster or more erratically within the
window (more back-and-forth movement per unit time), while the lower-`wl`
gesture holds a steadier level, the same distinction as the two people
pacing for 10 seconds in the waveform-length example above: same average
position in the room, very different amount of movement.
</details>

---

## Part 6 - The classifier: sorting into groups by their typical shape

### Building from variance to covariance

You already know variance: it tells you how spread out ONE set of numbers
is around its average. Covariance extends that idea to TWO sets of numbers
at once: does one tend to go up when the other goes up (positive
covariance), does one go up when the other goes down (negative), or are
they unrelated (near zero)? Height and weight across a group of people is
the classic example, taller people tend to weigh more, so those two
numbers have positive covariance.

A **covariance matrix** just records that pairwise relationship for every
pair of numbers at once, instead of one pair at a time. Here, there are 16
features per window, so the covariance matrix is a 16x16 table recording
how every feature relates to every other feature, which fits with the
matrices you already know, it's just bigger, and every entry has this
"do these two move together" meaning instead of being an arbitrary number.

### The classic toy example: sorting fruit

Picture sorting apples and oranges by two numbers: weight and redness.
Plot every fruit you've ever measured as a point on a graph, weight on one
axis, redness on the other. Apples cluster in roughly one region, oranges
in another. A new, unlabeled fruit gets sorted by asking: which cluster
does this point sit closest to, and if the clusters overlap a bit, which
one is it more *typical* of, given how much each fruit type's measurements
normally vary?

That "how much each type's measurements normally vary" part is exactly the
covariance idea above. If apple weights vary a lot but redness barely
varies, while oranges vary the opposite way, that's two different cluster
*shapes*, not just two different cluster *locations*.

### Same idea, scaled up

`classifier.py:45`, `LDAClassifier`, does exactly this fruit-sorting logic,
just with 16 numbers instead of 2, and 3 gesture classes (rest,
half_close, fist) instead of 2 fruit types. Each gesture's recorded windows
cluster together in that 16-number space, the same way apple measurements
cluster together in the weight/redness space. A new window gets classified
by which gesture's cluster it best matches.

`classifier.py:58`, `fit()`, is the training step, and reading through it
slowly maps directly onto the fruit example: it computes each gesture's
average position (`means`, the center of its cluster, like average
weight/redness for apples), how common each gesture was in your recordings
(`priors`), and the shared spread pattern across all gestures (`cov`, the
covariance matrix). The `shrinkage` step right after nudges that spread
estimate slightly toward a plain, evenly-round shape. This exists because
with only 16 features and a limited number of training windows, the raw
estimate of "how the 16 features vary together" can come out mathematically
unstable, similar to trying to judge how weight and redness typically
relate for apples from only 3 apples you've ever measured, not nearly
enough examples to trust the pattern yet.

One real simplification LDA makes: it assumes every gesture's cluster has
the *same shape*, just centered in a different place, like assuming apples
and oranges vary in weight and redness by the same amount and in the same
correlated way, they just happen to sit in different spots on the graph.
That assumption is what makes the boundary between gesture clusters come
out as a straight line rather than a curve. It's usually close enough to
true here, and it needs far less training data to estimate reliably than
letting every gesture have its own separate cluster shape would.

### Why LDA specifically, and not something else

`emg_protocol.json` originally specified `knn_k: 5`, meaning
**k-nearest neighbours**: classify a new point by finding its 5 closest
labelled examples and taking a vote among them. It was swapped for LDA here
for a concrete reason: kNN has to remember *every single training window
ever recorded* and compare a brand new reading against all of them, every
single time, 20 times a second, forever. That's like re-grading a test by
comparing it against every past test you've ever taken instead of just
knowing the grading rubric. LDA does the comparison work once, up front,
and boils it down into a compact rulebook (`mean_`, `std_`, `weights_`,
`bias_` in `classifier.py:151`, `save()`), so a live decision becomes one
quick calculation, not a search through your whole training history.

**Checkpoint 5.** In the fruit example, what would it mean if apples and
oranges had nearly identical average weight and redness, but very different
amounts of variation, say apples are always close to the same weight while
oranges vary wildly? Would LDA's shared-shape assumption struggle here, and
why?

<details>
<summary>Answer</summary>

It would mean the two clusters sit in roughly the same location on the
graph but have very different spreads, apples tightly bunched, oranges
scattered widely. LDA's shared-shape assumption would struggle here,
because it forces both fruits to be described by one common cluster shape,
which can't represent one being tight and the other being spread out. The
correct fix in that case is a classifier that allows each class its own
separate spread, and if you ever see this pattern show up between your
actual gestures (say "rest" is very consistent but "half_close" varies a
lot session to session), that's the sign LDA has hit its limit here.
</details>

---

## Part 7 - Validation: testing on questions you haven't seen

`evaluation.py:20`, `leave_one_recording_out()`, exists to answer one
question honestly: **how well will this actually work on data it has never
seen?**

You already know this trap from studying for exams. If you test yourself
using the exact same practice questions you memorized the answers to,
you'll score well no matter what, but that tells you nothing about whether
you actually understand the material. A fair test uses genuinely new
questions you haven't seen the answers to.

The exact same trap exists here. Consecutive EMG windows overlap 75%
(Part 4), so if you shuffled individual windows into train/test, near-
duplicate windows would land on both sides of the split, and the model
would essentially be tested on data it had already half-memorized. So
instead, this holds out **one entire recording session at a time**: train
on every session except one, test only on the session left out, repeat for
every session. That's the equivalent of testing yourself on a completely
different practice set than the one you studied from.

`evaluation.py:68`, `print_report()`, then prints a **confusion matrix**,
which is just a table showing, for each gesture, what the model actually
guessed instead. Rows are what you really did, columns are what it
predicted, the diagonal is correct guesses, and everything off the
diagonal shows a specific pair of gestures being mixed up, exactly like a
study report showing you which two topics you personally keep confusing on
practice tests.

**Checkpoint 6.** If you validated by shuffling all your EMG windows
randomly instead of holding out whole recordings, would the reported
accuracy be too high, too low, or unpredictable, and why specifically?

<details>
<summary>Answer</summary>

Too high. Because windows overlap 75%, a shuffled split would place windows
that are 75% identical to each other on both the training and the test
side, so the model would effectively be tested on data it had already seen
in near-duplicate form. That produces an inflated accuracy number that has
nothing to do with how it'll perform on a genuinely new session, the same
way scoring well on the exact practice questions you memorized tells you
nothing about how you'd do on the real exam.
</details>

---

## Part 8 - Smoothing: this is a thermostat, not a light switch

The classifier makes a fresh decision every 50 ms, 20 times a second, and
it will occasionally be wrong, especially mid-transition between two
gestures when the signal genuinely resembles both. If every raw decision
went straight to the servos, the hand would flicker unstably between poses,
the same way a cheap thermostat that reacted instantly to every tiny
temperature blip would click the AC on and off constantly instead of
holding a steady setting.

A real thermostat avoids that with the same three ideas
`smoother.py:28`, `GestureSmoother`, uses:

- It ignores tiny, uncertain readings rather than reacting to every one.
  `smoother.py:40`, `update()`, discards any decision below 60%
  confidence (`CONFIDENCE_THRESHOLD`) before it even gets counted, so a
  genuinely ambiguous moment doesn't get to influence anything.
- It waits for a consistent trend, not one reading. The last 5 confident
  decisions are kept, and at least 3 of them (`VOTE_MAJORITY` out of
  `VOTE_WINDOW`) need to agree before the hand actually commits to a new
  gesture, the same way a thermostat waits for the temperature to be
  consistently off target, not just one momentary blip, before switching
  the AC on.
- It won't flip back again immediately. Once a gesture is committed to, it
  has to hold for at least 0.25 seconds (`DWELL_SECONDS`) before it's
  allowed to change again. This exists because a human hand simply cannot
  usefully change gesture faster than a few times a second, so anything
  quicker than that is noise by definition, the exact reason your home
  thermostat has a minimum cycle time built in so the compressor doesn't
  slam on and off every few seconds.

**Checkpoint 7.** Why does throwing out low-confidence readings *before*
the majority vote (rather than letting them vote and just lose) matter?
Think about what happens if there's a sustained run of ambiguous, "maybe
fist" readings while you're actually resting.

<details>
<summary>Answer</summary>

If low-confidence guesses were allowed to vote, a sustained run of
ambiguous readings that all happen to lean one way could accumulate a
majority on their own, purely because they were consistent, even though
none of them were individually trustworthy. Throwing them out before the
vote means only genuinely confident evidence can change the held gesture,
so a stretch of uncertainty just holds the current pose instead of
drifting toward whatever the ambiguous readings happened to lean toward,
the same reason a thermostat should ignore a flickering, unreliable sensor
reading rather than let a string of glitchy readings talk it into
switching the AC on.
</details>

---

## Part 9 - Effort tracking: adjusting to what's normal right now

EMG amplitude has no fixed, absolute meaning. The same clench produces a
different raw amplitude on Monday versus Wednesday, because electrode
placement, skin moisture, and contact quality all shift slightly session
to session. A fixed threshold calibrated once would drift out of accuracy
over time, the same way your phone's screen doesn't use one fixed
brightness all day, it constantly checks the current ambient light level
and adjusts, because "bright enough" means something different at noon
outdoors versus in a dark room at night.

`amplitude.py:28`, `AmplitudeTracker`, does that adjustment live. It tracks
a slowly adapting **rest baseline**, `amplitude.py:44`, `update()`, only
refreshes this while you're actually resting, so a long grip can't drag the
baseline upward, and a slowly decaying **running maximum**. Effort is then
just reported as where the current amplitude sits between those two live
references, 0 to 1, constantly re-calibrating itself to whatever's normal
for this specific session instead of relying on a fixed number set once and
never revisited.

---

## Part 10 - Output: the part with no exotic theory

`driver.py:27`, `HandDriver`, is the simplest stage. It converts a gesture
name and an effort value into servo angles and writes them out. The one
thing worth knowing here is not physics or math, it's a **wiring
convention** from your own config: in `emg_protocol.json`, `rest` maps to
`[180, 180, ...]` and `fist` maps to `[0, 0, ...]`, so 180 degrees means
fully open and 0 means fully closed. That's why `driver.py:68`,
`target_angles()`, never hardcodes "closed = 0" anywhere, every pose is
looked up from that table, so the direction convention only has to be
correct in one place.

---

## Everyday translation table

| EMG / DSP / ML term | Everyday equivalent |
|---|---|
| Channel (one electrode) | One sensor input, like one axis of an accelerometer |
| Sample rate (Hz) | How many readings per second, like a heart monitor's refresh rate |
| Window (200 samples) | A short recent stretch, like a 7-day moving average window |
| Hop size, window overlap | How often you recompute that moving average (daily vs weekly) |
| Highpass filter | Bass cut / low-cut on an audio EQ |
| Notch filter | Removing one specific hum tone from a recording |
| Lowpass filter | Treble cut / hiss removal |
| Biquad / IIR filter | A moving average that also remembers its own recent output |
| Feature (mav, wl, etc.) | A summary stat, like steps or avg pace from raw accelerometer data |
| Frequency band power | Bass/mid/treble split on a music equalizer |
| Feature vector (16 numbers) | The row of stats a fitness tracker computes per activity window |
| Covariance matrix | Table of "do these two things vary together" for every pair of features |
| LDA classifier | Sorting fruit into clusters by typical weight/color, generalized to 16 numbers |
| Class mean / covariance | A cluster's center and its typical shape of variation |
| Confusion matrix | A study report showing which two topics you keep mixing up |
| Leave-one-recording-out | Testing yourself on questions you didn't study from |
| Majority-vote smoothing | A thermostat requiring a sustained trend before switching |
| Confidence threshold gate | Ignoring a flickery, unreliable sensor reading |
| Amplitude baseline tracking | Auto screen brightness adjusting to current ambient light |

---

## Where to actually go next

Don't read the code linearly file by file. Instead, for each part above,
open the exact file and line referenced, and try to explain out loud what
each line is doing *before* checking whether your explanation matches the
comment already there. If a line's purpose doesn't click even after
matching it to the physics above, that is the one to ask about specifically
- not "explain classifier.py to me," but "why does `predict_proba()`
(`classifier.py:129`) subtract the row max before exponentiating."
