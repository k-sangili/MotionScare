# MotionScare

A Raspberry Pi Halloween scare for the front door. A motion sensor spots trick-or-treaters walking up,
and a hidden Bluetooth speaker plays a spooky sound: footsteps on creaky boards, a heartbeat,
a wolf howling, ghostly whispers.

<p align="center">
  <img src="docs/wiring.svg" alt="Wiring: PIR sensor VCC to Pi pin 2 (5V), OUT to pin 7 (GPIO4), GND to pin 6; Bluetooth speaker paired with the Pi" width="720">
</p>

<p align="center">
  <img src="docs/sounds.png" alt="Waveforms of the 16 recorded sounds, from breath to wind, each one fading in rather than starting with a loud hit" width="720">
</p>

<sub>Waveforms of the actual sound files in <code>sounds/gentle/</code>, rendered by <code>tools/render_waveforms.sh</code>.</sub>

## Why I built this

Store-bought motion props play the same canned scream every time. That's boring by the third
group of kids, and a scream is the wrong sound for the littlest trick-or-treaters.

So I wanted something that:

- **Sounds real.** Real recordings of a heartbeat, footsteps, a wolf, ravens and whispers, made
  loud and even so they carry across a yard from a small Bluetooth speaker.
- **Is scary without making little kids cry.** Every sound fades in, and none of them is a scream
  or a sudden jump scare.
- **Gets a bit scarier as the night goes on.** Little kids come early and big kids come later, so it
  plays quieter until 7:30pm, then switches to full volume and any extra jump scares you've added.
- **Doesn't repeat itself.** It never plays the same sound twice in a row, and it often layers two
  sounds, such as a heartbeat under a whisper.
- **Uses cheap parts:** a Raspberry Pi, a PIR motion sensor, and any Bluetooth speaker, which can be
  hidden anywhere near the door.
- **Can be changed on the night without a laptop.** Switch modes with one file, drop in new sounds
  without restarting, and talk through the speaker in a demon voice with `say.sh`.

## What it does

1. The PIR sensor on GPIO4 detects motion.
2. `scare.py` picks one or two sounds and avoids whatever played last. In scary mode, if you've added
   anything to `sounds/scary/`, it always ends on one of those.
3. It plays them through PipeWire on the Bluetooth speaker. A second sound starts 0.5–2s after the
   first, and the two overlap.
4. It waits for a cooldown (8s by default) so one group at the door doesn't set it off over and over.

### The sounds

