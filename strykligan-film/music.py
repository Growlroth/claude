"""Syntetiserar ljudspåret (45 s, 120 BPM) synkat mot filmens klipp."""
import numpy as np
import wave

SR = 44100
DUR = 45.0
N = int(SR * DUR)
rng = np.random.default_rng(7)

def buf():
    return np.zeros(N + SR * 3)

def place(dst, sig, t0, amp=1.0):
    i = int(t0 * SR)
    if i < 0:
        sig = sig[-i:]; i = 0
    end = min(len(dst), i + len(sig))
    dst[i:end] += sig[: end - i] * amp

def env_exp(n, decay):
    return np.exp(-np.arange(n) / SR / decay)

def fft_filter(x, lo=None, hi=None):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    m = np.ones_like(f)
    if hi: m *= 1 / np.sqrt(1 + (f / hi) ** 4)
    if lo: m *= 1 / np.sqrt(1 + (lo / np.maximum(f, 1)) ** 4)
    return np.fft.irfft(X * m, len(x))

def sweep_filter(x, t0, cut_fn, hop=1024):
    """Tidsvarierande lågpass via överlappande FFT-block."""
    win = np.hanning(hop * 2)
    out = np.zeros(len(x) + hop * 2)
    f = np.fft.rfftfreq(hop * 2, 1 / SR)
    for s in range(0, len(x), hop):
        seg = x[s:s + hop * 2]
        if len(seg) < hop * 2: seg = np.pad(seg, (0, hop * 2 - len(seg)))
        c = cut_fn(t0 + s / SR)
        X = np.fft.rfft(seg * win) / np.sqrt(1 + (f / c) ** 4)
        out[s:s + hop * 2] += np.fft.irfft(X, hop * 2)
    return out[: len(x)]

# ---------- instrument ----------
def kick(amp=1.0, big=False):
    n = int(SR * (0.9 if big else 0.45))
    t = np.arange(n) / SR
    f = 45 + (170 if big else 130) * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) * np.exp(-t / (0.45 if big else 0.22))
    click = rng.standard_normal(n) * np.exp(-t * 400) * 0.3
    return np.tanh((s + click) * 1.6) * amp

def clap(amp=1.0):
    n = int(SR * 0.3)
    t = np.arange(n) / SR
    e = np.zeros(n)
    for d in (0, 0.011, 0.022):
        e += (t >= d) * np.exp(-np.maximum(t - d, 0) * (60 if d < 0.02 else 18))
    s = fft_filter(rng.standard_normal(n), lo=900, hi=5000) * e
    return s / np.abs(s).max() * amp

def hat(amp=1.0, open_=False):
    n = int(SR * (0.25 if open_ else 0.06))
    s = fft_filter(rng.standard_normal(n), lo=7000) * env_exp(n, 0.08 if open_ else 0.015)
    return s / np.abs(s).max() * amp

def tick(freq=2200, amp=1.0):
    n = int(SR * 0.03)
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * freq * t) * np.exp(-t * 200) * amp

def saw(freq, n, detune=0.0):
    t = np.arange(n) / SR
    ph = (freq * (1 + detune) * t + rng.random()) % 1.0
    return 2 * ph - 1

def supersaw(freqs, dur, cutoff):
    n = int(SR * dur)
    s = np.zeros(n)
    for fq in freqs:
        for d in (-0.012, -0.006, 0, 0.006, 0.012):
            s += saw(fq, n, d)
    s = fft_filter(s, hi=cutoff)
    return s / (np.abs(s).max() + 1e-9)

def pluck(freq, amp=1.0, dur=0.25):
    n = int(SR * dur)
    t = np.arange(n) / SR
    s = (np.sin(2*np.pi*freq*t) + 0.5*np.sin(4*np.pi*freq*t) + 0.25*np.sin(6*np.pi*freq*t))
    return s * np.exp(-t / 0.09) * amp

def bass(freq, dur, amp=1.0):
    n = int(SR * dur)
    t = np.arange(n) / SR
    s = saw(freq, n) + 0.6 * np.sin(2 * np.pi * freq * t)
    s = fft_filter(s, hi=380)
    a = np.minimum(1, t / 0.005) * np.exp(-t / (dur * 0.9))
    return s / (np.abs(s).max() + 1e-9) * a * amp

def boom(amp=1.0):
    n = int(SR * 2.5)
    t = np.arange(n) / SR
    f = 32 + 60 * np.exp(-t * 6)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.9)
    nz = fft_filter(rng.standard_normal(n), hi=2500) * np.exp(-t / 0.5) * 0.25
    return np.tanh((s + nz) * 1.4) * amp

def crash(amp=1.0):
    n = int(SR * 2.5)
    s = fft_filter(rng.standard_normal(n), lo=4000) * env_exp(n, 0.7)
    return s / np.abs(s).max() * amp

def hz(note):
    return 440.0 * 2 ** ((note - 69) / 12)

