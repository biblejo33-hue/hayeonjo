import sys, numpy as np, librosa, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
f=sys.argv[1]; sr=22050
y,_=librosa.load(f,sr=sr,mono=True)
D=librosa.amplitude_to_db(np.abs(librosa.stft(y,n_fft=2048,hop_length=512)),ref=np.max)
fig,ax=plt.subplots(2,1,figsize=(18,8),gridspec_kw={'height_ratios':[3,1]})
librosa.display.specshow(D,sr=sr,hop_length=512,x_axis='time',y_axis='log',ax=ax[0],cmap='magma',vmin=-72,vmax=0)
BAR=4*60/172.266
for name,b in [('intro',0),('verse1',12),('pre',28),('chorus1',36),('verse2',52),
               ('bridge',60),('SAX SOLO',68),('final',76),('end',92)]:
    ax[0].axvline(b*BAR,color='cyan',lw=1.0,alpha=.85); ax[0].text(b*BAR+.4,5200,name,color='cyan',fontsize=9)
ax[0].set_ylim(60,11000); ax[0].set_title(f)
r=librosa.feature.rms(y=y,frame_length=4096,hop_length=1024)[0]
t=librosa.frames_to_time(np.arange(len(r)),sr=sr,hop_length=1024)
ax[1].plot(t,20*np.log10(r+1e-6)); ax[1].set_ylim(-45,-5); ax[1].grid(alpha=.3); ax[1].set_ylabel('RMS dB')
for name,b in [('',0),('',12),('',28),('',36),('',52),('',60),('',68),('',76),('',92)]:
    ax[1].axvline(b*BAR,color='cyan',lw=1.0,alpha=.85)
ax[1].set_xlim(0,t[-1]); ax[0].set_xlim(0,t[-1])
plt.tight_layout(); plt.savefig(sys.argv[2],dpi=72); print("ok")
