#include "EMG_Filter_Custom.h"

EMGFilterCustom::EMGFilterCustom() {
    _fs     = 1000.0;
    _centre = 512.0;
    reset();
}

void EMGFilterCustom::init(float sampleRate,
                           float notchFreq,
                           float notchQ,
                           float hpFreq,
                           float envFreq) {
    _fs = sampleRate;

    // 60 Hz notch, biquad, direct form 1
    float w0    = 2.0 * PI * notchFreq / _fs;
    float alpha = sin(w0) / (2.0 * notchQ);
    float a0    = 1.0 + alpha;
    _nb0 =  1.0 / a0;
    _nb1 = -2.0 * cos(w0) / a0;
    _nb2 =  1.0 / a0;
    _na1 = -2.0 * cos(w0) / a0;
    _na2 = (1.0 - alpha) / a0;

    // first-order high-pass
    float rcHP = 1.0 / (2.0 * PI * hpFreq);
    _hpA = rcHP / (rcHP + 1.0 / _fs);

    // first-order low-pass on the rectified signal
    float rcEnv = 1.0 / (2.0 * PI * envFreq);
    _envA = (1.0 / _fs) / (rcEnv + 1.0 / _fs);

    reset();
                           }

                           void EMGFilterCustom::reset() {
                               _nx1 = _nx2 = _ny1 = _ny2 = 0.0;
                               _hpPrevIn = _hpPrevOut = 0.0;
                               _env = 0.0;
                               _lastNotch = _lastHp = 0.0;
                           }

                           float EMGFilterCustom::update(int raw) {
                               float x = (float)raw - _centre;

                               // notch
                               float y = _nb0 * x + _nb1 * _nx1 + _nb2 * _nx2
                               - _na1 * _ny1 - _na2 * _ny2;
                               _nx2 = _nx1; _nx1 = x;
                               _ny2 = _ny1; _ny1 = y;
                               _lastNotch = y;

                               // high-pass
                               float hp = _hpA * (_hpPrevOut + y - _hpPrevIn);
                               _hpPrevIn  = y;
                               _hpPrevOut = hp;
                               _lastHp = hp;

                               // rectify + smooth
                               _env += _envA * (fabs(hp) - _env);

                               return _env;
                           }
