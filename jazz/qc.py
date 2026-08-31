import numpy as np, librosa, soundfile as sf
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
SRC="/root/.claude/uploads/78895e4a-7b28-5945-8eae-1ed477f41d4b/125a20d2-LG_asitwas_remix.mp3"
sr=22050
o,_=librosa.load(SRC,sr=sr,mono=True)
v,_=librosa.load("stems/vocals.wav",sr=sr,mono=True)
n=min(len(o),len(v)); o,v=o[:n],v[:n]

BEAT=60/172.266; grid=0.0232
# leakage test: onset strength on the beat vs off the beat
def beatiness(x):
    oe=librosa.onset.onset_strength(y=x,sr=sr,hop_length=256)
    t=librosa.frames_to_time(np.arange(len(oe)),sr=sr,hop_length=256)
    ph=((t-grid)/BEAT)%1.0
    on=oe[(ph<0.10)|(ph>0.90)]; off=oe[(ph>0.35)&(ph<0.65)]
    return on.mean()/(off.mean()+1e-9)
print("beat-locked onset ratio  original=%.3f   vocal stem=%.3f  (lower = less drum leakage)"%(beatiness(o),beatiness(v)))
print("energy below 200Hz: original=%.1f%%  vocal=%.1f%%"%(
    100*np.sum(np.abs(np.fft.rfft(o))[:int(200*len(o)/sr)]**2)/np.sum(np.abs(np.fft.rfft(o))**2),
    100*np.sum(np.abs(np.fft.rfft(v))[:int(200*len(v)/sr)]**2)/np.sum(np.abs(np.fft.rfft(v))**2)))

fig,ax=plt.subplots(2,1,figsize=(16,7),sharex=True)
for a,x,t in zip(ax,[o,v],['ORIGINAL mix','ISOLATED VOCAL (REPET)']):
    D=librosa.amplitude_to_db(np.abs(librosa.stft(x,n_fft=2048,hop_length=256)),ref=np.max)
    librosa.display.specshow(D,sr=sr,hop_length=256,x_axis='time',y_axis='log',ax=a,cmap='magma',vmin=-70,vmax=0)
    a.set_title(t); a.set_ylim(80,10000)
plt.tight_layout(); plt.savefig('qc_spec.png',dpi=80)
print("saved qc_spec.png")
