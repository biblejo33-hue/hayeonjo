import numpy as np, librosa, soundfile as sf, json, sys

SRC = "/root/.claude/uploads/78895e4a-7b28-5945-8eae-1ed477f41d4b/125a20d2-LG_asitwas_remix.mp3"
y, sr = librosa.load(SRC, sr=44100, mono=True)
dur = len(y)/sr
print(f"duration: {dur:.2f}s  sr={sr}")

# tempo
tempo, beats = librosa.beat.beat_track(y=y, sr=sr, units='time')
tempo = float(np.atleast_1d(tempo)[0])
print(f"tempo(est): {tempo:.2f} BPM   beats: {len(beats)}")
onset_env = librosa.onset.onset_strength(y=y, sr=sr)
for st in (60,90,120,160):
    t2,_ = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr, start_bpm=st, units='time')
    print("  start_bpm",st,"->",float(np.atleast_1d(t2)[0]))

# key via chroma
chroma = librosa.feature.chroma_cqt(y=y, sr=sr, bins_per_octave=36)
cmean = chroma.mean(axis=1)
NOTES=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
print("chroma profile:", {NOTES[i]: round(float(cmean[i]),3) for i in np.argsort(-cmean)})

maj=np.array([6.35,2.23,3.48,2.33,4.38,4.09,2.52,5.19,2.39,3.66,2.29,2.88])
mnr=np.array([6.33,2.68,3.52,5.38,2.60,3.53,2.54,4.75,3.98,2.69,3.34,3.17])
def corr(a,b): 
    a=(a-a.mean())/a.std(); b=(b-b.mean())/b.std(); return float((a*b).mean())
scores=[]
for i in range(12):
    scores.append((corr(cmean, np.roll(maj,i)), f"{NOTES[i]} major"))
    scores.append((corr(cmean, np.roll(mnr,i)), f"{NOTES[i]} minor"))
scores.sort(reverse=True)
print("key candidates:", [(k, round(s,3)) for s,k in scores[:5]])

# rms envelope per 2s to see structure
hop=sr*2
rms=[float(np.sqrt(np.mean(y[i:i+hop]**2))) for i in range(0,len(y),hop)]
print("RMS/2s:", " ".join(f"{i*2}s:{v:.3f}" for i,v in enumerate(rms)))
json.dump({"duration":dur,"tempo":tempo,"beats":beats.tolist()}, open("/home/user/hayeonjo/jazz/analysis.json","w"))
