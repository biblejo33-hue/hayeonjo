import numpy as np, librosa, json
SRC="/root/.claude/uploads/78895e4a-7b28-5945-8eae-1ed477f41d4b/125a20d2-LG_asitwas_remix.mp3"
y,sr=librosa.load(SRC,sr=22050,mono=True)
oe=librosa.onset.onset_strength(y=y,sr=sr)
tempo,beats=librosa.beat.beat_track(onset_envelope=oe,sr=sr,start_bpm=172,units='frames')
tempo=float(np.atleast_1d(tempo)[0])
bt=librosa.frames_to_time(beats,sr=sr)
print(f"tempo={tempo:.3f} beats={len(bt)} first={bt[0]:.3f} last={bt[-1]:.3f}")
d=np.diff(bt); print(f"median beat interval={np.median(d):.4f}s -> {60/np.median(d):.2f} BPM")

# harmonic chroma
yh=librosa.effects.harmonic(y, margin=3)
ch=librosa.feature.chroma_cqt(y=yh,sr=sr,bins_per_octave=36)
NOTES=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
# templates
tpl={}
def add(name,ints):
    for r in range(12):
        v=np.zeros(12)
        for i in ints: v[(r+i)%12]=1
        tpl[f"{NOTES[r]}{name}"]=v/np.linalg.norm(v)
add("",[0,4,7]); add("m",[0,3,7]); add("maj7",[0,4,7,11]); add("m7",[0,3,7,10]); add("7",[0,4,7,10]); add("sus4",[0,5,7])
names=list(tpl); M=np.stack([tpl[n] for n in names])

# per-bar (4 beats) chords, assume downbeat at bt[0]
bar_starts=bt[::4]
rows=[]
for i in range(len(bar_starts)-1):
    a,b=bar_starts[i],bar_starts[i+1]
    fa,fb=librosa.time_to_frames([a,b],sr=sr)
    seg=ch[:,fa:fb]
    if seg.shape[1]<2: continue
    v=seg.mean(axis=1); v=v/ (np.linalg.norm(v)+1e-9)
    s=M@v; k=int(np.argmax(s))
    rows.append((i,round(float(a),2),names[k],round(float(s[k]),3)))
print("bar  time   chord  conf")
for r in rows: print(f"{r[0]:>3} {r[1]:>6} {r[2]:>7} {r[3]}")
json.dump({"tempo":tempo,"beats":bt.tolist(),"bars":[r[1] for r in bar_starts.tolist() and [(x,) for x in bar_starts]]}, open("/home/user/hayeonjo/jazz/beats.json","w"), default=float)
