#!/usr/bin/env python3
"""Halloween door scare: play a random spooky sound when the PIR sensor sees motion.

Wiring (PIR sensor -> Pi header):
  VCC -> pin 2 (5V)   GND -> pin 6 (GND)   OUT -> pin 7 (GPIO4)

Modes (little kids come early, big kids later):
  gentle  sounds/gentle/ only, at reduced volume
  scary   sounds/gentle/ + sounds/scary/, at full volume
  auto    gentle until SCARE_SCARY_AFTER (default 19:30), then scary
Override on the night without restarting:  echo gentle > ~/scare/mode   (rm it to go back to auto)

Usage:
  scare.py              run forever, waiting for motion
  scare.py --test       play one random sound and exit
  scare.py --simulate   no sensor needed: press Enter to fake a trigger
"""
import argparse
import logging
import os
import random
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

SOUND_DIR = Path(os.environ.get("SCARE_SOUNDS", Path(__file__).parent / "sounds"))
PIR_PIN = int(os.environ.get("SCARE_PIN", "4"))
COOLDOWN = float(os.environ.get("SCARE_COOLDOWN", "8"))  # seconds between scares
BT_SPEAKER = os.environ.get("SCARE_BT_SPEAKER", "")  # MAC of Bluetooth speaker, empty = none
KEEPALIVE = float(os.environ.get("SCARE_KEEPALIVE", "240"))  # seconds; stops BT speaker auto-sleep
SCARY_AFTER = os.environ.get("SCARE_SCARY_AFTER", "19:30")  # HH:MM when auto mode turns scary
GENTLE_VOLUME = os.environ.get("SCARE_GENTLE_VOLUME", "0.6")
AMBIENT_VOLUME = os.environ.get("SCARE_AMBIENT_VOLUME", "0.25")  # background hush; "0" turns it off
AMBIENT_HOURS = os.environ.get("SCARE_AMBIENT_HOURS", "17:00-23:00")  # when the hush plays
COMBO_CHANCE = float(os.environ.get("SCARE_COMBO_CHANCE", "0.6"))  # chance a scare layers two sounds
MODE_FILE = Path(__file__).parent / "mode"
SOUND_EXTS = {".wav", ".mp3", ".ogg", ".flac", ".m4a"}

log = logging.getLogger("scare")


def current_mode(forced=None):
    mode = forced or (MODE_FILE.read_text().strip() if MODE_FILE.exists() else "auto")
    if mode not in {"gentle", "scary"}:
        mode = "scary" if datetime.now().strftime("%H:%M") >= SCARY_AFTER else "gentle"
    return mode


def load_sounds(mode):
    folders = ["gentle"] if mode == "gentle" else ["gentle", "scary"]
    sounds = sorted(
        p for f in folders if (SOUND_DIR / f).is_dir()
        for p in (SOUND_DIR / f).iterdir() if p.suffix.lower() in SOUND_EXTS
    )
    if not sounds:
        sys.exit(f"No {mode} sounds found in {SOUND_DIR}")
    return sounds


def pw_play_cmd(*extra):
    """pw-play aimed at the Bluetooth speaker if one is configured, else the default output."""
    cmd = ["pw-play", *extra]
    if BT_SPEAKER:
        cmd += ["--target", f"bluez_output.{BT_SPEAKER.replace(':', '_')}.1"]
    return cmd


def play_combo(sounds, volume="1.0"):
    """Play sounds overlapping: each one starts 0.5-2s after the previous, all mixed by PipeWire."""
    threads = []
    for i, path in enumerate(sounds):
        if i:
            time.sleep(random.uniform(0.5, 2.0))
        t = threading.Thread(target=play, args=(path, volume))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()


def play(path, volume="1.0"):
    """Play a sound file and block until it finishes."""
    if path.suffix.lower() in {".wav", ".flac", ".ogg", ".mp3"}:
        subprocess.run(pw_play_cmd("--volume", volume, str(path)), check=False)
    else:
        decoder = subprocess.Popen(
            ["ffmpeg", "-loglevel", "quiet", "-i", str(path), "-f", "wav", "-"],
            stdout=subprocess.PIPE,
        )
        subprocess.run(pw_play_cmd("--volume", volume, "-"), stdin=decoder.stdout, check=False)
        decoder.wait()


def reset_speaker_volume():
    """Bluetooth reconnects can drop the sink volume (often to 40%), so force it back to 100%."""
    if not BT_SPEAKER:
        return
    import json
    node = f"bluez_output.{BT_SPEAKER.replace(':', '_')}.1"
    try:
        objs = json.loads(subprocess.run(["pw-dump"], capture_output=True, text=True, timeout=10).stdout)
        sink = next(o["id"] for o in objs if o.get("info", {}).get("props", {}).get("node.name") == node)
        subprocess.run(["wpctl", "set-volume", str(sink), "1.0"], check=False)
    except (StopIteration, ValueError, subprocess.TimeoutExpired):
        log.warning("Bluetooth speaker sink %s not found", node)


