#!/usr/bin/env bash
# Render docs/sounds.png: a grid of the waveform of every sound in sounds/gentle.
# Needs ffmpeg built with drawtext (Homebrew's is). FONT overrides the label font.
set -euo pipefail
cd "$(dirname "$0")/.."
FONT="${FONT:-/System/Library/Fonts/Supplemental/Arial.ttf}"
COLS=4 W=440 H=150
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT

i=0
inputs=() layout=()
shopt -s nullglob
for f in sounds/gentle/*.{flac,wav,ogg,mp3}; do
  name=$(basename "${f%.*}")
  secs=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f")
  label=$(printf '%s   %.1fs' "$name" "$secs")
  ffmpeg -v error -y -i "$f" -filter_complex "
    [0:a]aformat=channel_layouts=mono,showwavespic=s=$((W-40))x96:colors=0xff8a2a:scale=lin[w];
    color=c=0x1b1714:s=${W}x${H}[bg];
    [bg][w]overlay=20:40,
    drawtext=fontfile=$FONT:text='$label':x=20:y=14:fontsize=18:fontcolor=0xf3e9dc" \
    -frames:v 1 "$T/$(printf %02d $i).png"
  inputs+=(-i "$T/$(printf %02d $i).png")
  layout+=("$(( i % COLS * W ))_$(( i / COLS * H ))")
  i=$((i+1))
done

ffmpeg -v error -y "${inputs[@]}" -filter_complex \
  "$(for ((n=0; n<i; n++)); do printf '[%d:v]' $n; done)xstack=inputs=$i:layout=$(IFS='|'; echo "${layout[*]}"):fill=0x1b1714" \
  -frames:v 1 docs/sounds.png
echo "wrote docs/sounds.png ($i sounds)"
