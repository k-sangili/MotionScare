#!/usr/bin/env bash
# Say something in a scary demon voice on the speaker.  Usage: say.sh "Rohan... I see you..." [save-as.wav]
set -euo pipefail
TXT="$1"; OUT="${2:-/tmp/say.wav}"
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
espeak-ng -v en-us+m7 -p 15 -s 105 -g 12 "$TXT" -w "$T/v1.wav"
espeak-ng -v en-us+whisper -p 30 -s 105 -g 12 "$TXT" -w "$T/v2.wav"
sox "$T/v1.wav" -r 44100 -c 2 "$T/deep.wav" pitch -700 tremolo 5 25 overdrive 6 gain -6
sox "$T/v2.wav" -r 44100 -c 2 "$T/whisp.wav" pitch -100 gain -8 pad 0.08
sox -m "$T/deep.wav" "$T/whisp.wav" "$T/mix.wav"
sox "$T/mix.wav" "$OUT" echo 0.8 0.75 120 0.4 reverb 85 norm -1
pw-play --target bluez_output.30_22_21_04_EC_80.1 "$OUT"