These are real recordings from [Freesound](https://freesound.org), all CC0 (public domain). Each
one's licence is checked when it's built. Sources are listed in [sounds/CREDITS.md](sounds/CREDITS.md).

| Sound | What it is |
|---|---|
| `heartbeat` | a heart beating, about 7s |
| `footsteps` | footsteps on hollow wooden boards |
| `knock` | knocking on the door |
| `howl` | a lone wolf howl |
| `wind` | howling wind, in stereo |
| `raven` | crows cawing |
| `musicbox` | a music-box lullaby, slowed and detuned so it sounds like it's winding down |
| `growl` | a low beast growl |
| `whisper_ghostly`, `whisper_creepy`, `whisper_voices` | three different whispered recordings |
| `thunder` | rolling thunder |
| `moan` | ghosts moaning |
| `creak` | a slow door creak |
| `owl` | an owl hooting |
| `breath` | heavy, creepy breathing |

`tools/build_sounds.py` builds them from the Freesound previews. For each one it:
- trims the best few seconds
- converts to 48 kHz stereo, the format the Bluetooth output runs at, so there's no resampling on the Pi
- cuts sub-bass a small speaker can't play anyway
- reduces hiss on the quiet recordings
- brings everything to a loud, even level (about -12 LUFS) with a limiter so nothing clips

The old synth sounds varied from -12 to -24 LUFS, which is why some of them were hard to hear.

### Modes

| Mode | Plays | Volume |
|---|---|---|
| `gentle` | `sounds/gentle/` | 0.8 |
| `scary` | `sounds/gentle/` + `sounds/scary/` | 1.0 |
| `auto` (default) | `gentle` until 7:30pm, then `scary` | — |

`sounds/scary/` is empty out of the box. Put your own jump scares there and they only play in scary
mode. To switch modes on the night without restarting anything:

```bash
echo gentle > ~/scare/mode   # or: echo scary > ~/scare/mode
rm ~/scare/mode              # back to auto
```

### Keeping the Bluetooth speaker awake

Bluetooth speakers go to standby after a few minutes with nothing playing, and waking one up
takes seconds. That's too late when someone is already at the door. PipeWire also suspends an idle
output after about 5 seconds, and waking it adds another 1–2 seconds of lag to every scare.

To prevent both, `scare.py` streams a 25 Hz hum nonstop at low volume. That's too low for a small
speaker to reproduce, so you don't hear it, but the speaker sees a signal and stays on. A background
thread also reconnects the speaker if it drops. If reconnecting keeps failing, it restarts the Pi's
Bluetooth service, because the Pi 3B+ Bluetooth chip occasionally gets stuck.

## Hardware

- Raspberry Pi running PipeWire (the default on Raspberry Pi OS Bookworm desktop). Built on a Pi 3B+.
- PIR motion sensor, HC-SR501 or similar, wired as shown above: **VCC → pin 2 (5V), OUT → pin 7
  (GPIO4), GND → pin 6**.
- Any Bluetooth speaker. A wired speaker on the headphone jack also works; leave
  `SCARE_BT_SPEAKER` unset.

On an HC-SR501, turn the **time-delay** knob fully anticlockwise (about 3s) and set the jumper to
**repeat trigger**. `scare.py` already has its own cooldown, and a long delay on the sensor just
makes it miss the next group.

## Setup on the Pi

```bash
sudo apt install sox python3-gpiozero   # add espeak-ng for say.sh, ffmpeg for .m4a sounds
git clone https://github.com/k-sangili/MotionScare ~/scare
cd ~/scare && ./make_sounds.sh          # makes hum.wav and clears out any old synth sounds
```

Pair the speaker once:

```bash
bluetoothctl
  scan on          # wait for your speaker's MAC to appear
  pair  AA:BB:CC:DD:EE:FF
  trust AA:BB:CC:DD:EE:FF
  connect AA:BB:CC:DD:EE:FF
```

Put your speaker's MAC in `scare.service` (`SCARE_BT_SPEAKER`), then install it as a user service
that starts at boot:

```bash
mkdir -p ~/.config/systemd/user
cp scare.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now scare
sudo loginctl enable-linger $USER   # start at boot without anyone logging in
journalctl --user -u scare -f       # watch it
```

A working log should look something like this:

```
18:02:11 Mode now: gentle (16 sounds). Auto turns scary at 19:30
18:02:11 Keeping Bluetooth speaker 30:22:21:04:EC:80 connected and awake
18:02:12 Waiting for PIR on GPIO4 to settle...
18:02:14 Armed. Cooldown 8s.
18:04:37 BOO! [gentle] playing heartbeat.wav + whisper_closer.wav
```

## Usage

```bash
python3 scare.py                     # run forever (what the service does)
python3 scare.py --test              # play one scare and exit
python3 scare.py --all --mode scary  # play every sound once, in order, to check them
python3 scare.py --simulate          # no sensor needed: press Enter to fake motion
./say.sh "Who goes there..."         # say something in a demon voice on the speaker
```

Stop the service (`systemctl --user stop scare`) before `--all` if you don't want a real trigger
playing over it.

**Adding your own sounds:** drop `.wav`, `.mp3`, `.ogg`, `.flac` or `.m4a` files into
`sounds/gentle/` or `sounds/scary/`. The folder is re-read on every trigger, so there's no need to
restart. Git ignores files you add yourself, so `git pull` won't touch them.

**Changing a built-in sound:** edit the `SOUNDS` table in `tools/build_sounds.py` (Freesound id,
start and end times), run `python3 tools/build_sounds.py`, then `tools/render_waveforms.sh` to
refresh the picture.

## Configuration

Set these as `Environment=` lines in `scare.service`:

| Variable | Default | |
|---|---|---|
| `SCARE_BT_SPEAKER` | *(none)* | Bluetooth speaker MAC. Unset = default audio output. |
| `SCARE_HUM_VOLUME` | `0.15` | Volume of the keep-awake hum. Raise it if the speaker still sleeps, lower it if you can hear it. |
| `SCARE_SCARY_AFTER` | `19:30` | When `auto` mode turns scary. |
| `SCARE_GENTLE_VOLUME` | `0.8` | Volume in gentle mode. |
| `SCARE_COOLDOWN` | `8` | Seconds between scares. |
| `SCARE_COMBO_CHANCE` | `0.6` | Chance a scare layers two sounds. |
| `SCARE_PIN` | `4` | PIR GPIO (BCM numbering). |
| `SCARE_KEEPALIVE` | `240` | Seconds between Bluetooth connection checks. |
| `SCARE_SOUNDS` | `./sounds` | Sound folder. |

## Project layout

```
scare.py                  motion loop, sound picking, Bluetooth keep-awake and reconnect
sounds/gentle/*.flac      the recorded scare sounds (credits in sounds/CREDITS.md)
make_sounds.sh            Pi setup: makes hum.wav, removes retired synth sounds
say.sh                    speak text in a demon voice on the speaker (sox + espeak-ng)
scare.service             systemd user service
tools/build_sounds.py     rebuilds sounds/gentle/*.flac from Freesound (needs curl + ffmpeg)
tools/render_waveforms.sh renders docs/sounds.png (needs ffmpeg)
docs/                     README images
```

## Troubleshooting

- **Lag between motion and sound.** Check the log for `hum.wav missing`. Run `make_sounds.sh`, which
  creates it. Then check the HC-SR501 knobs (see Hardware).
- **Speaker goes to sleep anyway.** Raise `SCARE_HUM_VOLUME` (try 0.25). Some speakers need a stronger
  signal before they count it as playing.
- **You can hear a hum.** Lower `SCARE_HUM_VOLUME`. Bigger speakers with real bass can reproduce 25 Hz.
- **No sound but the log says BOO.** Run `bluetoothctl info <MAC>` and look for `Connected: yes`.
  Run `wpctl status` to see whether the `bluez_output` sink exists.
