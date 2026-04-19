#!/usr/bin/env python3
"""
Extract S&R expansion card data from IDML and PDF sources.

Outputs scripts/sr_extracted.csv with all card fields for manual review + Excel import.

Usage:
    python3 scripts/extract_sr_cards.py
"""

import os
import sys
import re
import zipfile
import io
import csv
import xml.etree.ElementTree as ET
from collections import defaultdict

# -- Paths ------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
MAIN_ZIP = os.path.join(PROJECT_DIR, "new_materials", "S&R_fish_cards_r6 Folder.zip")
STARTER_ZIP = os.path.join(PROJECT_DIR, "new_materials", "S&R_starter_fish_r5 Folder.zip")
MAIN_IDML_PATH = "S&R_fish_cards_r6.idml"
OUTPUT_CSV = os.path.join(SCRIPT_DIR, "sr_extracted.csv")

# -- Icon name mappings (AI filename -> final icon name) -------------------
ICON_MAP = {
    "AnyCoral.ai": "AnyCoral",
    "BlueCoral.ai": "BlueCoral",
    "GreenCoral.ai": "GreenCoral",
    "PurpleCoral.ai": "PurpleCoral",
    "NoCost.ai": "NoCost",
    "Un-SchoolFish.ai": "UnSchoolFish",
    "FreePlay-FishFromHand.ai": "FreePlayFishFromHand",
    # Standard icons (for ability area detection)
    "Wave2.ai": "Wave",
    "All_Players.ai": "AllPlayers",
    "ConsumeFish.ai": "ConsumeFish",
    "SchoolFish.ai": "SchoolFish",
    "FishEgg.ai": "FishEgg",
    "YoungFish.ai": "YoungFish",
    "DrawCard.ai": "DrawCard",
    "Discard.ai": "Discard",
    "ArrowDown.ai": "ArrowDown",
    "SchoolFeederMove.ai": "SchoolFeederMove",
    "FishFromHand.ai": "FishFromHand",
    "TuckedCardSolo.ai": "TuckedCardSolo",
    "PlayFishBottomRow.ai": "PlayFishBottomRow",
    "FishHatch.ai": "FishHatch",
}

# Icons that appear in the NAME area (tag icons)
NAME_ICONS = {"Predator.ai", "Bioluminescent_r1.ai", "Camouflage.ai", "Electric.ai", "Venemous.ai", "Venomous.ai"}
# Tag field names (must match cards.json schema)
TAG_MAP = {
    "Predator.ai": "Predator",
    "Bioluminescent_r1.ai": "Bioluminescent",
    "Camouflage.ai": "Camouflage",
    "Electric.ai": "Electric",
    "Venemous.ai": "Venomous",
    "Venomous.ai": "Venomous",
}

# Icons that appear in the COST area
COST_ICONS = {"DrawCard.ai", "FishEgg.ai", "YoungFish.ai", "ConsumeFish.ai", "SchoolFish.ai"}
COST_MAP = {
    "DrawCard.ai": "cardCost",
    "FishEgg.ai": "eggCost",
    "YoungFish.ai": "youngCost",
    "ConsumeFish.ai": "consuming",
    "SchoolFish.ai": "schoolFishCost",
}

# Icons that appear in the ZONE area
ZONE_ICONS = {"Sun.ai", "Dusk.ai", "Night.ai"}
ZONE_MAP = {
    "Sun.ai": "sunlight",
    "Dusk.ai": "twilight",
    "Night.ai": "midnight",
}

# Background images that indicate zone column color
BG_ICONS = {
    "BlueColumn.psd", "GreenColumn.psd", "PurpleColumn.psd",
    "FS_FishCardBackground1.psd", "FS_FishCardBackground1.png",
    "GameEnd.psd", "ifActivated.psd",
    "Card back_final version.psd",
}

# Icons for midnight double-slot
BOTTOM_ROW_ICONS = {"PlayFishBottomRow.ai"}

# Coral icon names for the coral field
CORAL_ICONS = {"AnyCoral.ai", "BlueCoral.ai", "GreenCoral.ai", "PurpleCoral.ai"}
CORAL_MAP = {
    "AnyCoral.ai": "any",
    "BlueCoral.ai": "blue",
    "GreenCoral.ai": "green",
    "PurpleCoral.ai": "purple",
}


