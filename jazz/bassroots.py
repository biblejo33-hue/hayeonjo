import numpy as np, librosa
SRC="/root/.claude/uploads/78895e4a-7b28-5945-8eae-1ed477f41d4b/125a20d2-LG_asitwas_remix.mp3"
sr=22050
y,_=librosa.load(SRC,sr=sr,mono=True)
import scipy.signal as ss
sos=ss.butter(6,[55/(sr/2),260/(sr/2)],'bandpass',output='sos'); yb=ss.sosfiltfilt(sos,y).astype('float32')
BPM=172.266; BEAT=60/BPM; BAR=4*BEAT
grid0=0.0232
NOTES=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
C=librosa.feature.chroma_cqt(y=yb,sr=sr,fmin=librosa.note_to_hz('C1'),n_octaves=4,bins_per_octave=36,tuning=0.0)
def root_at(t0,t1):
    f0,f1=librosa.time_to_frames([t0,t1],sr=sr)
    seg=C[:,max(f0,0):max(f1,1)]
    if seg.shape[1]==0: return None,0
    v=seg.mean(1); k=int(np.argmax(v)); return NOTES[k], float(v[k]/ (v.sum()+1e-9))
print("bar-by-bar bass root (2-beat resolution), grid offset %.3f" % grid0)
nb=int((80.4-grid0)/BAR)
for i in range(nb):
    t=grid0+i*BAR
    r1,c1=root_at(t,t+2*BEAT); r2,c2=root_at(t+2*BEAT,t+BAR)
    print(f"bar{i:>3} {t:6.2f}s  {r1:>2}({c1:.2f})  {r2:>2}({c2:.2f})")
