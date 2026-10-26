#!/usr/bin/env bash
# Generate mildly scary Halloween sounds with sox. Add your own to sounds/gentle any time.
#   gentle/ = creepy but no sudden loud hits (safe for little kids)
#   scary/  = (no longer generated) jump scares, only used in scary mode
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p sounds/gentle
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT

# ---------- gentle ----------
cd sounds/gentle

# Distant rumbling thunder
sox -n thunder.wav synth 4 brownnoise lowpass 300 fade q 0.05 4 2.5 tremolo 0.7 60 norm -1
# Ghostly moan
sox -n moan.wav synth 3.5 sine 260-170 sine 264-168 tremolo 4 50 gain -6 reverb 90 fade 0.6 3.5 1.2 norm -1
# Creaking door
sox -n creak.wav synth 2.5 sawtooth 140-55 tremolo 28 95 lowpass 1800 reverb 40 fade 0.1 2.5 0.6 norm -1
# Cartoon ghost "wooOOooo" (soft fade in, rises and falls)
sox -n "$T/up.wav" synth 1.2 sine 330-520 tremolo 5 30
sox -n "$T/down.wav" synth 1.6 sine 520-300 tremolo 5 30
sox "$T/up.wav" "$T/down.wav" ghost.wav fade t 0.5 2.8 0.9 gain -10 reverb 85 norm -3
# Owl: "hoo ... hoo-hoo"
sox -n "$T/hoo.wav" synth 0.45 sine 420-370 fade t 0.08 0.45 0.25
sox -n "$T/shorthoo.wav" synth 0.25 sine 420-380 fade t 0.05 0.25 0.15
sox -n -r 48000 "$T/rest.wav" trim 0 0.5
sox -n -r 48000 "$T/blip.wav" trim 0 0.12
sox "$T/hoo.wav" "$T/rest.wav" "$T/shorthoo.wav" "$T/blip.wav" "$T/hoo.wav" owl.wav gain -6 reverb 60 norm -3

# Retired goofy sounds (slide whistle, xylophone, giggle, "Happy Halloween"): remove old copies
rm -f whistle.wav tune.wav giggle.wav happy.wav

# Slow heartbeat: lub-dub x6
sox -n -r 44100 -c 2 "$T/lub.wav" synth 0.14 sine 62 overdrive 10 fade t 0.005 0.14 0.1 pad 0 0.12
sox -n -r 44100 -c 2 "$T/dub.wav" synth 0.11 sine 50 overdrive 10 fade t 0.005 0.11 0.08 pad 0 0.55
sox "$T/lub.wav" "$T/dub.wav" heartbeat.wav repeat 5 lowpass 300 gain -8 reverb 20 norm -1
# Footsteps creeping closer (each step louder)
i=0
for g in -10 -8 -6 -4 -2 0; do
  sox -n -r 44100 -c 2 "$T/step$i.wav" synth 0.18 brownnoise lowpass 250 fade t 0.005 0.18 0.15 gain $g pad 0 0.75
  i=$((i+1))
done
sox "$T"/step*.wav footsteps.wav gain -6 reverb 50 norm -1
# Three slow knocks on the door
sox -n -r 44100 -c 2 "$T/knock.wav" synth 0.07 brownnoise lowpass 600 overdrive 5 fade t 0.002 0.07 0.06 pad 0 0.9
sox "$T/knock.wav" knock.wav repeat 2 reverb 60 norm -1
# Distant wolf howl
sox -n -r 44100 -c 2 "$T/h1.wav" synth 0.8 sine 330-560
sox -n -r 44100 -c 2 "$T/h2.wav" synth 1.4 sine 560-520
sox -n -r 44100 -c 2 "$T/h3.wav" synth 1.0 sine 520-300
sox "$T/h1.wav" "$T/h2.wav" "$T/h3.wav" howl.wav tremolo 6 15 fade t 0.1 3.2 1.0 gain -8 reverb 90 echo 0.8 0.7 300 0.3 norm -2
# Howling wind gust
sox -n -r 44100 -c 2 wind.wav synth 6 pinknoise band 700 500 tremolo 0.25 80 fade t 0.2 6 2 reverb 80 norm -2
# Raven: caw... caw... caw
sox -n -r 44100 -c 2 "$T/caw.wav" synth 0.35 sawtooth 900-650 tremolo 45 60 band 1200 900 fade t 0.02 0.35 0.15 pad 0 0.3
sox "$T/caw.wav" raven.wav repeat 2 reverb 40 norm -3
# Creepy music box winding down: minor-key lullaby, each note a little slower
i=0
for n in 659:0.35 784:0.38 988:0.41 880:0.44 784:0.47 740:0.5 659:0.55 494:1.4; do
  f=${n%%:*}; d=${n##*:}
  sox -n -r 44100 -c 2 "$T/mbox$i.wav" synth "$d" pluck "$f" fade 0 "$d" 0.2 gain -6
  i=$((i+1))
done
sox "$T"/mbox*.wav musicbox.wav reverb 70 norm -3
# Low beast growl that swells in and fades (no sudden hit)
sox -n -r 44100 -c 2 growl.wav synth 3 brownnoise lowpass 220 tremolo 32 70 overdrive 12 fade t 0.2 3 1.2 gain -8 reverb 50 norm -2
# Whispers (needs espeak-ng)
if command -v espeak-ng >/dev/null; then
  espeak-ng -v en-us+whisper -p 40 -s 110 "I see you..." -w "$T/w1.wav"
  sox "$T/w1.wav" -r 44100 -c 2 whisper_see.wav reverb 80 echo 0.8 0.6 150 0.3 norm -3
  espeak-ng -v en-us+whisper -p 40 -s 100 "come closer..." -w "$T/w2.wav"
  sox "$T/w2.wav" -r 44100 -c 2 whisper_closer.wav reverb 80 echo 0.8 0.6 150 0.3 norm -3
  espeak-ng -v en-us+whisper -p 20 -s 95 "I'm right behind you..." -w "$T/w3.wav"
  sox "$T/w3.wav" -r 44100 -c 2 whisper_behind.wav pitch -300 reverb 80 echo 0.8 0.6 150 0.3 norm -3
fi

cd ../..
rm -f ambient.wav  # retired background hush

# 25 Hz hum streamed nonstop (quietly) so the Bluetooth speaker never goes to standby.
# 60s = exactly 1500 cycles, so it loops without a click.
sox -n -r 48000 -c 2 hum.wav synth 60 sine 25 gain -6
rm -f keepalive.wav silence.wav  # replaced by hum.wav

ls -l sounds/gentle