def read_idml(zip_path, idml_inner_path):
    """Open the outer zip and return an inner ZipFile for the IDML."""
    outer = zipfile.ZipFile(zip_path)
    idml_bytes = outer.read(idml_inner_path)
    return zipfile.ZipFile(io.BytesIO(idml_bytes))


def read_story(idml, story_id):
    """Read a story XML and return the concatenated text content."""
    try:
        story_xml = idml.read(f"Stories/Story_{story_id}.xml").decode("utf-8")
        root = ET.fromstring(story_xml)
        texts = []
        for c in root.iter():
            if c.tag.endswith("Content") and c.text:
                texts.append(c.text)
        return "".join(texts).strip()
    except Exception:
        return ""


def get_spread_data(idml, spread_name):
    """
    Parse one IDML spread and return extracted card data dict, or None if no card found.
    """
    content = idml.read(spread_name).decode("utf-8")
    root = ET.fromstring(content)

    # Collect story IDs from TextFrames
    story_ids = []
    for elem in root.iter():
        if "TextFrame" in elem.tag:
            s = elem.get("ParentStory")
            if s and s not in story_ids:
                story_ids.append(s)

    # Read all story texts
    stories = {}
    for sid in story_ids:
        text = read_story(idml, sid)
        if text:
            stories[sid] = text

    # Collect all image/link refs
    images = []
    for elem in root.iter():
        if elem.tag == "Link":
            uri = elem.get("LinkResourceURI", "")
            if uri:
                fname = uri.split("/")[-1].replace("%20", " ").replace("%26", "&")
                images.append(fname)

    if not stories:
        return None

    # -- Classify stories ---------------------------------------------------
    card_name = None
    latin = None
    description = None
    ability_type_raw = None
    ability_frags = []  # text fragments in the ability area
    numeric_vals = []   # all numeric stories

    for sid, text in stories.items():
        # Normalize non-breaking spaces and unicode quotes
        t = text.strip().replace("\xa0", " ").replace("\u2019", "'").replace("\u2018", "'")

        # Skip BOM-only strings
        if not t or t in ["\ufeff\ufeff", "\ufeff"]:
            continue

        # "cm" unit (standalone)
        if t == "cm":
            continue

        # Length (e.g. "145cm" or "1,500cm") — must check BEFORE card name
        if re.match(r"^[\d,]+cm$", t):
            ability_frags.append(t)
            continue

        # Pure numeric
        if re.match(r"^[\d,]+$", t):
            numeric_vals.append(t)
            continue

        # Ability type
        if t.lower() in ["when played:", "if activated:", "game end:"]:
            ability_type_raw = t
            continue
        # When Played combined with all players note
        if "when played:" in t.lower():
            ability_type_raw = "When Played:"
            ability_frags.append(t)
            continue

        # Latin name: binomial nomenclature (Genus species — both words lowercase-starting)
        if re.match(r"^[A-Z][a-z'\u2019\.]+(?: [a-z\.']+)+$", t) and len(t) < 60:
            latin = t
            continue

        # Description: longer sentence with sentence-like keywords
        if len(t) > 40 and re.match(r'^[A-Z\u201c\u2018"]', t) and not t.isupper():
            if any(kw in t.lower() for kw in ["the ", "its ", " in ", " is ", " has ", " it ", " a ", " an "]):
                description = t
                continue

        # Card name: title-case fish name — starts capital, has lowercase letters,
        # multiple words where EACH word starts with capital (or is short connector)
        # e.g. "Ninja Lanternshark", "Rose-veiled Fairy Wrasse", "American Pocket Shark"
        if (re.match(r"^[A-Z][a-zA-Z'\u2019\-]+(?: [A-Za-z'\u2019\-\.]+)*$", t)
                and 3 < len(t) < 70
                and any(c.islower() for c in t)):
            # Must not be an ability fragment keyword
            if t.lower() not in ["when played", "if activated", "game end", "cm", "only", "also"]:
                # Don't overwrite a good card name with a worse one
                if card_name is None:
                    card_name = t
                    continue

        # Ability text fragment (everything else)
        ability_frags.append(t)

    if not card_name and not latin:
        return None

    # -- Extract numeric values (points, length, wave score) ----------------
    points = None
    length = None
    wave_score = None  # additional wave score in ability

    # Sort numerics by value to help disambiguate
    nums = []
    for n in numeric_vals:
        v = int(n.replace(",", ""))
        nums.append(v)

    # Length from ability frags (e.g. "145cm")
    for frag in ability_frags[:]:
        m = re.match(r"^([\d,]+)cm$", frag)
        if m:
            length = int(m.group(1).replace(",", ""))
            ability_frags.remove(frag)
            break

    # Points: single number in numeric_vals that's <= 12
    # Wave score: another number if wave2 is in images
    wave2_count = sum(1 for img in images if img == "Wave2.ai")

    if wave2_count > 0 and len(nums) >= 2:
        # Two numbers: one is points, one is wave score
        nums_sorted = sorted(nums)
        # Points is typically the higher of the two (or the card's base score)
        # Wave score is typically from 2-6
        # We'll take the first numeric story as points, second as wave_score
        # but need to verify against typical ranges
        points = nums[0]
        wave_score = nums[1]
    elif len(nums) == 1:
        points = nums[0]
    elif len(nums) >= 2:
        # Multiple numbers but no wave: take the first small one as points
        points = min(nums)

    # -- Extract tags (from name area icons) --------------------------------
    tags = {}
    for img in images:
        if img in TAG_MAP:
            tag = TAG_MAP[img]
            tags[tag] = tags.get(tag, 0) + 1

    # -- Extract costs (from cost area icons) --------------------------------
    costs = {}
    for img in images:
        if img in COST_MAP:
            cost_field = COST_MAP[img]
            costs[cost_field] = costs.get(cost_field, 0) + 1

    # -- Extract zones -------------------------------------------------------
    zones = {}
    for img in images:
        if img in ZONE_MAP:
            zone = ZONE_MAP[img]
            if img == "Night.ai":
                # Check if PlayFishBottomRow appears (midnight=2)
                if any(i == "PlayFishBottomRow.ai" for i in images):
                    zones[zone] = 2
                else:
                    zones[zone] = 1
            elif zone not in zones:
                zones[zone] = 1

    # -- Extract coral type --------------------------------------------------
    coral_type = None
    coral_counts = defaultdict(int)
    for img in images:
        if img in CORAL_MAP:
            coral_counts[CORAL_MAP[img]] += 1

    if coral_counts:
        # Find the unique coral types used
        unique_corals = set(coral_counts.keys())
        if len(unique_corals) == 1:
            coral_type = list(unique_corals)[0]
        elif len(unique_corals) > 1:
            # Multiple coral types: "any" if AnyCoral + specific, else needs review
            if "any" in unique_corals:
                others = unique_corals - {"any"}
                if len(others) == 1:
                    coral_type = list(others)[0]  # The specific one + any backup
                else:
                    coral_type = "any"  # Multiple specific ones
            else:
                coral_type = "any"  # Mixed specific types

    # -- Build ability type string -------------------------------------------
    ability_type = None
    if ability_type_raw:
        at = ability_type_raw.lower().rstrip(":")
        ability_type = {
            "when played": "WhenPlayed",
            "if activated": "IfActivated",
            "game end": "GameEnd",
        }.get(at)

    # Clean ability frags (remove BOM and whitespace-only)
    ability_frags = [f.strip() for f in ability_frags if f.strip() and f.strip() not in ["\ufeff\ufeff", "\ufeff"]]

    # Determine needs_review: flag if we can't fully determine the ability text
    needs_review = False
    if not card_name:
        needs_review = True
    if not latin:
        needs_review = True
    if points is None:
        needs_review = True
    if length is None:
        needs_review = True

    return {
        "name_raw": card_name,
        "latin": latin,
        "points": points,
        "length": length,
        "description": description,
        "ability_type": ability_type,
        "ability_frags": ability_frags,
        "coral_type": coral_type,
        "coral_images": dict(coral_counts),
        "tags": tags,
        "costs": costs,
        "zones": zones,
        "images": [img for img in images if img not in BG_ICONS and img not in NAME_ICONS
                   and img not in COST_ICONS and img not in ZONE_ICONS],
        "wave_score": wave_score,
        "needs_review": needs_review,
    }


