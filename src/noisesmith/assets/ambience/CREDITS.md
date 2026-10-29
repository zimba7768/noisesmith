# Credits: recorded wind, rain and thunder

The wind, rain and thunder recipes are made from real field recordings by **Joseph Sardin**,
published on **BigSoundBank** (https://bigsoundbank.com) under **CC0 1.0 (public domain)**.
BigSoundBank's license page offers them under CC0 1.0 Universal, the WTFPL and a public domain
dedication, for any use including commercial, with no credit required. Credit is appreciated
all the same, so: thank you, Joseph Sardin. Each recipe reshapes the recordings (blending,
speed, tone, level), and the results are free to use anywhere.

| Clip files here | BigSoundBank sound | Description |
|---|---|---|
| `wind_light_grass` | s0908 "Wind in Tall Grass" | Light wind moving through a field's tall grass |
| `wind_light_window` | s0147 "Whistling of the Wind #1" | Light wind hiss through an open window |
| `wind_strong_trees_1` | s1450 "Strong wind and trees #1" | Strong wind in trees during storm "Miguel", France |
| `wind_strong_trees_3` | s1452 "Strong wind and trees #3" | The same storm, a longer take |
| `wind_strong_leaves` | s0154 "Strong wind #4" | Strong outside wind with leaves and crackling |
| `wind_strong_inside` | s1714 "Wind from inside #1" | Storm wind heard from inside a house |
| `wind_whistle_chimney` | s0155 "Whistling of the Wind #2" | Wind whistling in a chimney |
| `rain_soft_umbrella` | s2679 "Rain Under an Umbrella" | Steady rain under an umbrella on a street |
| `rain_hard_concrete` | s1289 "Rain on concrete" | Large drops on a small concrete slab |
| `rain_heavy_terrace` | s1019 "Summer Rain on Terrace" | Large drops during a summer storm on a terrace |
| `thunder_2718`, `thunder_3115`, `thunder_3181`, `thunder_3113`, `thunder_3114`, `thunder_3116`, `thunder_3179`, `thunder_3180` | s2718 "Thunder #1", s3115 "#4", s3181 "#8", s3113 "#2", s3114 "#3", s3116 "#5", s3179 "#6", s3180 "#7" | Single thunder claps and rolls |

Each sound's page is `https://bigsoundbank.com/` followed by its title and number, for example
`https://bigsoundbank.com/strong-wind-and-trees-1-s1450.html`, and the original file is
`https://bigsoundbank.com/UPLOAD/mp3/<number>.mp3` (for example `1450.mp3`).

## What was done to the files

Mono, resampled to 48 kHz, saved as compact OGG (Vorbis). Wind and rain: the calmest stretch of up
to 40 seconds (fewest bumps and sudden events), leveled to -23 LUFS so different recordings mix
evenly. Thunder: the whole clip with silence trimmed, leveled to a peak of -1 dBFS. See
`scripts/prepare_ambience_assets.py`. Nothing else was changed.

## A note on provenance

Each BigSoundBank page and its license page declare these recordings CC0. If you are the rights
holder of any of them and want one removed, please open an issue.
