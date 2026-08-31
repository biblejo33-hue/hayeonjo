import numpy as np, librosa
SRC="/root/.claude/uploads/78895e4a-7b28-5945-8eae-1ed477f41d4b/125a20d2-LG_asitwas_remix.mp3"
sr=44100
y,_=librosa.load(SRC,sr=sr,mono=True)
BEAT=60/172.266; BAR=4*BEAT; LOOP=8*BAR
print("loop = %.4f s = %d samples"%(LOOP, LOOP*sr))
P=LOOP*sr
n=int(len(y)//P)
print("full loops:",n)
segs=[y[int(round(i*P)):int(round(i*P))+int(P)] for i in range(n)]
L=min(len(s) for s in segs); segs=[s[:L] for s in segs]
import itertools
print("pairwise normalised correlation of loop repetitions:")
for i,j in itertools.combinations(range(n),2):
    a,b=segs[i],segs[j]
    c=float(np.dot(a,b)/(np.linalg.norm(a)*np.linalg.norm(b)+1e-9))
    # also best correlation allowing +-2000 sample shift
    best=c; bl=0
    for sh in range(-1500,1501,50):
        aa=np.roll(a,sh)
        cc=float(np.dot(aa,b)/(np.linalg.norm(aa)*np.linalg.norm(b)+1e-9))
        if cc>best: best,bl=cc,sh
    print(f"  loop{i} vs loop{j}:  corr={c:+.3f}   best={best:+.3f} @shift {bl}")
