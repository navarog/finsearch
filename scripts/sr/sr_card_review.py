#!/usr/bin/env python3
"""
S&R Card Visual Review Orchestrator

Compares each S&R card's PDF reference against the webapp rendering.
Pre-extracts all screenshots, then spawns N concurrent claude subprocesses.
After reviews, syncs cards.xlsx to match the (now-corrected) cards.json.

Usage:
    python3 scripts/sr_card_review.py
    python3 scripts/sr_card_review.py --rerun-issues      # Only cards with prior issues
    python3 scripts/sr_card_review.py --cards 136,137     # Specific card IDs
    python3 scripts/sr_card_review.py --concurrency 3     # Override N workers (default 5)
    python3 scripts/sr_card_review.py --skip-screenshots  # Reuse existing images
"""

import argparse
import concurrent.futures
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

try:
    import fitz  # pymupdf
except ImportError:
    print("ERROR: pymupdf not installed. Run: pip install pymupdf")
    sys.exit(1)

try:
    import pandas as pd
except ImportError:
    print("ERROR: pandas not installed. Run: pip install pandas openpyxl")
    sys.exit(1)

# ── Paths ──────────────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_DIR = SCRIPT_DIR.parent

CARDS_JSON = PROJECT_DIR / "src" / "assets" / "cards.json"
SR_ID_MAP = SCRIPT_DIR / "sr_id_map.json"
INSTRUCTIONS_MD = SCRIPT_DIR / "card_review_instructions.md"
CARDS_XLSX = SCRIPT_DIR / "cards.xlsx"

MAIN_PDF = PROJECT_DIR / "new_materials" / "extracted" / "main_set" / "S&R_fish_cards_r6.pdf"
STARTER_PDF = PROJECT_DIR / "new_materials" / "extracted" / "starter_set" / "S&R_starter_fish_r5.pdf"

WEBAPP_URL = "http://localhost:3000"

# Claude CLI (try local mise install, then PATH)
CLAUDE_BIN = Path.home() / ".local/share/mise/installs/node/18.20.2/bin/claude"
if not CLAUDE_BIN.exists():
    CLAUDE_BIN = Path("claude")  # fallback to PATH

# gstack browse binary
BROWSE_BIN = PROJECT_DIR / ".claude/skills/gstack/browse/dist/browse"
if not BROWSE_BIN.exists():
    BROWSE_BIN = Path.home() / ".claude/skills/gstack/browse/dist/browse"

OUTPUT_DIR = SCRIPT_DIR / "review_output"
REPORT_MD = SCRIPT_DIR / "sr_review_report.md"
REPORT_JSON = SCRIPT_DIR / "sr_review_report.json"

N_WORKERS_DEFAULT = 5
SUBPROCESS_TIMEOUT = 360  # 6 minutes per card


# ── PDF page → card ID mapping ─────────────────────────────────────────────────

def normalize_name(s: str) -> str:
    """Normalize card name: uppercase, ASCII apostrophes, collapse whitespace."""
    # Normalize unicode (smart quotes → straight, ligatures, etc.)
    s = unicodedata.normalize("NFKD", s)
    s = s.replace("\u2019", "'").replace("\u2018", "'")
    s = s.replace("\u2013", "-").replace("\u2014", "-")
    s = s.replace("\xa0", " ")
    return " ".join(s.upper().split())


