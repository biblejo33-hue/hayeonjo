"""Vocal isolation without pretrained models.
Combines: (1) REPET loop-median background estimation (the track is a strict 4-bar loop),
          (2) REPET-SIM nn_filter refinement, (3) stereo centre/side cues.
"""
import numpy as np, librosa, soundfile as sf, os

SRC="/root/.claude/uploads/78895e4a-7b28-5945-8eae-1ed477f41d4b/125a20d2-LG_asitwas_remix.mp3"
OUT="/home/user/hayeonjo/jazz/stems"; os.makedirs(OUT, exist_ok=True)
SR=44100; N=4096; H=512
BPM=172.266; BEAT=60.0/BPM; BAR=4*BEAT; LOOP=4*BAR      # 4-bar loop = 5.5728 s

y,sr = librosa.load(SRC, sr=SR, mono=False)
if y.ndim==1: y=np.stack([y,y])
L,R = y[0], y[1]
mid=(L+R)/2; side=(L-R)/2
print("stereo width (side/mid rms): %.3f" % (np.sqrt((side**2).mean())/np.sqrt((mid**2).mean())))

def stft(x):  return librosa.stft(x, n_fft=N, hop_length=H)
def istft(X,n): return librosa.istft(X, hop_length=H, n_fft=N, length=n)

def repet_mask(S, loop_frames, margin_v=3.0, margin_i=2.0, power=2.0):
    """Background = median across loop repetitions; foreground = residual."""
    F,T = S.shape
    P = int(round(loop_frames))
    nrep = int(np.ceil(T/P))
    pad = nrep*P - T
    Sp = np.pad(S, ((0,0),(0,pad)), mode='edge').reshape(F, nrep, P)
    bg = np.median(Sp, axis=1)                       # F x P
    BG = np.tile(bg, (1,nrep))[:, :T]
    BG = np.minimum(S, BG)
    FG = S - BG
    mv = librosa.util.softmask(FG, margin_v*BG, power=power)
    mi = librosa.util.softmask(BG, margin_i*FG, power=power)
    return mv, mi

loop_frames = LOOP*sr/H
print("loop frames = %.2f" % loop_frames)

vox=[]; inst=[]
for ch in (L,R):
    S = stft(ch); M, P_ = np.abs(S), np.exp(1j*np.angle(S))
    mv, mi = repet_mask(M, loop_frames)
    Sv = M*mv
    # REPET-SIM refinement: remove anything that repeats elsewhere in the track
    filt = librosa.decompose.nn_filter(Sv, aggregate=np.median, metric='cosine',
                                       width=int(librosa.time_to_frames(1.0, sr=sr, hop_length=H)))
    filt = np.minimum(Sv, filt)
    mv2 = librosa.util.softmask(Sv-filt, 2.0*filt, power=2.0)
    Sv2 = Sv*mv2
    vox.append(istft(Sv2*P_, len(ch)))
    inst.append(istft(M*mi*P_, len(ch)))

V=np.stack(vox); I=np.stack(inst)
# vocals sit centre: keep the correlated part, drop hard-panned residue
vmid=(V[0]+V[1])/2
V = np.stack([vmid, vmid])
# tame sub-bass and hiss around the voice
V = librosa.effects.preemphasis(V, coef=0.0) if False else V
import scipy.signal as ss
b,a = ss.butter(4, 130/(sr/2), 'highpass'); V = ss.filtfilt(b,a,V,axis=1)
b,a = ss.butter(4, 12000/(sr/2), 'lowpass'); V = ss.filtfilt(b,a,V,axis=1)

peak=np.abs(V).max(); V = V/peak*0.89
sf.write(f"{OUT}/vocals.wav", V.T, sr, subtype='PCM_24')
sf.write(f"{OUT}/backing_removed.wav", I.T, sr, subtype='PCM_24')
print("wrote vocals.wav  rms=%.4f" % np.sqrt((V**2).mean()))

# where is the voice actually singing?
env = librosa.feature.rms(y=V.mean(0), frame_length=2048, hop_length=512)[0]
t = librosa.frames_to_time(np.arange(len(env)), sr=sr, hop_length=512)
thr = env.max()*0.10
on = env > thr
segs=[]; st=None
for i,v in enumerate(on):
    if v and st is None: st=t[i]
    if not v and st is not None:
        if t[i]-st > 0.28: segs.append((round(st,2), round(t[i],2)))
        st=None
if st is not None: segs.append((round(st,2), round(t[-1],2)))
print("vocal segments:")
for s,e in segs: print(f"   {s:6.2f} -> {e:6.2f}   ({e-s:.2f}s)")
