#!/bin/bash
# Extract AI icon files from the extracted zip folder and convert to SVG using PyMuPDF.
# PyMuPDF properly converts CMYK colors to RGB and produces clean small SVGs without
# embedded PDF blobs (unlike Inkscape which produces ~920KB files for these AI assets).
# Name mapping: AI filename → final SVG name (removing hyphens)

set -e

ICONS_DIR="src/assets/icons"
EXTRACT_DIR="new_materials/extracted/main_set/Links"

# Ensure we're in the project root
cd "$(dirname "$0")/.."

echo "Converting AI icons to SVG using PyMuPDF..."

python3 << 'PYEOF'
import fitz, os, sys

ICONS_DIR = "src/assets/icons"
EXTRACT_DIR = "new_materials/extracted/main_set/Links"

name_map = {
    "AnyCoral": "AnyCoral",
    "BlueCoral": "BlueCoral",
    "GreenCoral": "GreenCoral",
    "PurpleCoral": "PurpleCoral",
    "Un-SchoolFish": "UnSchoolFish",
    "NoCost": "NoCost",
    "FreePlay-FishFromHand": "FreePlayFishFromHand",
}

ok = True
for ai_name, svg_name in name_map.items():
    ai_path = f"{EXTRACT_DIR}/{ai_name}.ai"
    svg_path = f"{ICONS_DIR}/{svg_name}.svg"
    if not os.path.exists(ai_path):
        print(f"WARNING: Not found: {ai_path}")
        ok = False
        continue
    doc = fitz.open(ai_path)
    svg = doc[0].get_svg_image()
    with open(svg_path, "w") as f:
        f.write(svg)
    size = os.path.getsize(svg_path)
    print(f"  ✓ {svg_name}.svg ({size:,} bytes)")

sys.exit(0 if ok else 1)
PYEOF

echo ""
echo "Done. New SVGs in ${ICONS_DIR}:"
ls "${ICONS_DIR}" | grep -E "AnyCoral|BlueCoral|GreenCoral|PurpleCoral|UnSchoolFish|NoCost|FreePlayFishFromHand"
