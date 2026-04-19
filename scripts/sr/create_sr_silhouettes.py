#!/usr/bin/env python3
"""
Generate S&R expansion silhouettes.
Extracts fish PSDs from zip archives, creates silhouettes matching existing app style.

Existing silhouette spec (measured from src/assets/silhouettes/1.png):
  Canvas:     750 x 491 px (RGBA)
  Gray value: ~#a0a0a0 (RGB 160, 160, 160)
  Style:      Gaussian blur, soft edges, transparent background

Usage:
    python3 scripts/create_sr_silhouettes.py --id-map scripts/sr_id_map.json
"""

import argparse
import io
import json
import os
import sys

import cv2
import numpy as np
import zipfile
from psd_tools import PSDImage

# -- Match existing silhouette dimensions (measured from silhouettes/1.png) --
TARGET_CANVAS_W = 750
TARGET_CANVAS_H = 491
TARGET_COLOR_RGB = (160, 160, 160)   # ~#a0a0a0

# Padding on each side so Gaussian blur can fade to transparent without hitting the canvas edge.
# Canvas is landscape (750x491) but many fish PSDs are portrait — height is the limiting axis.
# 25px padding ensures the blur kernel (41px, sigma=15) has room to fade on all sides.
BLUR_PAD = 25

# Gaussian blur params (to match soft edge style)
BLUR_KERNEL = (21, 21)
BLUR_SIGMA = 15

# PSD file names that are NOT fish illustrations (skip these)
SKIP_PATTERNS = {
    'FS_FishCardBackground1', 'BlueColumn', 'GreenColumn', 'PurpleColumn',
    'ifActivated', 'GameEnd', 'Card back_final version', 'AnyFishConsume',
    'Card back_final version-Starter',
}

def is_fish_psd(psd_path):
    name = os.path.basename(psd_path).replace('.psd', '')
    return not any(skip in name for skip in SKIP_PATTERNS)

def psd_bytes_to_rgba_numpy(psd_bytes):
    """Open PSD bytes, composite all visible layers, return RGBA numpy array."""
    psd = PSDImage.open(io.BytesIO(psd_bytes))
    composite = psd.composite()  # returns PIL Image in RGBA mode
    return np.array(composite.convert('RGBA'))

def make_silhouette(rgba_arr):
    """
    Convert an RGBA fish image to a gray silhouette on transparent background,
    matching the existing app style.
    """
    # Extract channels (PIL RGBA → numpy RGBA, cv2 uses BGRA)
    r, g, b, a = rgba_arr[:,:,0], rgba_arr[:,:,1], rgba_arr[:,:,2], rgba_arr[:,:,3]

    # Build gray-colored BGRA image preserving alpha from source
    gray_val = TARGET_COLOR_RGB
    bgra = np.zeros((rgba_arr.shape[0], rgba_arr.shape[1], 4), dtype=np.uint8)
    bgra[:,:,0] = gray_val[2]  # B
    bgra[:,:,1] = gray_val[1]  # G
    bgra[:,:,2] = gray_val[0]  # R
    bgra[:,:,3] = a             # preserve alpha

    # Scale to fit within canvas minus blur padding on all sides.
    # Fish PSDs can be portrait while the canvas is landscape — we must fit both axes,
    # not just the max dimension, otherwise portrait fish exceed canvas height and get clipped.
    h, w = bgra.shape[:2]
    max_fish_w = TARGET_CANVAS_W - 2 * BLUR_PAD
    max_fish_h = TARGET_CANVAS_H - 2 * BLUR_PAD
    scale = min(max_fish_w / w, max_fish_h / h)
    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))
    resized = cv2.resize(bgra, (new_w, new_h), interpolation=cv2.INTER_AREA)

    # Create canvas and center the fish (fits within bounds by construction — no clamping needed)
    canvas = np.zeros((TARGET_CANVAS_H, TARGET_CANVAS_W, 4), dtype=np.uint8)
    offset_x = (TARGET_CANVAS_W - new_w) // 2
    offset_y = (TARGET_CANVAS_H - new_h) // 2
    canvas[offset_y:offset_y+new_h, offset_x:offset_x+new_w] = resized

    # Apply Gaussian blur for soft edges (match existing silhouette style)
    rgb = canvas[:,:,:3].astype(np.float32)
    alpha = canvas[:,:,3:].astype(np.float32) / 255.0

    # Pre-multiplied alpha blur — use BORDER_CONSTANT so blur fades to transparent at canvas
    # edges rather than reflecting alpha back in (which causes a hard cutoff appearance)
    blurred_rgb = cv2.GaussianBlur(rgb * alpha, BLUR_KERNEL, BLUR_SIGMA,
                                    borderType=cv2.BORDER_CONSTANT)
    blurred_alpha = cv2.GaussianBlur(alpha, BLUR_KERNEL, BLUR_SIGMA,
                                      borderType=cv2.BORDER_CONSTANT)
    if blurred_alpha.ndim == 2:
        blurred_alpha = blurred_alpha[:,:, np.newaxis]

    # Un-multiply
    normalized = blurred_rgb / np.clip(blurred_alpha, 1e-5, 1.0)
    result = np.dstack([normalized, blurred_alpha * 255]).astype(np.uint8)

    return result


