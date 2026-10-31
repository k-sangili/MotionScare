#!/usr/bin/env python3
"""Rebuild sounds/gentle/*.flac from CC0 recordings on Freesound, and write sounds/CREDITS.md.

The built files are committed, so you only need this to change a sound or re-tune loudness.
Needs curl and ffmpeg. Run from anywhere:  python3 tools/build_sounds.py

Each sound is trimmed, converted to 48 kHz stereo (what the Bluetooth sink runs at), stripped of
sub-bass a small speaker can't play, lightly compressed, then brought to TARGET_LUFS with a
limiter so nothing clips. Every clip fades in, so even the gentle mode has no sudden hits.
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "sounds" / "gentle"
TARGET_LUFS = -12.0  # loud and even; the old synth sounds ranged from -12 to -24
PEAK = 0.89  # limiter ceiling, about -1 dBFS

# percussive sounds: squash the transients so they can be as loud as the rest without clipping
PUNCH = "acompressor=threshold=-34dB:ratio=6:attack=1:release=120,"
# quiet recordings that get 20+ dB of gain: pull the room hiss down first
DENOISE = "afftdn=nr=10:nf=-45,"

# name, Freesound id, author, title, start s, end s (None = to the end), extra ffmpeg filters
SOUNDS = [
    ("heartbeat", 273150, "michorvath", "Heart Beating", 0.0, 7.0, PUNCH),
    ("footsteps", 459970, "florianreichelt", "Footsteps on hollow wood", 0.0, 9.0, DENOISE + PUNCH),
    ("knock", 256513, "HunteR4708", "Knock on the door", 0.0, 3.4, PUNCH),
    ("howl", 398430, "NaturesTemper", "Wolf howl", 0.0, None, ""),
    ("wind", 117611, "swiftoid", "wind_howl2_stereo.wav", 0.0, 8.0, ""),
    ("raven", 75162, "nigelcoop", "crow.wav", 0.0, None, ""),
    ("musicbox", 163644, "AudioBitsAndBytes", "Music Box Lullaby Clip", 0.0, 9.0,
     "asetrate=44100*0.88,aresample=44100,"),  # slowed and detuned: a music box winding down
    ("growl", 170454, "husky70", "Angry Beast.wav", 0.0, 6.5, ""),
    ("whisper_ghostly", 316797, "dimbark1", "Ghostly Whispers", 1.0, 8.0, DENOISE),
    ("whisper_creepy", 234044, "RaspberryTickle", "Creepy Whispering", 0.0, None, ""),
    ("whisper_voices", 193818, "geoneo0", "Four_Voices_Whispering_6_wEcho.wav", 2.5, 9.5, ""),
    ("thunder", 244053, "lennyboy", "Thunder.ogg", 3.0, 13.0, ""),
    ("moan", 249597, "staticpony1", "Ghosts moaning.wav", 0.0, 9.0, ""),
    ("creak", 168650, "0XMUSEX0", "DoorCreak.wav", 2.0, 7.0, DENOISE),
    ("owl", 465697, "Breviceps", "Owl Hoot", 0.0, None, DENOISE),
    ("breath", 204963, "titsher", "Scary_Breath.wav", 2.0, None, DENOISE),
]


def preview_url(sound_id, author):
    """Freesound's high-quality preview (OGG ~192 kbps). Originals need a logged-in API token."""
    page = subprocess.run(
        ["curl", "-sfL", "-A", "Mozilla/5.0", f"https://freesound.org/people/{author}/sounds/{sound_id}/"],
        capture_output=True, text=True, check=True).stdout
    if "creativecommons.org/publicdomain/zero/1.0" not in page:
        sys.exit(f"{sound_id} by {author} is no longer CC0; pick another sound")
    m = re.search(rf'https://cdn\.freesound\.org/previews/\d+/{sound_id}_\d+-lq\.ogg', page)
    if not m:
        sys.exit(f"no preview found for {sound_id}")
    return m.group(0).replace("-lq.ogg", "-hq.ogg")


def ffmpeg(*args):
    return subprocess.run(["ffmpeg", "-hide_banner", "-nostats", *args], capture_output=True, text=True, check=True)


def loudness(path, filters):
    """Integrated loudness (LUFS) of path after filters."""
    log = ffmpeg("-i", str(path), "-af", filters + "loudnorm=print_format=json", "-f", "null", "-").stderr
    return float(json.JSONDecoder().raw_decode(log[log.rindex("{"):])[0]["input_i"])


def build(name, sound_id, author, start, end, extra, tmp):
    raw = tmp / f"{sound_id}.ogg"
    subprocess.run(["curl", "-sfL", "-o", str(raw), preview_url(sound_id, author)], check=True)
    trim = ["-ss", str(start)] + (["-to", str(end)] if end else [])
    shape = (f"{extra}aresample=48000:resampler=soxr:precision=28,aformat=sample_rates=48000:channel_layouts=stereo,"
             "highpass=f=55,acompressor=threshold=-26dB:ratio=2.5:attack=15:release=250,")
    tmpclip = tmp / f"{name}.wav"
    ffmpeg("-y", *trim, "-i", str(raw), "-af", shape.rstrip(","), str(tmpclip))
    gain = TARGET_LUFS - loudness(tmpclip, "")
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                str(tmpclip)], capture_output=True, text=True, check=True).stdout)
    finish = (f"volume={gain:.2f}dB,alimiter=limit={PEAK}:attack=4:release=80:level=false,"
              f"afade=t=in:d=0.15,afade=t=out:st={max(dur - 0.8, 0):.2f}:d=0.8")
    out = OUT / f"{name}.flac"
    ffmpeg("-y", "-i", str(tmpclip), "-af", finish, "-sample_fmt", "s16", str(out))
    print(f"{name:<16} {dur:5.1f}s  gain {gain:+5.1f} dB  ->  {loudness(out, ''):6.1f} LUFS")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as t:
        for name, sound_id, author, _, start, end, extra in SOUNDS:
            build(name, sound_id, author, start, end, extra, Path(t))
    rows = "\n".join(
        f"| `{name}.flac` | [{title}](https://freesound.org/people/{author}/sounds/{sid}/) | {author} |"
        for name, sid, author, title, *_ in SOUNDS)
    (ROOT / "sounds" / "CREDITS.md").write_text(
        "# Sound credits\n\n"
        "Every sound here comes from [Freesound](https://freesound.org) under "
        "[CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) (public domain). Attribution "
        "isn't required, but thank you to these recordists.\n\n"
        "Built by `tools/build_sounds.py`, which trims each sound and adjusts its loudness.\n\n"
        "| File | Original | By |\n|---|---|---|\n" + rows + "\n")


if __name__ == "__main__":
    main()