def extract_cards_from_zip(zip_path, idml_path):
    """Extract all card data from a zip file containing an IDML."""
    print(f"Processing: {zip_path}")
    idml = read_idml(zip_path, idml_path)

    cards = []
    for spread_name in sorted(idml.namelist()):
        if not spread_name.startswith("Spreads/"):
            continue
        data = get_spread_data(idml, spread_name)
        if data and (data["name_raw"] or data["latin"]):
            cards.append(data)

    return cards


def main():
    if not os.path.exists(MAIN_ZIP):
        print(f"ERROR: Main zip not found: {MAIN_ZIP}")
        sys.exit(1)

    # Extract main set
    main_cards = extract_cards_from_zip(MAIN_ZIP, MAIN_IDML_PATH)
    print(f"Main set: {len(main_cards)} cards extracted")

    # Extract starter set
    starter_cards = []
    if os.path.exists(STARTER_ZIP):
        try:
            # Find IDML in starter zip
            starter_outer = zipfile.ZipFile(STARTER_ZIP)
            idml_files = [n for n in starter_outer.namelist() if n.endswith(".idml")]
            if idml_files:
                starter_cards = extract_cards_from_zip(STARTER_ZIP, idml_files[0])
                print(f"Starter set: {len(starter_cards)} cards extracted")
        except Exception as e:
            print(f"WARNING: Could not extract starter set: {e}")

    all_cards = main_cards + starter_cards

    # Write CSV
    fieldnames = [
        "name_raw", "latin", "points", "length",
        "ability_type", "ability_frags_joined",
        "coral_type", "coral_images_str",
        "sunlight", "twilight", "midnight",
        "cardCost", "eggCost", "youngCost", "consuming", "schoolFishCost",
        "Bioluminescent", "Camouflage", "Electric", "Predator", "Venomous",
        "wave_score", "description",
        "needs_review",
    ]

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for card in all_cards:
            row = {
                "name_raw": card["name_raw"] or "",
                "latin": card["latin"] or "",
                "points": card["points"] or "",
                "length": card["length"] or "",
                "ability_type": card["ability_type"] or "",
                "ability_frags_joined": " | ".join(card["ability_frags"]),
                "coral_type": card["coral_type"] or "",
                "coral_images_str": str(card["coral_images"]),
                "sunlight": card["zones"].get("sunlight", 0),
                "twilight": card["zones"].get("twilight", 0),
                "midnight": card["zones"].get("midnight", 0),
                "cardCost": card["costs"].get("cardCost", 0),
                "eggCost": card["costs"].get("eggCost", 0),
                "youngCost": card["costs"].get("youngCost", 0),
                "consuming": card["costs"].get("consuming", 0),
                "schoolFishCost": card["costs"].get("schoolFishCost", 0),
                "Bioluminescent": card["tags"].get("Bioluminescent", 0),
                "Camouflage": card["tags"].get("Camouflage", 0),
                "Electric": card["tags"].get("Electric", 0),
                "Predator": card["tags"].get("Predator", 0),
                "Venomous": card["tags"].get("Venomous", 0),
                "wave_score": card["wave_score"] or "",
                "description": card["description"] or "",
                "needs_review": card["needs_review"],
            }
            writer.writerow(row)

    print(f"\nOutput written to: {OUTPUT_CSV}")
    needs_review_count = sum(1 for c in all_cards if c["needs_review"])
    print(f"Cards needing review: {needs_review_count} / {len(all_cards)}")

    # Summary
    print("\nCard summary:")
    for card in all_cards:
        flag = "REVIEW" if card["needs_review"] else "ok"
        print(f"  [{flag}] {card['name_raw'] or '???'!r:40s} pts={card['points']} len={card['length']} coral={card['coral_type']} type={card['ability_type']}")


if __name__ == "__main__":
    main()