# Aliases for names in sr_id_map.json that have typos or differ from PDF text
# Maps normalized PDF text → card_id (overrides the id_map for those specific cases)
PDF_NAME_ALIASES = {
    # sr_id_map.json typos → correct matches
    "FILETALE CATSHARK": 152,
    "FILETAIL CATSHARK": 152,
    "STARRY PIPEFIISH": 196,
    "STARRY PIPEFISH": 196,
    "ZEBRE SEAHORSE": 210,
    "ZEBRA SEAHORSE": 210,
    "MEGAMOUTH": 173,
    "MEGAMOUTH SHARK": 173,
    "BONNEHEAD SHARK": 145,
    "BONNETHEAD": 145,
    "BONNETHEAD SHARK": 145,
    "BROADNOSE SEVENGILL": 146,
    "BROADNOSE SEVENGILL SHARK": 146,
    "DWARF LANTERNSHARK": 150,
    "DWARF_LANTERNSHARK": 150,
    "FURRY COFFINFISH": 157,
    "FURRY COFFFINFISH": 157,
    # PDF may have different spacing or hyphenation
    "INDIAN SAIL FIN SURGEONFISH": 165,
    "INDIAN SAIL-FIN SURGEONFISH": 165,
    "RED LIPPED BATFISH": 181,
    "RED-LIPPED BATFISH": 181,
    "ROSE VEILED FAIRY WRASSE": 185,
    "ROSE-VEILED FAIRY WRASSE": 185,
    "SHORTNOSE DEMON CATSHARK": 192,
    # Common alternate spellings
    "ATLANTIC BLACKTIP SHARK": 142,
    "BLACKTIP SHARK": 142,
    "GREY REEF SHARK": 163,
    "GRAY REEF SHARK": 163,
    "ILLUMINATED NETDEVIL": 215,
    "ILLUMINATE NETDEVIL": 215,
}


def build_name_lookup(id_map: dict) -> dict:
    """Build a normalized name → card_id lookup from the id_map + aliases."""
    lookup = {}
    for name, card_id in id_map.items():
        lookup[normalize_name(name)] = card_id
    # Apply aliases (override any conflicting id_map entries)
    lookup.update(PDF_NAME_ALIASES)
    return lookup


def build_page_card_map(pdf_path: Path, lookup: dict) -> dict:
    """
    Extract text from each PDF page and map to card IDs.
    Returns {page_index: card_id}.
    PDF page order is NOT the same as JSON ID order — text matching is essential.
    """
    doc = fitz.open(str(pdf_path))
    page_map = {}

    for i in range(doc.page_count):
        page = doc[i]
        text = page.get_text()
        raw_lines = [l.strip() for l in text.split("\n") if l.strip()]
        lines = [normalize_name(l) for l in raw_lines if len(l.strip()) > 2]

        found_id = None
        for j, line in enumerate(lines):
            # 1-line match
            if line in lookup:
                found_id = lookup[line]
                break
            # 2-line concat (e.g., "AMERICAN POCKET\nSHARK")
            if j + 1 < len(lines):
                two = line + " " + lines[j + 1]
                if two in lookup:
                    found_id = lookup[two]
                    break
            # 3-line concat
            if j + 2 < len(lines):
                three = line + " " + lines[j + 1] + " " + lines[j + 2]
                if three in lookup:
                    found_id = lookup[three]
                    break

        if found_id is not None:
            page_map[i] = found_id

    doc.close()
    return page_map


def build_complete_card_page_map(id_map: dict) -> dict:
    """
    Returns {card_id: (pdf_path, page_index)} for all mapped S&R cards.
    """
    lookup = build_name_lookup(id_map)
    result = {}

    for pdf_path in [MAIN_PDF, STARTER_PDF]:
        if not pdf_path.exists():
            print(f"  WARNING: PDF not found: {pdf_path}")
            continue
        page_map = build_page_card_map(pdf_path, lookup)
        for page_idx, card_id in page_map.items():
            if card_id not in result:  # first match wins
                result[card_id] = (pdf_path, page_idx)

    return result


# ── Image extraction ───────────────────────────────────────────────────────────

def extract_pdf_page(pdf_path: Path, page_idx: int, out_path: Path, scale: float = 3.0) -> None:
    """Render a PDF page to PNG using pymupdf at the given scale factor."""
    doc = fitz.open(str(pdf_path))
    page = doc[page_idx]
    mat = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=mat)
    pix.save(str(out_path))
    doc.close()


def extract_all_pdf_images(card_page_map: dict, output_dir: Path) -> dict:
    """
    Pre-render all card PDF pages to PNG. Returns {card_id: png_path}.
    Skips cards where the image already exists (use --skip-screenshots to bypass).
    """
    pdf_dir = output_dir / "pdf_pages"
    pdf_dir.mkdir(parents=True, exist_ok=True)

    card_to_image = {}
    for card_id in sorted(card_page_map.keys()):
        pdf_path, page_idx = card_page_map[card_id]
        out_path = pdf_dir / f"{card_id}_pdf.png"
        if not out_path.exists():
            try:
                extract_pdf_page(pdf_path, page_idx, out_path)
                print(f"  PDF extracted: card {card_id} (page {page_idx} of {pdf_path.name})")
            except Exception as e:
                print(f"  ERROR extracting PDF for card {card_id}: {e}")
                continue
        card_to_image[card_id] = out_path

    return card_to_image


