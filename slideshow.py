#!/usr/bin/env python3
"""
Portable memorial device — photo slideshow with looping audio.

Cycles through images in ./photos, drawing directly to the Pi's SPI
touchscreen framebuffer (bypassing SDL/pygame's video system, which is
unreliable on headless Raspberry Pi OS Lite for small SPI displays), while
looping an audio recording from ./audio underneath via pygame.mixer.

Requires: python3-pygame, python3-pil (Pillow), python3-numpy
"""

import glob
import os
import re
import sys
import time
import random

import numpy as np
from PIL import Image
import pygame

# ---- Settings to tweak ----
PHOTO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "photos")
AUDIO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio")
SLIDE_SECONDS = 8          # how long each photo stays on screen
SHUFFLE_PHOTOS = False     # True = random order, False = alphabetical / file order
LOOP_AUDIO = True          # keep the recording playing on repeat
SCREEN_SIZE = (480, 320)   # matches the Hosyond panel's native resolution (width, height)
BACKGROUND_COLOR = (0, 0, 0)
# ------------------------------------------


def find_framebuffer_device():
    """Auto-detect which /dev/fbN is the SPI touchscreen (480x320), since the
    number can shift between boots depending on driver load order."""
    for path in sorted(glob.glob("/sys/class/graphics/fb*/virtual_size")):
        try:
            with open(path) as f:
                size = f.read().strip()
            if size == f"{SCREEN_SIZE[0]},{SCREEN_SIZE[1]}":
                fb_name = path.split("/")[-2]
                return f"/dev/{fb_name}"
        except OSError:
            continue
    # Fall back to fb0 if detection fails
    print("Could not auto-detect the SPI screen's framebuffer — defaulting to /dev/fb0", file=sys.stderr)
    return "/dev/fb0"


def _natural_sort_key(filename):
    """Split into text/number chunks so photo2 sorts before photo11
    (plain alphabetical sort would put photo10, photo11 before photo2)."""
    return [
        int(chunk) if chunk.isdigit() else chunk.lower()
        for chunk in re.split(r"(\d+)", filename)
    ]


def load_photo_paths():
    if not os.path.isdir(PHOTO_DIR):
        print(f"No photos folder found at {PHOTO_DIR}", file=sys.stderr)
        return []
    valid_ext = (".jpg", ".jpeg", ".png", ".bmp")
    filenames = [f for f in os.listdir(PHOTO_DIR) if f.lower().endswith(valid_ext)]
    filenames.sort(key=_natural_sort_key)

    # Always start on "photo1" (or "photo 1") if present, regardless of what
    # else sorts before it.
    def is_photo_one(name):
        stem = os.path.splitext(name)[0].lower().replace(" ", "").replace("_", "")
        return stem in ("photo1", "img1", "image1", "picture1")

    photo_one = next((f for f in filenames if is_photo_one(f)), None)
    if photo_one:
        filenames.remove(photo_one)
        filenames.insert(0, photo_one)

    paths = [os.path.join(PHOTO_DIR, f) for f in filenames]
    if SHUFFLE_PHOTOS:
        # Keep photo1 pinned as the very first slide; shuffle the rest.
        rest = paths[1:] if photo_one else paths
        random.shuffle(rest)
        paths = ([paths[0]] + rest) if photo_one else rest
    return paths


def load_audio_path():
    if not os.path.isdir(AUDIO_DIR):
        return None
    valid_ext = (".mp3", ".wav", ".ogg")
    for f in sorted(os.listdir(AUDIO_DIR)):
        if f.lower().endswith(valid_ext):
            return os.path.join(AUDIO_DIR, f)
    return None


def fit_image(path, target_size):
    """Load an image, scale to fit inside target_size preserving aspect ratio,
    centered on a black background. Returns an RGB PIL Image of target_size."""
    img = Image.open(path).convert("RGB")
    img_w, img_h = img.size
    target_w, target_h = target_size
    scale = min(target_w / img_w, target_h / img_h)
    new_size = (max(1, int(img_w * scale)), max(1, int(img_h * scale)))
    scaled = img.resize(new_size, Image.LANCZOS)
    canvas = Image.new("RGB", target_size, BACKGROUND_COLOR)
    x = (target_w - new_size[0]) // 2
    y = (target_h - new_size[1]) // 2
    canvas.paste(scaled, (x, y))
    return canvas


def image_to_rgb565_bytes(img):
    """Convert an RGB PIL Image to raw RGB565 little-endian bytes for
    writing straight to a Linux framebuffer device."""
    arr = np.array(img, dtype=np.uint16)
    r = (arr[:, :, 0] >> 3) & 0x1F
    g = (arr[:, :, 1] >> 2) & 0x3F
    b = (arr[:, :, 2] >> 3) & 0x1F
    rgb565 = (r << 11) | (g << 5) | b
    return rgb565.astype("<u2").tobytes()


def draw_to_framebuffer(fb_path, img):
    data = image_to_rgb565_bytes(img)
    with open(fb_path, "wb") as fb:
        fb.write(data)


def main():
    fb_path = find_framebuffer_device()
    print(f"Using framebuffer: {fb_path}", file=sys.stderr)

    photos = load_photo_paths()
    if not photos:
        print("No photos found — add images to the photos/ folder.", file=sys.stderr)

    # Audio via pygame's mixer only (no video/display subsystem needed)
    pygame.mixer.init()
    audio_path = load_audio_path()
    audio_active = False
    if audio_path:
        try:
            pygame.mixer.music.load(audio_path)
            pygame.mixer.music.play(loops=-1 if LOOP_AUDIO else 0)
            audio_active = True
        except pygame.error as e:
            print(f"Could not play audio ({audio_path}): {e}", file=sys.stderr)
            print("Continuing without audio — photos will still play.", file=sys.stderr)
    else:
        print("No audio file found — add a recording to the audio/ folder.", file=sys.stderr)

    index = 0
    last_switch = 0  # Immediate draw of the first photo

    while True:
        now = time.time()
        if photos and now - last_switch >= SLIDE_SECONDS:
            try:
                img = fit_image(photos[index], SCREEN_SIZE)
                draw_to_framebuffer(fb_path, img)
            except Exception as e:
                print(f"Could not display {photos[index]}: {e}", file=sys.stderr)
            index = (index + 1) % len(photos)
            last_switch = now

        # Keep audio looping even if pygame.mixer's built-in loop count runs out
        if audio_active and LOOP_AUDIO and not pygame.mixer.music.get_busy():
            pygame.mixer.music.play(loops=-1)

        time.sleep(0.5)


if __name__ == "__main__":
    main()