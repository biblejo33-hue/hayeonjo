import numpy as np, librosa, json
from scipy.signal import butter, sosfilt
SR=44100; A=json.load(open("work/analysis.json"))
y,_=librosa.load("work/original.mp3",sr=SR,mono=True)
bass=sosfilt(butter(4,[55/(SR/2),260/(SR/2)],btype="band",output="sos"),y)
NN=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
cb=librosa.feature.chroma_cqt(y=bass,sr=SR,hop_length=512,fmin=librosa.note_to_hz('C2'),n_octaves=3)
cf=librosa.feature.chroma_cqt(y=librosa.effects.harmonic(y),sr=SR,hop_length=512)
ct=librosa.frames_to_time(np.arange(cb.shape[1]),sr=SR,hop_length=512)
bar=A["beat_a"]*8; t0=A["first_downbeat"]
res=[]
for b in range(int((A["dur"]-t0)/bar)):
    bt=t0+b*bar; m=(ct>=bt)&(ct<bt+bar)
    if m.sum()==0: continue
    vb=cb[:,m].mean(1); vf=cf[:,m].mean(1)
    root=int(np.argmax(vb)); conf=float(vb[root]/(vb.sum()+1e-9))
    m3,M3=vf[(root+3)%12],vf[(root+4)%12]
    qual='m' if m3>M3 else ''; qconf=float(abs(m3-M3)/(m3+M3+1e-9))
    res.append((b,NN[root]+qual,conf,qconf))
print("first 24 bars:"); print("  "+"  ".join(f"{r[1]}" for r in res[:24]))
roots=[r[1].rstrip('m') for r in res]
from collections import Counter
print("root histogram:",Counter(roots).most_common(8))
exp={'F#','D','A','E'}
print(f"in expected key set: {sum(r in exp for r in roots)}/{len(roots)} = {sum(r in exp for r in roots)/len(roots):.1%}")
print(f"mean root conf {np.mean([r[2] for r in res]):.3f}  mean qual conf {np.mean([r[3] for r in res]):.3f}")