def browse(*args) -> subprocess.CompletedProcess:
    """Run a gstack browse command, returning the CompletedProcess."""
    return subprocess.run(
        [str(BROWSE_BIN)] + list(args),
        capture_output=True, text=True, timeout=30
    )


def extract_webapp_screenshots(cards: list, output_dir: Path) -> dict:
    """
    Take webapp screenshots of each card sequentially using gstack browse.
    Returns {card_id: png_path}.
    """
    if not BROWSE_BIN.exists():
        print(f"  ERROR: gstack browse binary not found at {BROWSE_BIN}")
        return {}

    webapp_dir = output_dir / "webapp_screenshots"
    webapp_dir.mkdir(parents=True, exist_ok=True)

    card_to_image = {}

    # Set a consistent viewport
    browse("viewport", "700x900")

    for card in sorted(cards, key=lambda c: c["id"]):
        card_id = card["id"]
        out_path = webapp_dir / f"{card_id}_webapp.png"
        if out_path.exists():
            card_to_image[card_id] = out_path
            continue

        card_name = card["name"]
        try:
            # Navigate and search for this specific card
            browse("goto", WEBAPP_URL)
            browse("wait", "--load")

            # Clear the search field first, then type the card name
            browse("fill", "input[type='text']", card_name)
            time.sleep(0.5)  # Wait for React filter re-render

            # Screenshot the first card element
            result = browse("screenshot", ".card", str(out_path))
            if result.returncode != 0:
                print(f"  WARNING: screenshot failed for card {card_id} ({card_name}): {result.stderr[:100]}")
                # Try screenshotting the whole page as fallback
                browse("screenshot", str(out_path))
            else:
                print(f"  Screenshot: card {card_id} ({card_name})")

            card_to_image[card_id] = out_path

        except Exception as e:
            print(f"  ERROR taking screenshot for card {card_id} ({card_name}): {e}")

    return card_to_image


# ── Dev server check ──────────────────────────────────────────────────────────

def check_dev_server() -> bool:
    """Return True if the dev server is responding."""
    import urllib.request
    try:
        urllib.request.urlopen(WEBAPP_URL, timeout=5)
        return True
    except Exception:
        return False


# ── Subprocess invocation ─────────────────────────────────────────────────────

