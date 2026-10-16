# EverLocket 🕊️

A portable, offline memorial device for elderly users built on Raspberry Pi Zero 2W.

## What It Does
- Displays a slideshow of family photos on a 3.5" screen
- Plays a loved one's voice recording automatically on boot
- Requires no WiFi, no setup, no technical knowledge to use
- Turns on and plays — just like opening a locket

## Hardware
- Raspberry Pi Zero 2W
- Hosyond 3.5" SPI touchscreen (480x320)
- USB audio adapter + speakers
- Custom 3D-printed enclosure
- USB power bank for portability

## Software
- Raspberry Pi OS Lite
- Python 3 with Pillow, NumPy, pygame
- Direct framebuffer rendering (no X11/desktop required)
- Auto-starts on boot via rc.local

## Built For
My grandmother, to keep my grandfather's memory alive. ❤️

## Setup
1. Add photos to `photos/` folder
2. Add audio file to `audio/` folder  
3. Device auto-plays on power on