# ackord: Am, F, C, G (MIDI)
CHORDS = [[57, 60, 64], [53, 57, 60], [55, 60, 64], [55, 59, 62]]
ROOTS = [33, 29, 36, 31]

drums, music, verbsend, sc = buf(), buf(), buf(), buf()

# ---------- 0–2: pad-uppbyggnad + omvänd cymbal ----------
pad = supersaw([hz(n) for n in CHORDS[0]] + [hz(45)], 2.2, 900)
pad *= np.linspace(0, 1, len(pad)) ** 2
place(music, pad, 0.0, 0.22); place(verbsend, pad, 0.0, 0.25)
rc = crash()[::-1][-int(SR*1.6):]
place(drums, rc, 2.0 - 1.6, 0.35)

# ---------- impacts ----------
for t0, a in [(2.0, 1.0), (5.0, 0.9)]:
    place(drums, boom(), t0, a); place(sc, np.ones(int(SR*0.3)), t0)

# ---------- 2–8: hjärtslag ----------
for i in range(12):
    t0 = 2.0 + i * 0.5
    place(drums, kick(), t0, 0.75 if i % 2 == 0 else 0.45)
for i in range(6):
    place(drums, tick(2400), 5.25 + i * 0.5, 0.25)
lowpad = supersaw([hz(45), hz(52)], 6.0, 400)
lowpad *= np.minimum(1, np.linspace(0, 6, len(lowpad))) * np.linspace(1, 0.6, len(lowpad))
place(music, lowpad, 2.0, 0.25)
for i in range(24):
    place(drums, hat(), 5.0 + i * 0.125, 0.08 + 0.04 * (i % 2))