def run_card_review(card: dict, pdf_image: Path, webapp_image: Path, instructions: str) -> dict:
    """
    Spawn a claude subprocess to review one card.
    Returns the parsed JSON result dict.
    """
    card_id = card["id"]
    card_name = card["name"]

    prompt = f"""Review card ID {card_id}: "{card_name}"

PDF reference image (official design): {pdf_image}
Webapp screenshot (current rendering): {webapp_image}

Card data from cards.json:
{json.dumps(card, indent=2)}

Read both image files, compare them carefully against the checklist in your instructions, apply any data fixes to cards.json if needed, and output your JSON result.
"""

    try:
        result = subprocess.run(
            [
                str(CLAUDE_BIN),
                "-p", prompt,
                "--dangerously-skip-permissions",
                "--output-format", "json",
                "--no-session-persistence",
                "--system-prompt", instructions,
            ],
            capture_output=True,
            text=True,
            timeout=SUBPROCESS_TIMEOUT,
            cwd=str(PROJECT_DIR),
        )

        if result.returncode != 0:
            stderr_snippet = result.stderr[:400] if result.stderr else ""
            return {
                "card_id": card_id,
                "card_name": card_name,
                "status": "error",
                "issues": [{"severity": "high", "category": "other",
                             "description": f"Subprocess exited {result.returncode}: {stderr_snippet}"}],
                "fixes_applied": [],
                "css_issues": [],
            }

        # Parse the outer JSON envelope that --output-format json produces
        try:
            outer = json.loads(result.stdout)
            text_output = outer.get("result", outer.get("content", result.stdout))
        except json.JSONDecodeError:
            text_output = result.stdout

        # Extract the inner JSON code block from the text response
        json_match = re.search(r"```json\s*(\{[\s\S]*?\})\s*```", text_output)
        if not json_match:
            # Fallback: look for any top-level JSON object with card_id
            json_match = re.search(r'(\{[^{}]*"card_id"[^{}]*\})', text_output, re.DOTALL)

        if json_match:
            try:
                review = json.loads(json_match.group(1))
                # Ensure required fields exist
                review.setdefault("card_id", card_id)
                review.setdefault("card_name", card_name)
                review.setdefault("status", "ok")
                review.setdefault("issues", [])
                review.setdefault("fixes_applied", [])
                review.setdefault("css_issues", [])
                return review
            except json.JSONDecodeError as e:
                pass

        # Could not parse JSON from output
        return {
            "card_id": card_id,
            "card_name": card_name,
            "status": "parse_error",
            "issues": [{"severity": "low", "category": "other",
                         "description": f"Could not parse subprocess JSON output: {text_output[:300]}"}],
            "fixes_applied": [],
            "css_issues": [],
        }

    except subprocess.TimeoutExpired:
        return {
            "card_id": card_id,
            "card_name": card_name,
            "status": "timeout",
            "issues": [{"severity": "low", "category": "other",
                         "description": f"Subprocess timed out after {SUBPROCESS_TIMEOUT}s"}],
            "fixes_applied": [],
            "css_issues": [],
        }
    except Exception as e:
        return {
            "card_id": card_id,
            "card_name": card_name,
            "status": "error",
            "issues": [{"severity": "high", "category": "other",
                         "description": f"Exception: {e}"}],
            "fixes_applied": [],
            "css_issues": [],
        }


def run_reviews_parallel(
    cards_to_review: list,
    card_to_pdf: dict,
    card_to_webapp: dict,
    instructions: str,
    n_workers: int,
) -> list:
    """Run card reviews concurrently. Returns list of result dicts sorted by card_id."""
    results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=n_workers) as executor:
        future_to_card = {
            executor.submit(
                run_card_review,
                card,
                card_to_pdf[card["id"]],
                card_to_webapp[card["id"]],
                instructions,
            ): card
            for card in cards_to_review
            if card["id"] in card_to_pdf and card["id"] in card_to_webapp
        }

        # Report cards missing images
        missing = [c for c in cards_to_review
                   if c["id"] not in card_to_pdf or c["id"] not in card_to_webapp]
        for c in missing:
            missing_pdf = c["id"] not in card_to_pdf
            missing_wb = c["id"] not in card_to_webapp
            print(f"  SKIP card {c['id']} ({c['name']}): "
                  f"{'no PDF image ' if missing_pdf else ''}"
                  f"{'no webapp screenshot' if missing_wb else ''}")
            results.append({
                "card_id": c["id"],
                "card_name": c["name"],
                "status": "skip",
                "issues": [{"severity": "low", "category": "other",
                             "description": "Missing image(s) for review"}],
                "fixes_applied": [],
                "css_issues": [],
            })

        for future in concurrent.futures.as_completed(future_to_card):
            card = future_to_card[future]
            try:
                result = future.result()
            except Exception as e:
                result = {
                    "card_id": card["id"],
                    "card_name": card["name"],
                    "status": "exception",
                    "issues": [{"severity": "high", "category": "other",
                                 "description": str(e)}],
                    "fixes_applied": [],
                    "css_issues": [],
                }
            results.append(result)
            status = result.get("status", "?")
            n_issues = len(result.get("issues", [])) + len(result.get("css_issues", []))
            n_fixes = len(result.get("fixes_applied", []))
            print(f"  [{status:12s}] {result['card_id']:3d} {result.get('card_name', '?'):40s} "
                  f"{n_issues} issues  {n_fixes} fixes")

    return sorted(results, key=lambda r: r.get("card_id", 0))


# ── xlsx sync ─────────────────────────────────────────────────────────────────

