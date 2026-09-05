#ifndef EMG_FILTER_CUSTOM_H
#define EMG_FILTER_CUSTOM_H

#if defined(ARDUINO) && ARDUINO >= 100
#include "Arduino.h"
#else
#include "WProgram.h"
#endif

/*
 * EMG_Filter_Custom
 *
 * Notch -> high-pass -> rectify -> envelope, one sample at a time.
 * Each instance keeps its own state, so use one object per channel.
 *
 * Notes:
 *  - the notch is a discrete IIR: it is only correct at the sample rate
 *    you declare, so the calling sketch must actually run at that rate
 *  - notch Q is deliberately narrow; EMG content sits near 50-150 Hz and a
 *    wide notch deletes real signal
 *  - mains is a single fixed frequency per grid (NA 60, EU 50), not a range
 */

class EMGFilterCustom {
public:
    EMGFilterCustom();

    // sampleRate  Hz, must match the sketch's actual loop rate
    // notchFreq   60.0 in North America, 50.0 in Europe
    // notchQ      higher = narrower. 8.0 is a good default
    // hpFreq      high-pass corner, strips drift and motion artifact
    // envFreq     envelope smoothing corner. lower = smoother, slower
    void init(float sampleRate,
              float notchFreq = 60.0,
              float notchQ    = 8.0,
              float hpFreq    = 10.0,
              float envFreq   = 3.0);

    // feed one raw analogRead value, get the envelope back
    float update(int raw);

    // intermediate stages, useful for plotting or debugging
    float lastNotched()  const { return _lastNotch; }
    float lastFiltered() const { return _lastHp; }
    float envelope()     const { return _env; }

    // clear history, e.g. after re-seating electrodes
    void reset();

    // ADC midpoint. 512 for a 10-bit ADC, 2048 for 12-bit
    void setCentre(float centre) { _centre = centre; }

private:
    float _fs, _centre;

    float _nb0, _nb1, _nb2, _na1, _na2;
    float _nx1, _nx2, _ny1, _ny2;

    float _hpA, _hpPrevIn, _hpPrevOut;

    float _envA, _env;

    float _lastNotch, _lastHp;
};

#endif