# ---------- 8–12: kupongen – arpeggio ----------
arp = [69, 72, 76, 81]
for i in range(32):
    t0 = 8.0 + i * 0.125
    bar = int((t0 - 8.0) // 2) % 4
    notes = [n + 12 for n in CHORDS[bar]] + [CHORDS[bar][0] + 24]
    p = pluck(hz(notes[i % 4]), 0.35)
    place(music, p, t0); place(verbsend, p, t0, 0.3)
for i in range(8):
    place(drums, kick(), 8.0 + i * 0.5, 0.6)
    place(drums, hat(), 8.25 + i * 0.5, 0.18)
for t0 in (9.0, 9.5, 10.0):
    place(drums, clap(), t0, 0.6); place(drums, boom(), t0, 0.35)
for i in range(4):
    place(music, bass(hz(ROOTS[i % 4] + 12), 1.0), 8.0 + i, 0.3)

# ---------- 12–26.5: full groove ----------
def groove(t_start, t_end, dark=False):
    b = 0
    t0 = t_start
    while t0 < t_end - 1e-6:
        place(drums, kick(), t0, 0.95); place(sc, np.ones(int(SR*0.12)), t0)
        place(drums, hat(), t0 + 0.25, 0.22)
        if b % 2 == 1: place(drums, clap(), t0, 0.55); place(verbsend, clap(), t0, 0.15)
        bar = int((t0 - 12.0) // 2) % 4
        root = ROOTS[bar] - (1 if dark and bar % 2 == 0 else 0)
        for k in range(2):
            place(music, bass(hz(root + 12 * (k % 2)), 0.24), t0 + k * 0.25, 0.55)
        b += 1; t0 += 0.5

groove(12.0, 17.0)
groove(17.0, 22.0, dark=True)
groove(22.0, 26.5)
for bar_t in np.arange(12.0, 26.0, 2.0):
    bar = int((bar_t - 12.0) // 2) % 4
    ch = supersaw([hz(n) for n in CHORDS[bar]], 2.0, 1400)
    ch *= np.minimum(1, np.arange(len(ch)) / SR / 0.02)
    place(music, ch, bar_t, 0.14); place(verbsend, ch, bar_t, 0.12)
for t0 in (12.0, 17.0, 22.0):
    place(drums, crash(), t0, 0.35); place(drums, boom(), t0, 0.5)
place(drums, kick(big=True), 19.5, 0.8); place(drums, boom(), 19.5, 0.6)
for i in range(8):
    place(drums, tick(1800 + (i % 2) * 400), 23.0 + i * 0.25, 0.18)

# ---------- 26.5–32: uppbyggnad ----------
roll_times = list(np.arange(26.5, 28.5, 0.5)) + list(np.arange(28.5, 30.0, 0.25)) + \
             list(np.arange(30.0, 31.0, 0.125)) + list(np.arange(30.5, 31.0, 0.0625))
for i, t0 in enumerate(sorted(set(np.round(roll_times, 4)))):
    place(drums, clap(), t0, 0.3 + 0.5 * (t0 - 26.5) / 4.5)
for i in range(7):
    place(drums, kick(), 26.5 + i * 0.5, 0.9)
rn = int(SR * 4.5)
riser = rng.standard_normal(rn)
riser = sweep_filter(riser, 26.5, lambda t: 300 * (18000 / 300) ** min(1, (t - 26.5) / 4.5))
riser *= np.linspace(0, 1, rn) ** 2
place(music, riser / np.abs(riser).max(), 26.5, 0.35)
t = np.arange(rn) / SR
sine_r = np.sin(2 * np.pi * np.cumsum(110 * 2 ** (t / 4.5 * 3)) / SR) * np.linspace(0, 1, rn) ** 1.5
place(music, sine_r, 26.5, 0.12)
bar_bass = bass(hz(33), 4.5, 1.0) * np.linspace(0.3, 1, rn)
place(music, bar_bass, 26.5, 0.3)
# andhämtning 31.0–32.0: bara ett omvänt svep
rs = supersaw([hz(n) for n in CHORDS[0]], 1.0, 3000)[::-1] * np.linspace(0, 1, SR) ** 3
place(music, rs, 31.0, 0.25)

# ---------- 32–40: DROPPEN ----------
place(drums, boom(), 32.0, 1.1); place(drums, crash(), 32.0, 0.6)
place(drums, crash(), 36.0, 0.45); place(drums, boom(), 37.0, 0.8)
b = 0
t0 = 32.0
while t0 < 40.0 - 1e-6:
    place(drums, kick(big=(b % 8 == 0)), t0, 1.0); place(sc, np.ones(int(SR*0.12)), t0)
    place(drums, hat(open_=True), t0 + 0.25, 0.2)
    place(drums, hat(), t0 + 0.125, 0.1); place(drums, hat(), t0 + 0.375, 0.1)
    if b % 2 == 1: place(drums, clap(), t0, 0.7); place(verbsend, clap(), t0, 0.2)
    bar = int((t0 - 32.0) // 2) % 4
    for k in range(4):
        place(music, bass(hz(ROOTS[bar] + (12 if k % 2 else 0)), 0.12), t0 + k * 0.125, 0.6)
    b += 1; t0 += 0.5
for bar_t in np.arange(32.0, 40.0, 2.0):
    bar = int((bar_t - 32.0) // 2) % 4
    notes = CHORDS[bar] + [CHORDS[bar][0] + 12, CHORDS[bar][1] + 12]
    ch = supersaw([hz(n) for n in notes], 2.0, 4200)
    place(music, ch, bar_t, 0.24); place(verbsend, ch, bar_t, 0.18)
    lead = [81, 84, 88, 84, 81, 79, 77, 79] if bar % 2 == 0 else [76, 79, 81, 84, 83, 81, 79, 76]
    for k, nn in enumerate(lead):
        p = pluck(hz(nn), 0.28, 0.3)
        place(music, p, bar_t + k * 0.25); place(verbsend, p, bar_t + k * 0.25, 0.35)
for i in range(16):  # klockan snurrar 36–37
    place(drums, tick(1500 + i * 120), 36.0 + i * 0.0625, 0.25)

# ---------- 40–45: slutackord ----------
place(drums, boom(), 40.0, 0.9); place(drums, crash(), 40.0, 0.5); place(drums, kick(big=True), 40.0, 0.9)
fin = supersaw([hz(n) for n in [45, 57, 60, 64, 69, 72]], 5.0, 2500)
fin *= np.exp(-np.arange(len(fin)) / SR / 2.2)
place(music, fin, 40.0, 0.3); place(verbsend, fin, 40.0, 0.35)

# ---------- mix ----------
ir_n = int(SR * 2.2)
ir = rng.standard_normal(ir_n) * np.exp(-np.arange(ir_n) / SR / 0.55)
ir = fft_filter(ir, hi=6000)
L = len(verbsend) + ir_n
verb = np.fft.irfft(np.fft.rfft(verbsend, L) * np.fft.rfft(ir, L), L)[: len(verbsend)]
verb /= np.abs(verb).max() + 1e-9

# sidechain-pump
scenv = np.convolve(np.minimum(sc, 1), np.exp(-np.arange(int(SR*0.25)) / SR / 0.08))[: len(sc)]
duck = 1 - 0.55 * np.clip(scenv / (scenv.max() + 1e-9), 0, 1)

mix = drums * 0.9 + music * duck + verb * 0.18 * duck
mix = mix[:N]
fade = np.ones(N); fl = int(SR * 1.2); fade[-fl:] = np.linspace(1, 0, fl) ** 2
mix *= fade
mix = np.tanh(mix / np.abs(mix).max() * 1.4)
mix = mix / np.abs(mix).max() * 0.93

# enkel stereobredd: reverb något förskjuten
d = int(SR * 0.012)
left = mix
right = np.concatenate([mix[:d], mix[:-d]]) * 0.15 + mix * 0.85
stereo = np.stack([left, right], 1)
pcm = (np.clip(stereo, -1, 1) * 32767).astype(np.int16)
with wave.open("music.wav", "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print("ok", pcm.shape)