def sync_xlsx_from_json() -> None:
    """
    Update cards.xlsx Master sheet to match the current cards.json.
    Only updates S&R cards (expansion='sr'); base cards are left unchanged.
    This propagates all JSON corrections (including pre-existing ones) into the xlsx.
    """
    if not CARDS_XLSX.exists():
        print("  WARNING: cards.xlsx not found, skipping sync")
        return

    print("\nSyncing cards.xlsx from cards.json...")

    with open(CARDS_JSON) as f:
        all_cards = json.load(f)

    sr_by_id = {c["id"]: c for c in all_cards if c.get("expansion") == "sr"}

    # Read xlsx preserving all sheets
    xl = pd.ExcelFile(str(CARDS_XLSX))
    dfs = {sheet: xl.parse(sheet) for sheet in xl.sheet_names}
    xl.close()

    if "Master" not in dfs:
        print("  WARNING: 'Master' sheet not found in cards.xlsx, skipping sync")
        return

    df = dfs["Master"]

    # Find the ID column (case-insensitive)
    id_col = None
    for col in df.columns:
        if str(col).lower() == "id":
            id_col = col
            break
    if id_col is None:
        print("  WARNING: 'id' column not found in xlsx, skipping sync")
        return

    updates = 0
    for idx, row in df.iterrows():
        try:
            row_id = int(row[id_col])
        except (ValueError, TypeError):
            continue

        if row_id not in sr_by_id:
            continue

        json_card = sr_by_id[row_id]

        for col in df.columns:
            col_lower = str(col).lower()
            # Match xlsx column to json field (case-insensitive)
            json_val = None
            if col in json_card:
                json_val = json_card[col]
            elif col_lower in json_card:
                json_val = json_card[col_lower]
            else:
                continue

            current_val = row[col]

            # Compare, handling None/NaN/null equivalences
            def val_eq(a, b):
                import math
                if a is None and b is None:
                    return True
                if a is None or b is None:
                    try:
                        if isinstance(a, float) and math.isnan(a) and b is None:
                            return True
                        if isinstance(b, float) and math.isnan(b) and a is None:
                            return True
                    except Exception:
                        pass
                    return False
                try:
                    if isinstance(a, float) and math.isnan(a):
                        return b is None
                    if isinstance(b, float) and math.isnan(b):
                        return a is None
                except Exception:
                    pass
                return str(a) == str(b)

            if not val_eq(current_val, json_val):
                df.at[idx, col] = json_val
                updates += 1

    dfs["Master"] = df

    # Write all sheets back
    with pd.ExcelWriter(str(CARDS_XLSX), engine="openpyxl") as writer:
        for sheet_name, sheet_df in dfs.items():
            sheet_df.to_excel(writer, sheet_name=sheet_name, index=False)

    print(f"  xlsx sync complete: {updates} cell(s) updated across {len(sr_by_id)} S&R cards")


# ── Report generation ─────────────────────────────────────────────────────────

