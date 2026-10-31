#!/usr/bin/env bash
# Set up sounds on the Pi. The scare sounds themselves are real recordings committed in
# sounds/gentle/*.flac (see sounds/CREDITS.md; rebuilt by tools/build_sounds.py), so this only:
#   - removes the old sox-generated .wav sounds, which would otherwise play alongside them
#   - makes hum.wav, the inaudible hum that keeps the Bluetooth speaker out of standby
# Add your own sounds to sounds/gentle (or sounds/scary for jump scares) any time.
set -euo pipefail
cd "$(dirname "$0")"

for old in thunder moan creak ghost owl tune whistle happy giggle heartbeat footsteps knock howl \
           wind raven musicbox growl whisper_see whisper_closer whisper_behind; do
  rm -f "sounds/gentle/$old.wav"
done
rm -f ambient.wav keepalive.wav silence.wav  # retired background hush and keepalive tones

# 25 Hz hum streamed nonstop (quietly) so the Bluetooth speaker never goes to standby.
# 60s = exactly 1500 cycles, so it loops without a click.
sox -n -r 48000 -c 2 hum.wav synth 60 sine 25 gain -6

ls sounds/gentle
