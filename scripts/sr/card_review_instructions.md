# S&R Card Visual Review Agent Instructions

You are auditing a single Finspan S&R expansion card for visual fidelity. You will be given:
- A **PDF reference image** (the official card design, high-resolution)
- A **webapp screenshot** (how the card currently renders at http://localhost:3000)
- The card's **JSON data** from cards.json

Your job: read both images, compare them, fix any data issues you can in cards.json, and report everything in a structured JSON result.

---

## Step 1: Read Both Images

Use the Read tool to view both image files. Look carefully at both before drawing conclusions.

---

## Step 2: Visual Comparison Checklist

Compare these elements between the PDF reference and the webapp screenshot:

### Card Identity
- **Card title** (top center): correct text, readable, not truncated
- **Latin name** (below title): correct scientific name, readable
- **Group**: main cards have no corner markers; starter cards have gray diagonal triangles in top-left and bottom-right corners

### Left Side Elements
- **Cost box** (top-left pill): icons match the card's cost fields. Icon→field mapping:
  - `DrawCard` = cardCost, `FishEgg` = eggCost, `YoungFish` = youngCost
  - `ConsumeFish` = consuming, `SchoolFish` = schoolFishCost
  - Count of each icon must match the numeric field value (e.g., cardCost=2 → 2 DrawCard icons)
- **Zone box** (left-middle pill): icons match sunlight/twilight/midnight booleans
  - sunlight=1 → Sun icon, twilight=1 → Dusk icon, midnight=1 → Night icon
  - midnight=2 → PlayFishBottomRow icon (only 2 base cards; no S&R cards use this)
  - Number of icons in pill must match the number of active zones
- **Points** (bottom-left, large number): matches the `points` field value + Wave icon next to it
- **Length** (below points): matches `length` field in cm + correct size icon:
  - < 50cm → FishLengthSmall, 50–149cm → FishLengthMedium, ≥ 150cm → FishLengthLarge

### Right Side Elements
- **Ability label** (bold text at top of ability box):
  - WhenPlayed → "WHEN PLAYED:"
  - IfActivated → "IF ACTIVATED:"
  - GameEnd → "GAME END:"
- **Ability background**: IfActivated and GameEnd cards have a brown/textured background image in the ability area. WhenPlayed cards have no background wash.
- **Ability icons**: every `[IconName]` in the `ability` field must appear as an icon in the webapp. Missing or extra icons are bugs.
- **Ability text**: non-icon text segments (e.g., "in this dive site:", "only", "(all players)", "on each", "if ... in ALL your dive sites") must be present
- **Wave point abilities**: format `"N [Wave] if ..."` renders as a large bold number + Wave icon. The number precedes the Wave icon in the display.
- **"also, if" split**: IfActivated cards with "also, if" in their ability field render TWO separate ability boxes — the first shows the cost icons, the second shows the conditional effect. Verify both boxes are present.
- **Description text** (bottom-right, small italic): should match the `description` field. If the PDF shows a description but the webapp shows none (or a different one), flag it.

### Tag Icons (in title area)
- Tags `Predator`, `Bioluminescent`, `Camouflage`, `Electric`, `Venomous` show as small icons immediately after the first line of the card title.
- Count must match the numeric value in the field (usually 0 or 1; some cards may have 2).

### Fish Silhouette
- A gray fish silhouette should appear in the center-right area of the card (overlapping the ability zone)
- It should be visible and roughly match the fish depicted in the PDF
- Extremely mispositioned (completely off-card, totally hidden behind another element) is a bug

### Expansion Logo
- S&R cards should show the SRLogo.svg in the bottom-right corner
- NOTE: The expansion logo size is a KNOWN GLOBAL CSS ISSUE — do NOT report it as a per-card issue. It may appear large compared to the PDF; this will be fixed globally.

### Background Color (band)
- `band` field value determines the card background: null→base (dark blue/gray), blue→blue, green→green, purple→purple
- Cards with a `coral` type typically (but not always) have a matching `band`
- If the card background is clearly the wrong color compared to the PDF, report it as a data issue (wrong `band` value)

---

## Step 3: Issues You Can Fix (cards.json only)

You MAY edit `/Users/cief/projects/finsearch/src/assets/cards.json` to fix issues in this specific card's entry. Only fix what you are confident about from the PDF reference.

**Fixable fields:**
- `ability`: wrong icon names, missing icons, extra icons, wrong text segments
- `abilityType`: wrong type (WhenPlayed / IfActivated / GameEnd)
- `band`: wrong background color (null / "blue" / "green" / "purple")
- `description`: wrong or missing description text
- `points`: wrong numeric value
- `length`: wrong numeric value in cm
- `cardCost`, `eggCost`, `youngCost`, `consuming`, `schoolFishCost`: wrong numeric values
- `sunlight`, `twilight`, `midnight`: wrong zone presence (0 or 1)
- `Bioluminescent`, `Camouflage`, `Electric`, `Predator`, `Venomous`: wrong tag values (0 or 1)
- `coral`: wrong coral type (null / "blue" / "green" / "purple" / "any")

**How to edit cards.json atomically:**
1. Read the entire `/Users/cief/projects/finsearch/src/assets/cards.json` file
2. Parse the JSON array
3. Find the entry where `"id"` equals this card's ID
4. Apply ONLY the specific field changes needed
5. Write the complete updated array back to the file
6. Preserve ALL other cards unchanged — do not reformat or reorder

**Icon names valid in `ability` field text** (these are the SVG filenames without `.svg`):
```
AllPlayers, AnyCoral, ArrowDown, BlueCoral, ConsumeFish, ConsumeFish1, ConsumeFish2,
ConsumeFish3, Discard, DrawCard, Estuary, FishEgg, FishFromHand, FishHatch,
FishLengthLarge, FishLengthMedium, FishLengthSmall, FlipperBlue, FlipperGreen,
FlipperPurple, FreePlayFishFromHand, GreenCoral, NoCost, PlayFishBottomRow,
PurpleCoral, SchoolFeederMove, SchoolFish, Sun, TuckedCardSolo, UnSchoolFish,
Wave, YoungFish
```

**Common ability text patterns** (reference for correct formatting):
- WhenPlayed simple: `"[DrawCard]"` or `"[SchoolFeederMove][SchoolFeederMove]"`
- Coral placement: `"[BlueCoral]"` or `"[AnyCoral]"`
- Coral + fish from hand (each player): `"[BlueCoral][FishFromHand]"` — NOT `[SchoolFeederMove]`
- All-players coral (2 icons): `"(all players) [PurpleCoral][PurpleCoral] on each [AllPlayers]"`
- IfActivated basic: `"[Discard] also, if [BlueCoral][BlueCoral][BlueCoral] in this dive site: [DrawCard]"`
- GameEnd wave: `"5 [Wave] if [AnyCoral][AnyCoral][AnyCoral] in ALL your dive sites"`
- GameEnd "only": `"only [FreePlayFishFromHand]"`

---

## Step 4: Issues You Must NOT Fix

Do **NOT** edit `Card.jsx`, `Card.scss`, or any file other than `cards.json`. Instead, report these rendering issues in the `css_issues` array.

CSS issues to report (if you observe them):
- Icons in the ability area appear too large or too small relative to the card
- Ability background wash extends beyond the intended area
- Silhouette is severely mispositioned (not just slightly off)
- Zone or cost pill boxes are incorrectly sized
- Any layout issue clearly caused by CSS metrics, not data

---

## Step 5: Output Format

At the very end of your response, output **exactly one** JSON code block with this structure. No other JSON blocks.

```json
{
  "card_id": 136,
  "card_name": "American Pocket Shark",
  "status": "ok",
  "issues": [],
  "fixes_applied": [],
  "css_issues": []
}
```

**Status values:**
- `"ok"` — no issues found
- `"data_fixed"` — card data issues were fixed in cards.json
- `"css_issues"` — rendering issues requiring CSS changes (reported only)
- `"mixed"` — both data fixes applied AND css issues reported
- `"error"` — something went wrong (explain in `issues`)

**Issue object schema:**
```json
{
  "severity": "high",
  "category": "ability_icons",
  "description": "Missing FishFromHand icon after BlueCoral in ability",
  "expected": "[BlueCoral][FishFromHand]",
  "actual": "[BlueCoral]"
}
```
Categories: `ability_icons`, `ability_text`, `band`, `description`, `zones`, `costs`, `points`, `length`, `tags`, `silhouette`, `sizing`, `positioning`, `layout`, `other`

**Fix object schema:**
```json
{
  "field": "ability",
  "old_value": "[BlueCoral][SchoolFeederMove]",
  "new_value": "[BlueCoral][FishFromHand]"
}
```

**CSS issue object schema:**
```json
{
  "severity": "medium",
  "file": "src/card/Card.scss",
  "selector": ".ability-container .ability img",
  "current_value": "height: 9cqw",
  "suggested_value": "height: 7cqw",
  "description": "Ability icons appear oversized relative to the card area in the PDF"
}
```

---

## Important Notes

- The **expansion logo size** (`.expansion-logo { height: 5cqw }`) is a known global issue. Do NOT report it as a per-card CSS issue.
- If a card has `group: "starter"`, it should have gray diagonal corner triangles. Base set cards have none.
- The `coral` field is NOT rendered visually as a badge — it's only game-rule data. The coral TYPE is conveyed by the `band` background color and coral icons in the ability text.
- The `band` field controls background: null=base (dark), "blue"=blue, "green"=green, "purple"=purple.
- If you are unsure about a fix, report it as an issue instead of applying it.