def generate_report(results: list, report_path: Path) -> None:
    """Write a human-readable Markdown report."""
    total = len(results)
    ok = sum(1 for r in results if r.get("status") in ("ok", "data_fixed"))
    css_only = sum(1 for r in results if r.get("status") == "css_issues")
    mixed = sum(1 for r in results if r.get("status") == "mixed")
    errors = sum(1 for r in results if r.get("status") in
                 ("error", "timeout", "parse_error", "exception", "skip"))

    all_css = [(r["card_id"], r.get("card_name", "?"), issue)
               for r in results
               for issue in r.get("css_issues", [])]

    outstanding_data = [r for r in results if r.get("issues")]

    lines = [
        "# S&R Card Visual Review Report",
        "",
        f"**Cards reviewed:** {total}  ",
        f"**OK / data fixed:** {ok}  ",
        f"**CSS issues only:** {css_only}  ",
        f"**Mixed (data + CSS):** {mixed}  ",
        f"**Errors / skipped:** {errors}  ",
        "",
        "---",
        "",
    ]

    # CSS Issues section
    if all_css:
        lines += ["## CSS / Rendering Issues (Require Manual Fix in Card.scss / Card.jsx)", ""]
        seen = set()
        for card_id, card_name, issue in all_css:
            key = (issue.get("selector", ""), issue.get("suggested_value", ""))
            marker = " *(duplicate)*" if key in seen else ""
            seen.add(key)
            lines += [
                f"### Card {card_id}: {card_name}{marker}",
                f"- **Severity:** {issue.get('severity', '?')}",
                f"- **File:** `{issue.get('file', '?')}`",
                f"- **Selector:** `{issue.get('selector', '?')}`",
                f"- **Current:** `{issue.get('current_value', '?')}`",
                f"- **Suggested:** `{issue.get('suggested_value', '?')}`",
                f"- **Description:** {issue.get('description', '')}",
                "",
            ]
    else:
        lines += ["## CSS / Rendering Issues", "", "None reported.", ""]

    # Data fixes section
    data_fixes = [r for r in results if r.get("fixes_applied")]
    if data_fixes:
        lines += ["## Data Fixes Applied (cards.json)", ""]
        for r in data_fixes:
            lines.append(f"### Card {r['card_id']}: {r.get('card_name', '?')}")
            for fix in r["fixes_applied"]:
                lines.append(
                    f"- `{fix.get('field', '?')}`: "
                    f"`{fix.get('old_value', '?')}` → `{fix.get('new_value', '?')}`"
                )
            lines.append("")
    else:
        lines += ["## Data Fixes Applied", "", "None.", ""]

    # Outstanding data issues
    if outstanding_data:
        lines += ["## Outstanding Data Issues (Not Auto-Fixed)", ""]
        for r in outstanding_data:
            lines.append(f"### Card {r['card_id']}: {r.get('card_name', '?')} `[{r.get('status')}]`")
            for issue in r["issues"]:
                desc = issue.get("description", "")
                exp = issue.get("expected", "")
                act = issue.get("actual", "")
                lines.append(f"- **[{issue.get('severity', '?')}]** {desc}")
                if exp:
                    lines.append(f"  - Expected: `{exp}`")
                if act:
                    lines.append(f"  - Actual: `{act}`")
            lines.append("")
    else:
        lines += ["## Outstanding Data Issues", "", "None.", ""]

    # Errors
    error_results = [r for r in results
                     if r.get("status") in ("error", "timeout", "parse_error", "exception", "skip")]
    if error_results:
        lines += ["## Errors / Skipped", ""]
        for r in error_results:
            lines.append(f"- **{r['card_id']} {r.get('card_name', '?')}** "
                          f"[{r.get('status')}]: "
                          f"{r['issues'][0]['description'] if r.get('issues') else ''}")
        lines.append("")

    with open(report_path, "w") as f:
        f.write("\n".join(lines))

    print(f"\nReport written to: {report_path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="S&R Card Visual Review Orchestrator")
    parser.add_argument("--rerun-issues", action="store_true",
                        help="Only re-run cards with issues from the previous report")
    parser.add_argument("--cards", type=str, default="",
                        help="Comma-separated card IDs to review (e.g. 136,137,140)")
    parser.add_argument("--concurrency", type=int, default=N_WORKERS_DEFAULT,
                        help=f"Concurrent workers (default {N_WORKERS_DEFAULT})")
    parser.add_argument("--skip-screenshots", action="store_true",
                        help="Reuse existing images in review_output/; skip extraction")
    parser.add_argument("--skip-xlsx-sync", action="store_true",
                        help="Skip syncing cards.xlsx after reviews")
    args = parser.parse_args()

    print("=== S&R Card Visual Review ===")
    print(f"Project: {PROJECT_DIR}")

    # Load cards.json
    with open(CARDS_JSON) as f:
        all_cards = json.load(f)
    sr_cards = sorted([c for c in all_cards if c.get("expansion") == "sr"],
                      key=lambda c: c["id"])
    print(f"S&R cards in cards.json: {len(sr_cards)}")

    # Determine which cards to review
    if args.cards:
        target_ids = {int(x.strip()) for x in args.cards.split(",") if x.strip()}
        cards_to_review = [c for c in sr_cards if c["id"] in target_ids]
        print(f"Reviewing {len(cards_to_review)} specified cards")
    elif args.rerun_issues and REPORT_JSON.exists():
        with open(REPORT_JSON) as f:
            prev = json.load(f)
        issue_ids = {
            r["card_id"] for r in prev
            if r.get("status") not in ("ok", "data_fixed")
            or r.get("issues") or r.get("css_issues")
        }
        cards_to_review = [c for c in sr_cards if c["id"] in issue_ids]
        print(f"Re-running {len(cards_to_review)} cards with prior issues")
    else:
        cards_to_review = sr_cards
        print(f"Reviewing all {len(cards_to_review)} S&R cards")

    if not cards_to_review:
        print("No cards to review.")
        return

    # Check dev server
    print(f"\nChecking dev server at {WEBAPP_URL}...")
    if not check_dev_server():
        print(f"ERROR: Dev server not responding at {WEBAPP_URL}")
        print("Start it with: npm start")
        sys.exit(1)
    print("  Dev server OK")

    # Check claude binary
    if not Path(str(CLAUDE_BIN)).exists() and str(CLAUDE_BIN) != "claude":
        print(f"WARNING: claude binary not found at {CLAUDE_BIN}, will try PATH")

    # Load instructions
    with open(INSTRUCTIONS_MD) as f:
        instructions = f.read()

    # Setup output directory
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Image pre-extraction
    if args.skip_screenshots:
        print("\nLoading existing images...")
        card_to_pdf = {
            int(p.stem.split("_")[0]): p
            for p in (OUTPUT_DIR / "pdf_pages").glob("*_pdf.png")
        }
        card_to_webapp = {
            int(p.stem.split("_")[0]): p
            for p in (OUTPUT_DIR / "webapp_screenshots").glob("*_webapp.png")
        }
        print(f"  {len(card_to_pdf)} PDF images, {len(card_to_webapp)} webapp screenshots found")
    else:
        # Build PDF page map
        print("\nBuilding PDF page → card ID map...")
        with open(SR_ID_MAP) as f:
            id_map = json.load(f)
        card_page_map = build_complete_card_page_map(id_map)
        print(f"  Mapped {len(card_page_map)}/80 cards to PDF pages")
        unmapped = [c["id"] for c in sr_cards if c["id"] not in card_page_map]
        if unmapped:
            print(f"  Unmapped card IDs: {unmapped}")

        # Extract PDF page images
        print("\nExtracting PDF page images...")
        card_to_pdf = extract_all_pdf_images(card_page_map, OUTPUT_DIR)
        print(f"  {len(card_to_pdf)} PDF images ready")

        # Take webapp screenshots
        print("\nTaking webapp screenshots...")
        card_to_webapp = extract_webapp_screenshots(cards_to_review, OUTPUT_DIR)
        print(f"  {len(card_to_webapp)} webapp screenshots ready")

    # Run concurrent reviews
    print(f"\nRunning reviews with {args.concurrency} concurrent workers...")
    results = run_reviews_parallel(
        cards_to_review, card_to_pdf, card_to_webapp, instructions, args.concurrency
    )

    # Merge with previous results if rerunning a subset
    if (args.rerun_issues or args.cards) and REPORT_JSON.exists():
        with open(REPORT_JSON) as f:
            prev_results = json.load(f)
        prev_by_id = {r["card_id"]: r for r in prev_results}
        new_by_id = {r["card_id"]: r for r in results}
        prev_by_id.update(new_by_id)
        results = sorted(prev_by_id.values(), key=lambda r: r.get("card_id", 0))

    # Save machine-readable report
    with open(REPORT_JSON, "w") as f:
        json.dump(results, f, indent=2)

    # Generate Markdown report
    generate_report(results, REPORT_MD)

    # Sync xlsx (always, even on subset re-runs — json may have been modified by subprocesses)
    if not args.skip_xlsx_sync:
        sync_xlsx_from_json()

    # Summary
    print("\n=== SUMMARY ===")
    statuses = {}
    for r in results:
        s = r.get("status", "?")
        statuses[s] = statuses.get(s, 0) + 1
    for s, count in sorted(statuses.items()):
        print(f"  {s:15s}: {count}")

    outstanding = sum(1 for r in results
                      if r.get("status") not in ("ok", "data_fixed")
                      or r.get("issues") or r.get("css_issues"))
    print(f"\nCards with outstanding issues: {outstanding}")
    if outstanding == 0:
        print("All cards OK!")
    else:
        print("Re-run with --rerun-issues after fixing CSS/data issues.")


if __name__ == "__main__":
    main()
