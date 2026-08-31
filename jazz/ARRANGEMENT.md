# Jazz Big Band Arrangement — chart & production notes

## Source analysis
| | |
|---|---|
| Tempo | 172.27 BPM (beat 0.3483 s, bar 1.3932 s), grid starts at t = 0.0232 s |
| Key | **D major / B minor** |
| Form | strict **8-bar loop**, 7 times (56 bars, 80.4 s) |
| Loop harmony | `Bm · Bm · E · E · A · A · D · D` = **vi – II7 – V7 – Imaj7** in D |

That loop is already a jazz turnaround, which is why the reharmonisation lands so
naturally: `Bm7 → E7 → A7 → Dmaj7` is a textbook long ii-V chain.

## New form (98 bars, 2:23) — swing, medium-up
| Bars | Time | Section | Scoring |
|---|---|---|---|
| 1–4 | 0:00 | **Intro — solo piano** | rootless Maj9 / m11 / 13 voicings, singing top line |
| 5–12 | 0:06 | **Intro — combo** | double bass enters, then brushes; guitar comping |
| 9–12 | 0:11 | muted trumpet hints the tune | hands off to the singer |
| 13–28 | 0:17 | **Verse 1** | piano / bass / brushes / Freddie-Green guitar; tenor answers each 4-bar phrase |
| 29–36 | 0:39 | **Pre-chorus** | chromatic passing chords, tritone subs, brushes → ride, horns enter family by family, rising brass shout |
| 37–52 | 0:50 | **Chorus 1** | full big band: brass stabs, 5-part sax bed, call & response |
| 53–60 | 1:12 | **Verse 2** | back to the combo, freer walking bass, tenor obbligato |
| 61–68 | 1:24 | **Bridge** | hushed — voice, bass, piano, brushes only |
| 69–76 | 1:35 | **Tenor sax solo** | 8 bars, blue notes + chromatic enclosure; band builds underneath |
| 77–92 | 1:46 | **Final chorus** | shout chorus, high lead trumpet, new counter-melody, **stop-time** at bars 81 & 89 |
| 93–98 | 2:08 | **Ending** | ritardando from bar 96, full-band hits, final **D6/9** left to ring |

## Reharmonisation used
```
VERSE      | Bm9    | Bm11        | E13   | Bb7#11 | A13 | A13         | Dmaj9 | F#m7  B7#9 |
PRE-CHORUS | Bm9    | Bm11 C#m7b5 | E13   | E7#9 Bb13 | A13 | A13 Eb7#11 | Dmaj9 | Em9  A7alt |
CHORUS     | Bm9    | Bm11  E7#9  | E13   | E13  Bb13 | A13 | A13 Eb13   | Dmaj9 | D6/9 Em9 A13 |
SOLO       | Bm9    | Bm11 Bb7#11 | E13   | Bb7#11 | A13 | A13 Eb7#11  | Dmaj9 | Em9  A7alt |
ENDING     | Bm9 | E13 | A13 | Dmaj9 | Em9  A13 | D6/9 (fermata) |
```
* `Bb7#11` is the **tritone sub of E7** — it keeps the original's E as its #11, so it
  sits under the vocal without fighting it.
* `Eb7#11` / `Eb13` does the same job for A7.
* `F#m7 B7#9` turns the tonic bar into a **ii-V back into Bm**, so the loop keeps moving.

## Band
5 saxes (2 alto, 2 tenor, bari) · 2 trumpets + muted trumpet · 2 trombones ·
piano · double bass · guitar · drums (brush kit for the verses, jazz kit from the
pre-chorus on).

## How it was made
No music-generation model was reachable from this environment, so the track is
composed and performed by code:
1. `analyze.py` / `bassroots.py` — tempo, key, beat grid and the bass-root loop.
2. `separate.py` / `separate2.py` — vocal isolation with **REPET**: the backing repeats
   every 8 bars, the voice does not, so a loop-aligned spectral median gives the
   accompaniment, and the residual is the voice. Refined with REPET-SIM and HPSS.
   (No pretrained separator — model weight hosts are blocked here.)
3. `theory.py` / `engine.py` — chord grammar, rootless voicings, section (drop-2) voicings,
   walking-bass generator, comping-rhythm pools, swing grid (0.605), micro-timing humanisation.
4. `chart.py` / `arrange.py` — the arrangement above, 4,905 notes.
5. `render.py` — each part rendered separately through FluidSynth + FluidR3 GM.
6. `mix.py` — loudness-matched balance, big-band seating pan, one shared room reverb,
   section dynamics automation, vocal sidechain.

## Known limits
* The vocal stem is DSP-separated, not model-separated, so there is some residual
  "phasey" backing under the voice, mostly in the busiest bars.
* The band is a General MIDI soundfont, not sampled players. The MIDI file is included so
  you can re-render it with better instruments in Logic / Cubase / Kontakt.
