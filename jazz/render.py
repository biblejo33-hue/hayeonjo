"""Render each MIDI track separately through FluidSynth, then mix as a live jazz band."""
import os, subprocess, numpy as np, soundfile as sf, pretty_midi as pm
import scipy.signal as ss

SF2="/usr/share/sounds/sf2/FluidR3_GM.sf2"
SR=44100
OUT="render"; os.makedirs(OUT, exist_ok=True)

src = pm.PrettyMIDI('jazz_arrangement.mid')
end = src.get_end_time()+6.0

def render_track(inst, name):
    m = pm.PrettyMIDI(initial_tempo=172.266)
    m.instruments.append(inst)
    mid = f"{OUT}/{name}.mid"; wav = f"{OUT}/{name}.wav"
    m.write(mid)
    subprocess.run(["fluidsynth","-ni","-F",wav,"-r",str(SR),"-g","0.45","-R","0","-C","1",
                    "--sample-rate",str(SR),SF2,mid],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    x,_ = sf.read(wav, dtype='float32', always_2d=True)
    x = x.T
    n = int(end*SR)
    if x.shape[1] < n: x = np.pad(x, ((0,0),(0,n-x.shape[1])))
    return x[:, :n]

tracks={}
for inst in src.instruments:
    tracks[inst.name] = render_track(inst, inst.name)
    print(f"  rendered {inst.name:<12} peak={np.abs(tracks[inst.name]).max():.3f}")
np.save(f"{OUT}/_tracks.npy", np.array({k:v for k,v in tracks.items()}, dtype=object), allow_pickle=True)
print("done", len(tracks), "tracks, %.1fs"%end)