def bt_connected(mac):
    info = subprocess.run(["bluetoothctl", "info", mac], capture_output=True, text=True).stdout
    return "Connected: yes" in info


def keep_speaker_alive(mac, silence):
    """Reconnect the Bluetooth speaker if it drops, and play near-silence so it never auto-sleeps."""
    failures = 0
    while True:
        if not bt_connected(mac):
            failures += 1
            log.info("Speaker %s not connected, reconnecting (attempt %d)...", mac, failures)
            if failures % 10 == 0:
                # Pi 3B+ Bluetooth chip can wedge ("adapter not powered"); a service restart revives it
                log.warning("Repeated failures, restarting Bluetooth service")
                subprocess.run(["sudo", "-n", "systemctl", "restart", "bluetooth"], check=False)
                time.sleep(5)
            try:
                subprocess.run(["bluetoothctl", "power", "on"], capture_output=True, timeout=10)
                subprocess.run(["bluetoothctl", "connect", mac], capture_output=True, timeout=30)
            except subprocess.TimeoutExpired:
                pass
        else:
            if failures:
                log.info("Speaker reconnected")
            failures = 0
            if not ambient_active():  # while the hush plays it already keeps the speaker awake
                subprocess.run(pw_play_cmd("--volume", "0.02", str(silence)), check=False)
        time.sleep(KEEPALIVE if bt_connected(mac) else 30)


def ambient_active():
    if float(AMBIENT_VOLUME) <= 0:
        return False
    start, end = AMBIENT_HOURS.split("-")
    return start <= datetime.now().strftime("%H:%M") < end


def loop_ambient(path):
    """Loop the background hush during AMBIENT_HOURS; scares play on top. Also keeps a BT speaker awake."""
    while True:
        if not ambient_active():
            time.sleep(30)
            continue
        started = time.monotonic()
        subprocess.run(pw_play_cmd("--volume", AMBIENT_VOLUME, str(path)), check=False)
        if time.monotonic() - started < 5:  # playback failed (e.g. speaker gone); don't spin
            time.sleep(10)


class Scarer:
    def __init__(self, forced_mode=None):
        self.forced_mode = forced_mode
        self.last = []
        self.last_time = 0.0

    def scare(self):
        if time.monotonic() - self.last_time < COOLDOWN:
            return
        mode = current_mode(self.forced_mode)
        sounds = load_sounds(mode)  # re-read each time so new files and mode changes apply live
        choices = [s for s in sounds if s not in self.last] or sounds
        count = 2 if len(choices) >= 2 and random.random() < COMBO_CHANCE else 1
        if mode == "scary" and any(s.parent.name == "scary" for s in sounds):
            # always end on a scary hit; optionally lead in with a gentle build-up sound
            hits = [s for s in choices if s.parent.name == "scary"] or [s for s in sounds if s.parent.name == "scary"]
            builds = [s for s in choices if s.parent.name != "scary"]
            picked = [random.choice(hits)]
            if count == 2 and builds:
                picked.insert(0, random.choice(builds))
        else:
            picked = random.sample(choices, count)
        self.last = picked
        reset_speaker_volume()
        log.info("BOO! [%s] playing %s", mode, " + ".join(p.name for p in picked))
        play_combo(picked, GENTLE_VOLUME if mode == "gentle" else "1.0")
        self.last_time = time.monotonic()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--test", action="store_true", help="play one sound and exit")
    parser.add_argument("--simulate", action="store_true", help="press Enter to fake motion")
    parser.add_argument("--mode", choices=["gentle", "scary"], help="force a mode instead of auto")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    scarer = Scarer(args.mode)
    mode = current_mode(args.mode)
    log.info("Mode now: %s (%d sounds). Auto turns scary at %s", mode, len(load_sounds(mode)), SCARY_AFTER)

    if BT_SPEAKER and not args.test:
        silence = Path(__file__).parent / "keepalive.wav"
        threading.Thread(target=keep_speaker_alive, args=(BT_SPEAKER, silence), daemon=True).start()
        log.info("Keeping Bluetooth speaker %s connected and awake", BT_SPEAKER)

    if args.test:
        scarer.scare()
        return

    ambient = Path(__file__).parent / "ambient.wav"
    if float(AMBIENT_VOLUME) > 0 and ambient.exists():
        threading.Thread(target=loop_ambient, args=(ambient,), daemon=True).start()
        log.info("Background hush %s at volume %s", AMBIENT_HOURS, AMBIENT_VOLUME)

    if args.simulate:
        log.info("Simulate mode: press Enter to trigger, Ctrl+C to quit")
        for _ in sys.stdin:
            scarer.scare()
        return

    from gpiozero import MotionSensor

    pir = MotionSensor(PIR_PIN)
    log.info("Waiting for PIR on GPIO%d to settle...", PIR_PIN)
    pir.wait_for_no_motion()
    log.info("Armed. Cooldown %.0fs.", COOLDOWN)
    while True:
        pir.wait_for_motion()
        scarer.scare()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
