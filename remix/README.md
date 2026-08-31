# As It Was — Lo-fi / City Pop flip (practice)

Genre-change arrangement of a commercial recording, done as a personal
DSP/arranging exercise. **No audio is committed here** — only the scripts.
Drop your own copy at `work/original.mp3` and run the two steps below.

## Run

```
pip install numpy scipy soundfile librosa imageio-ffmpeg
python3 analyze.py     # HPSS split + tempo/beat grid  -> work/
python3 build.py       # arrangement + mix             -> out/
```

## What the original turned out to be

Measured, not assumed:

| | |
|---|---|
| tempo | **174.000 BPM** (441 tracked beats fit one rigid grid) |
| half-time feel | 87.00 BPM, first downbeat at 5.9717 s |
| tuning | +5 cents from A440 |
| key / loop | A major family — **Bm – E – A – D** (ii–V–I–IV), 4 bars |
| original groove | four-on-the-floor: kicks on 16th-steps 0/4/8/12 |

Grid checks that had to pass before anything was rendered:

* 100 % of the original's low-end hits land within 30 ms of the 16th grid,
  median deviation **+3.1 ms**.
* Chord-change energy clusters on steps 14–15–0–1–2 (straddling the bar
  line) and is strongly negative at step 8, so the bar phase is right and
  the half-bar is not a chord boundary.

## The arrangement

1. **Separation** — `librosa` HPSS, soft mask, `margin=(1, 3)`, per channel.
   Harmonic part (vocal, synth arp, bass) is kept; the percussive part is
   dropped to 8 %, just enough transient glue.
   *ML separation (demucs/torchaudio) was unavailable — every weight host is
   blocked by the network policy — so this is a pure-DSP split.*
2. **Tape varispeed** — resample by `2^(-1/12)`: one semitone down, tempo
   drags 174 → 164.2 BPM (**82.12** half-time). Pitch drop is the point, not
   a side effect; that is the slowed-and-warm lo-fi move.
3. **New kit** — synthesized from scratch: kick (pitch-swept sine + 47 Hz sub
   + click), snare (band-passed noise + 183/331 Hz body), hats, side-stick.
   Boom-bap pattern, kick on steps 0 and 10, backbeat on 4 and 12,
   **22 % swing** on the offbeat 8ths, ±3.5 ms and velocity humanisation.
4. **Dynamic gate** — the new drums follow the *original* drum track's RMS
   envelope, so the song keeps its own arrangement: the intro stays empty and
   the kit enters on the first downbeat (6.33 s). Drums cover 92 % of the track.
5. **Keys** — 4-op-ish FM Rhodes (carrier + self-modulation, decaying index,
   detuned second layer), voiced `E3–D#4` under the vocal so it never fights
   it. Chords are read from the audio per bar (bass-band chroma for the root,
   3rd-vs-b3rd energy for quality) then majority-voted across the 4-bar loop,
   which removes the relative-minor misreads a plain chroma match produces.
6. **Texture** — vinyl crackle (Poisson impulses, 1.4–7 kHz) over a pink bed,
   wow at 0.55 Hz and flutter at 6.3 Hz via a modulated fractional delay,
   FFT-convolution reverb from a decaying-noise IR, kick sidechain (−2.3 dB),
   M/S widening above 800 Hz, 11.5 kHz bed roll-off, tanh saturation.

Final balance: bed −18.9, drums −18.6, keys −24.0, vinyl −42.3, mix −13.6 dBFS,
peak 0.97.
