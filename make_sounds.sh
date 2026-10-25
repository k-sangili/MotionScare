#!/usr/bin/env bash
# Generate kid-friendly Halloween sounds with sox. Add your own to sounds/gentle any time.
#   gentle/ = spooky-fun, no sudden loud hits (safe for little kids)
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
sox "$T/up.wav" "$T/down.wav" ghost.wav fade t 0.5 2.8 0.9 gain -6 reverb 85 norm -3
# Owl: "hoo ... hoo-hoo"
sox -n "$T/hoo.wav" synth 0.45 sine 420-370 fade t 0.08 0.45 0.25
sox -n "$T/shorthoo.wav" synth 0.25 sine 420-380 fade t 0.05 0.25 0.15
sox -n -r 48000 "$T/rest.wav" trim 0 0.5
sox -n -r 48000 "$T/blip.wav" trim 0 0.12
sox "$T/hoo.wav" "$T/rest.wav" "$T/shorthoo.wav" "$T/blip.wav" "$T/hoo.wav" owl.wav gain -6 reverb 60 norm -3

# Skeleton xylophone tune: playful plucked notes
i=0
for f in 440 523 659 622 659 523 440; do
  sox -n -r 44100 -c 2 "$T/note$i.wav" synth 0.22 pluck $f fade 0 0.22 0.1 gain -6
  i=$((i+1))
done
sox -n -r 44100 -c 2 "$T/note$i.wav" synth 0.7 pluck 330 fade 0 0.7 0.5 gain -6
sox "$T"/note*.wav tune.wav reverb 30 norm -3
# Slide whistle "wheee-ooo"
sox -n -r 44100 -c 2 "$T/w1.wav" synth 0.6 sine 500-1400 tremolo 6 15
sox -n -r 44100 -c 2 "$T/w2.wav" synth 0.8 sine 1400-400 tremolo 6 15
sox "$T/w1.wav" "$T/w2.wav" whistle.wav fade 0.05 1.4 0.3 gain -6 norm -3
# Friendly voices (needs espeak-ng)
if command -v espeak-ng >/dev/null; then
  espeak-ng -v en-us+f3 -p 70 -s 150 "Happy Halloween! Trick or treat!" -w "$T/h.wav"
  sox "$T/h.wav" -r 44100 -c 2 happy.wav reverb 30 norm -3
  espeak-ng -v en-us+f4 -p 90 -s 220 -g 1 "hee hee hee hee, boo!" -w "$T/g.wav"
  sox "$T/g.wav" -r 44100 -c 2 giggle.wav pitch 200 echo 0.8 0.6 80 0.3 reverb 40 norm -3
fi

# Background hush: breathy "shhhh" that swells and fades like wind, loops every 30s
cd ../..
sox -n -r 48000 -c 2 ambient.wav synth 30 pinknoise band 2500 2000 tremolo 0.1 85 gain -6 norm -3 fade t 0.05 30 0.05

# Quiet low tone used to keep Bluetooth speakers from auto-sleeping
sox -n keepalive.wav synth 0.5 sine 40 gain -30

ls -l sounds/gentle
