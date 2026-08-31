import numpy as np, librosa, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
sr=22050; BEAT=60/172.266; grid=0.0232
files=[("original","/root/.claude/uploads/78895e4a-7b28-5945-8eae-1ed477f41d4b/125a20d2-LG_asitwas_remix.mp3"),
       ("vocals v1 (4-bar REPET)","stems/vocals.wav"),("vocals v2 (8-bar REPET+HPSS)","stems/vocals2.wav")]
fig,ax=plt.subplots(3,1,figsize=(17,10),sharex=True)
for a,(t,f) in zip(ax,files):
    y,_=librosa.load(f,sr=sr,mono=True)
    D=librosa.amplitude_to_db(np.abs(librosa.stft(y,n_fft=2048,hop_length=256)),ref=np.max)
    librosa.display.specshow(D,sr=sr,hop_length=256,x_axis='time',y_axis='log',ax=a,cmap='magma',vmin=-70,vmax=0)
    oe=librosa.onset.onset_strength(y=y,sr=sr,hop_length=256)
    tt=librosa.frames_to_time(np.arange(len(oe)),sr=sr,hop_length=256); ph=((tt-grid)/BEAT)%1.0
    on=oe[(ph<0.10)|(ph>0.90)].mean(); off=oe[(ph>0.35)&(ph<0.65)].mean()
    lo=100*np.sum(np.abs(np.fft.rfft(y))[:int(250*len(y)/sr)]**2)/np.sum(np.abs(np.fft.rfft(y))**2)
    a.set_title(f"{t}   beat-lock={on/off:.3f}  energy<250Hz={lo:.1f}%"); a.set_ylim(90,9000)
plt.tight_layout(); plt.savefig('qc_vox.png',dpi=68); print('ok')