def process_zip(zip_path, id_map, out_dir, processed):
    """Process all fish PSDs in a zip file."""
    print(f"\nProcessing: {zip_path}")
    with zipfile.ZipFile(zip_path) as z:
        psd_entries = [n for n in z.namelist()
                       if n.endswith('.psd') and is_fish_psd(n)]

        for psd_path in sorted(psd_entries):
            fish_name = os.path.basename(psd_path).replace('.psd', '')

            if fish_name not in id_map:
                print(f"  SKIP (no ID mapping): {fish_name!r}")
                continue

            card_id = id_map[fish_name]
            out_path = os.path.join(out_dir, f'{card_id}.png')

            if os.path.exists(out_path):
                print(f"  SKIP (already exists): {fish_name} → {card_id}.png")
                processed.add(card_id)
                continue

            print(f"  Processing: {fish_name!r} → {card_id}.png ...", end=' ', flush=True)
            try:
                psd_bytes = z.read(psd_path)
                rgba_arr = psd_bytes_to_rgba_numpy(psd_bytes)
                silhouette = make_silhouette(rgba_arr)
                cv2.imwrite(out_path, silhouette)
                processed.add(card_id)
                print('done')
            except Exception as e:
                print(f'ERROR: {e}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--id-map', required=True,
                        help='JSON file mapping PSD fish name → card ID')
    parser.add_argument('--skip-existing', action='store_true', default=True,
                        help='Skip cards that already have a silhouette')
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.realpath(__file__))
    project_dir = os.path.dirname(script_dir)

    with open(args.id_map) as f:
        id_map = json.load(f)
    print(f"ID map loaded: {len(id_map)} entries")

    out_dir = os.path.join(project_dir, 'src', 'assets', 'silhouettes')
    os.makedirs(out_dir, exist_ok=True)

    processed = set()

    zip_paths = [
        os.path.join(project_dir, 'new_materials', 'S&R_fish_cards_r6 Folder.zip'),
        os.path.join(project_dir, 'new_materials', 'S&R_starter_fish_r5 Folder.zip'),
    ]

    for zip_path in zip_paths:
        if not os.path.exists(zip_path):
            print(f"WARNING: Zip not found: {zip_path}")
            continue
        process_zip(zip_path, id_map, out_dir, processed)

    expected_ids = set(id_map.values())
    missing = expected_ids - processed
    if missing:
        print(f"\nWARNING: Missing silhouettes for IDs: {sorted(missing)}")
    else:
        print(f"\nAll {len(processed)} silhouettes created successfully.")

    print(f"\nNext step: bash scripts/webp.sh")


if __name__ == '__main__':
    main()
