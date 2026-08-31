import numpy as np, librosa, soundfile as sf, json, os

SR = 44100
SRC = "work/original.mp3"
os.makedirs("work", exist_ok=True)

y, _ = librosa.load(SRC, sr=SR, mono=False)
if y.ndim == 1: y = np.vstack([y, y])
L, R = y[0], y[1]
mono = (L + R) / 2
dur = len(mono) / SR
print(f"duration {dur:.2f}s  shape {y.shape}")

# --- HPSS per channel (soft mask, margin for a cleaner split) ---
NF, HOP = 2048, 512
def hpss_ch(x):
    S = librosa.stft(x, n_fft=NF, hop_length=HOP)
    H, P = librosa.decompose.hpss(S, margin=(1.0, 3.0), power=2.0)
    return (librosa.istft(H, hop_length=HOP, length=len(x)),
            librosa.istft(P, hop_length=HOP, length=len(x)))

hL, pL = hpss_ch(L); hR, pR = hpss_ch(R)
harm = np.vstack([hL, hR]); perc = np.vstack([pL, pR])
sf.write("work/harmonic.wav", harm.T, SR, subtype="FLOAT")
sf.write("work/percussive.wav", perc.T, SR, subtype="FLOAT")
print("HPSS done. harm rms", float(np.sqrt((harm**2).mean())),
      "perc rms", float(np.sqrt((perc**2).mean())))

# --- tempo / beat grid from percussive part ---
pmono = (pL + pR) / 2
onset = librosa.onset.onset_strength(y=pmono, sr=SR, hop_length=HOP)
tempo, beats = librosa.beat.beat_track(onset_envelope=onset, sr=SR, hop_length=HOP, units="time")
tempo = float(np.atleast_1d(tempo)[0])
print(f"tracked tempo {tempo:.2f} BPM, {len(beats)} beats")

# fit a rigid grid (song is machine-timed): t = a*k + b, robust to outliers
k = np.arange(len(beats)); a, b = np.polyfit(k, beats, 1)
for _ in range(3):
    res = np.abs(beats - (a * k + b)); keep = res < max(0.06, 2 * res.std())
    a, b = np.polyfit(k[keep], beats[keep], 1)
grid_bpm = 60.0 / a
print(f"rigid grid: {grid_bpm:.3f} BPM  first beat {b:.4f}s  (kept {int(keep.sum())}/{len(beats)})")

# --- low-band onset energy, to pick half-time phase and downbeat ---
Sp = np.abs(librosa.stft(pmono, n_fft=NF, hop_length=HOP))
freqs = librosa.fft_frequencies(sr=SR, n_fft=NF)
low = Sp[freqs < 160].sum(axis=0)
low_on = np.maximum(0, np.diff(low, prepend=low[0]))
times = librosa.frames_to_time(np.arange(len(low_on)), sr=SR, hop_length=HOP)

nb = int((dur - b) / a)
bt = b + a * np.arange(nb)
def energy_at(ts, w=0.05):
    return np.array([low_on[(times > t - w) & (times < t + w)].sum() for t in ts])
be = energy_at(bt)

half_phase = int(np.argmax([be[p::2].sum() for p in range(2)]))
qt = bt[half_phase::2]                       # half-time quarter notes
qe = be[half_phase::2]
down_phase = int(np.argmax([qe[p::4].sum() for p in range(4)]))
print(f"half-time phase {half_phase}, downbeat phase {down_phase}")
print(f"half-time BPM {grid_bpm/2:.2f}, first downbeat {qt[down_phase]:.4f}s")

# --- chord rotation: F#m - D - A - E, one chord per half-time bar ---
chroma = librosa.feature.chroma_cqt(y=librosa.effects.harmonic(mono), sr=SR, hop_length=HOP)
ctimes = librosa.frames_to_time(np.arange(chroma.shape[1]), sr=SR, hop_length=HOP)
bar_len = a * 8
bars = np.arange(qt[down_phase], dur - bar_len, bar_len)
N = {n: i for i, n in enumerate(['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'])}
def tmpl(root, minor):
    v = np.zeros(12); iv = [0,3,7] if minor else [0,4,7]
    for i in iv: v[(N[root] + i) % 12] = 1
    return v / np.linalg.norm(v)
prog = [tmpl('F#',1), tmpl('D',0), tmpl('A',0), tmpl('E',0)]
barvec = []
for t in bars:
    m = (ctimes >= t) & (ctimes < t + bar_len)
    v = chroma[:, m].mean(axis=1); n = np.linalg.norm(v)
    barvec.append(v / n if n > 0 else v)
scores = [float(np.mean([barvec[i] @ prog[(i + rot) % 4] for i in range(len(barvec))])) for rot in range(4)]
best = int(np.argmax(scores))
print("chord rotation scores", [round(s,4) for s in scores], "-> best rot", best,
      "=", ['F#m','D','A','E'][best % 4], "on bar 1")

json.dump(dict(sr=SR, dur=dur, grid_bpm=grid_bpm, beat_a=a, beat_b=b,
               half_phase=half_phase, down_phase=down_phase,
               first_downbeat=float(qt[down_phase]), chord_rot=best,
               chord_scores=scores), open("work/analysis.json","w"), indent=2)
print("saved work/analysis.json")
