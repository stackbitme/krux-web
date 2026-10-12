"""Runs Krux's official desktop simulator (pygame) on a sequence file, saving
the raw LCD surface (320x480 for the Amigo) for each `screenshot` command
instead of the framed/masked device image. Used as the reference for
pixel-by-pixel comparisons with the web simulator.

    cd <krux>/simulator && SDL_VIDEODRIVER=dummy ../.venv/bin/python \
        <this file> <outdir> --device maixpy_amigo --sd --sequence sequences/x.txt
"""
import os
import runpy
import sys

import pygame

OUT = sys.argv.pop(1)
os.makedirs(OUT, exist_ok=True)
_orig_save = pygame.image.save


def _save(surface, path, *args):
    from kruxsim.mocks import lcd

    name = os.path.basename(path)
    # strip the "-<size>.<locale>" suffix the simulator adds
    _orig_save(lcd.screen, os.path.join(OUT, name.split("-300")[0].split(".png")[0] + ".png"))


pygame.image.save = _save
sys.argv = ["simulator.py", "--no-screenshot-scale"] + sys.argv[1:]
runpy.run_path("simulator.py", run_name="__main__")
