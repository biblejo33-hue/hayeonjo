import numpy as np, soundfile as sf, scipy.signal as ss
SR=44100
v1,_=sf.read('stems/vocals.wav',dtype='float32',always_2d=True); v1=v1.T
v2,_=sf.read('stems/vocals2.wav',dtype='float32',always_2d=True); v2=v2.T
n=min(v1.shape[1],v2.shape[1]); v1,v2=v1[:,:n],v2[:,:n]
hp=ss.butter(4,4200/(SR/2),'highpass',output='sos')       # air + consonants from v1
air=ss.sosfilt(hp,v1,axis=1)
v=v2+0.45*air
# de-ess a touch, then gate the gaps so REPET artefacts don't wash the jazz mix
b,a=ss.iirnotch(7200/(SR/2),2.0); v=v*0.85+ss.lfilter(b,a,v,axis=1)*0.25
env=np.abs(ss.sosfilt(ss.butter(2,18/(SR/2),'low',output='sos'),np.abs(v).max(0)))
thr=np.percentile(env,26)
g=np.clip((env-thr*0.65)/(thr*1.6+1e-9),0.0,1.0)*0.85+0.15
g=ss.sosfilt(ss.butter(2,9/(SR/2),'low',output='sos'),g)
v=v*g
v=v/np.abs(v).max()*0.9
sf.write('stems/vocals_final.wav',v.T,SR,subtype='PCM_24')
print('wrote stems/vocals_final.wav  gate floor %.2f  rms %.4f'%(g.min(),np.sqrt((v**2).mean())))
