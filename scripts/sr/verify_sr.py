#!/usr/bin/env python3
"""
Post-integration verification for the S&R expansion.

Checks:
  - 80 new cards (IDs 136-215) exist in cards.json
  - Each has expansion="sr"
  - Each has a silhouette PNG and WebP
  - All icon names in ability text have a corresponding SVG file

Usage:
    python3 scripts/verify_sr.py
"""

import json
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
CARDS_JSON = os.path.join(PROJECT_DIR, 'src', 'assets', 'cards.json')
SILHOUETTES_DIR = os.path.join(PROJECT_DIR, 'src', 'assets', 'silhouettes')
ICONS_DIR = os.path.join(PROJECT_DIR, 'src', 'assets', 'icons')

EXPECTED_NEW_CARD_COUNT = 80
FIRST_NEW_ID = 136
LAST_NEW_ID = 215


def main():
    errors = []
    warnings = []

    # Load cards.json
    if not os.path.exists(CARDS_JSON):
        print(f"ERROR: {CARDS_JSON} not found")
        sys.exit(1)

    with open(CARDS_JSON) as f:
        cards = json.load(f)

    new_cards = [c for c in cards if c.get('id', 0) >= FIRST_NEW_ID]

    # Check count
    if len(new_cards) != EXPECTED_NEW_CARD_COUNT:
        errors.append(f"Expected {EXPECTED_NEW_CARD_COUNT} new cards, got {len(new_cards)}")
    else:
        print(f"✓ Card count: {len(new_cards)} new cards")

    # Check ID range
    ids = {c['id'] for c in new_cards}
    expected_ids = set(range(FIRST_NEW_ID, LAST_NEW_ID + 1))
    missing_ids = expected_ids - ids
    extra_ids = ids - expected_ids
    if missing_ids:
        errors.append(f"Missing card IDs: {sorted(missing_ids)}")
    if extra_ids:
        errors.append(f"Unexpected card IDs: {sorted(extra_ids)}")
    if not missing_ids and not extra_ids:
        print(f"✓ Card IDs: {FIRST_NEW_ID}–{LAST_NEW_ID} all present")

    # Parse icon names from ability text
    icon_re = re.compile(r'\[([^\]]+)\]')

    for c in new_cards:
        card_id = c.get('id')
        name = c.get('name', f'id={card_id}')

        # Check expansion field
        if c.get('expansion') != 'sr':
            errors.append(f"Card {card_id} ({name}): expansion={c.get('expansion')!r}, expected 'sr'")

        # Check silhouette PNG
        png_path = os.path.join(SILHOUETTES_DIR, f'{card_id}.png')
        if not os.path.exists(png_path):
            errors.append(f"Missing silhouette PNG: {card_id}.png ({name})")

        # Check silhouette WebP
        webp_path = os.path.join(SILHOUETTES_DIR, f'{card_id}.webp')
        if not os.path.exists(webp_path):
            errors.append(f"Missing silhouette WebP: {card_id}.webp ({name})")

        # Check ability icons
        ability = c.get('ability') or ''
        for icon in icon_re.findall(ability):
            icon_path = os.path.join(ICONS_DIR, f'{icon}.svg')
            if not os.path.exists(icon_path):
                errors.append(f"Missing icon SVG: {icon}.svg (used by card {card_id}: {name})")

    # Summary
    expansion_ok = sum(1 for c in new_cards if c.get('expansion') == 'sr')
    print(f"{'✓' if expansion_ok == len(new_cards) else '✗'} Expansion field: {expansion_ok}/{len(new_cards)} cards have expansion='sr'")

    png_count = sum(1 for c in new_cards if os.path.exists(os.path.join(SILHOUETTES_DIR, f'{c["id"]}.png')))
    print(f"{'✓' if png_count == len(new_cards) else '✗'} Silhouette PNGs: {png_count}/{len(new_cards)}")

    webp_count = sum(1 for c in new_cards if os.path.exists(os.path.join(SILHOUETTES_DIR, f'{c["id"]}.webp')))
    print(f"{'✓' if webp_count == len(new_cards) else '✗'} Silhouette WebPs: {webp_count}/{len(new_cards)}")

    # Find unique icons used across all new cards
    all_icons = set()
    for c in new_cards:
        for icon in icon_re.findall(c.get('ability') or ''):
            all_icons.add(icon)
    missing_icons = {i for i in all_icons if not os.path.exists(os.path.join(ICONS_DIR, f'{i}.svg'))}
    print(f"{'✓' if not missing_icons else '✗'} Icon SVGs: all {len(all_icons)} icons found" if not missing_icons
          else f"✗ Icon SVGs: {len(missing_icons)} missing: {sorted(missing_icons)}")

    if errors:
        print(f"\n{'='*50}")
        print(f"ERRORS ({len(errors)}):")
        for e in errors:
            print(f"  ✗ {e}")
        sys.exit(1)
    else:
        print(f"\n✓ All {len(new_cards)} new cards verified successfully.")


if __name__ == '__main__':
    main()
