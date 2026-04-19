# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FinSearch is a React SPA for searching and filtering Finspan trading card game cards. It's a purely static client-side app — all card data lives in `src/assets/cards.json`, indexed at runtime with FlexSearch for instant search results. There is no backend.

## Commands

```bash
npm start          # Dev server at http://localhost:3000
npm test           # Jest in watch mode (no tests currently exist)
npm run build      # Production build to /build (CI=false to suppress warnings as errors)
npm run start-prod # Build + serve production build locally
```

Deployment is automatic: every push to `main` triggers GitHub Actions to build and deploy to GitHub Pages at `/finsearch`.

## Architecture

**Data flow:**
1. `App.js` loads all cards from `cards.json` and manages filtered results via `useReducer`
2. `Search.jsx` builds a FlexSearch index over card fields and applies multi-dimensional filters
3. Filtered cards are passed back to `App.js` and rendered via `react-infinite-scroll-component`

**Component tree:**
```
App.js           — root state, holds allCards + filteredCards, passes dispatch to Search
  Search.jsx     — all filter UI; owns the FlexSearch index; emits filtered card arrays upward
    EmojiTextField.jsx  — text input with inline SVG icons
    EmojiButton.jsx     — toggle buttons for filter presets (zones, tags, length, group)
  InfiniteScroll
    Card.jsx     — renders a single card with background image + ability icons
```

**Filter types in Search.jsx:** text search (name, latin name, ability text), group (main/starter), length buckets (small/medium/large), zones (sunlight/twilight/midnight), tags (Bioluminescent, Camouflage, Electric, Predator, Venomous).

## Card Data

Master data is `scripts/cards.xlsx`. The `scripts/cards_to_json.py` Python script (requires pandas) converts it to `src/assets/cards.json`. After changing card data, re-run the script and commit the updated JSON.

Card object shape: `id`, `name`, `latin`, `group`, `length`, `points`, `cardCost`, `eggCost`, `youngCost`, `schoolFishCost`, `consuming`, `sunlight`, `twilight`, `midnight`, `abilityType`, `ability`, tags (boolean fields), `band`, `description`, `expansion` (base/sr), `coral` (null/blue/green/purple/any).

**S&R expansion fields:** `expansion: "sr"` marks S&R cards (IDs 136–215: 75 main + 5 starter). The `coral` field indicates what coral type the fish contributes to a dive site — this is a game-rule data field only, not rendered as a visual indicator (coral type is conveyed via the `band` background color and `[CoralIcon]` references in ability text).

## Assets

- `src/assets/backgrounds/` — card background images (WebP with PNG fallbacks)
- `src/assets/silhouettes/` — per-card fish silhouettes
- `src/assets/icons/` — SVG icons for abilities, zones, and tags

Use `scripts/webp.sh` to batch-convert new PNG/JPG assets to WebP (quality 25, mode 6).

## S&R Fidelity Audit Findings (April 2026)

### Bugs Fixed
1. **Zone CSS classes missing** (`Card.scss`): `.zones` container had no rules for `.s`, `.st`, `.stm` combinations, affecting 96 base cards and 59 S&R cards with sunlight-only or sun+twilight zones. Added `flex-start` alignment for `.s` and `.st`, `space-between` for `.stm`.
2. **`TuckedCardSolo` missing from `ALLOWED_EMOJIS`** (`EmojiTextField.jsx`): Icon exists in `src/assets/icons/` but was absent from the search filter icon list. Added. Note: `[TuckedCardSolo]` does NOT appear in any ability strings in the final corrected JSON — the icon file exists for potential future use.
3. **Wave-point ability ordering** (`cards.json`): Two S&R GAME END cards had ability text in the format `"if [AnyCoral] ...: N [Wave]"` which broke the `processAbilityText()` Wave regex (the `N [Wave]` token needs to be at the start of the chunk). Fixed to match the established format `"N [Wave] if [AnyCoral] ..."`:
   - id=202 Tasseled Scorpionfish: `"5 [Wave] if [AnyCoral] in ALL your dive sites"`
   - id=206 Variegated Lizardfish: `"3 [Wave] if [AnyCoral] (in a dive site with at least 5)"`
4. **Missing card descriptions** (`cards.json`): Three S&R cards had `null` descriptions despite having descriptions in the PDF source. Added:
   - id=148 Daggertooth
   - id=163 Gray Reef Shark
   - id=190 Sarcastic Fringehead

### Rendering Logic Notes
- **`processAbilityText()` Wave format**: Wave-point abilities MUST start with `"N [Wave]"` (e.g., `"5 [Wave] if ..."`). The regex `\d+ ?\[Wave\]` must match at the beginning of a token — if text comes before the wave number, the number gets consumed by the text regex.
- **`also, if` split**: Only applies to `IfActivated` cards. The split at `"also, if"` creates two `<div class="ability">` containers — first for the cost icons, second for the conditional effect.
- **Zone class generation**: `getZoneClass()` in Card.jsx builds a string like `"stm"` from `sunlight/twilight/midnight` field initials. CSS classes `.s`, `.st`, `.stm`, `.tm`, `.t`, `.m`, `.sm` control `justify-content` on the zones strip.
- **`coral` field**: Not rendered as a visual badge. Coral type is conveyed by `band` background and ability icon references. The `coral` field is purely a game-rule data field.
- **`midnight=2`**: Only two base cards (IDs 44, 77) use this; renders `PlayFishBottomRow` icon instead of `Night`. No S&R cards use it.

5. **Missing icons in `[Coral][FishFromHand]` abilities** (`cards.json`): Four S&R cards that give a coral token AND let each player play a fish from hand had `[SchoolFeederMove]` where `[FishFromHand]` was correct. Fixed:
   - id=163 Gray Reef Shark: `[PurpleCoral][FishFromHand]`
   - id=177 Nurse Shark: `[BlueCoral][FishFromHand]`
   - id=195 Spotted Wobbegong: `[GreenCoral][FishFromHand]`
   - id=162 Great Hammerhead: `[UnSchoolFish][FishFromHand]` (ability was also missing the second icon entirely)
6. **Duplicate coral icon in "(all players) on each" abilities** (`cards.json`): Three S&R WhenPlayed cards give one coral to EACH player; the ability correctly shows TWO coral icons side-by-side (one per player zone), but JSON had only one. Fixed:
   - id=159 Giant Moray: `(all players) [PurpleCoral][PurpleCoral] on each [AllPlayers]`
   - id=161 Great Barracuda: `(all players) [BlueCoral][BlueCoral] on each [AllPlayers]`
   - id=187 Roving Coral Grouper: `(all players) [GreenCoral][GreenCoral] on each [AllPlayers]`

7. **`[TuckedCardSolo]` / `[ConsumeFish]` misidentified as reward icon** (`cards.json`): Four S&R cards had the wrong reward icon in their `also, if` ability string. The correct icon is `[FishFromHand]` (blue card with white fish silhouette + red torn border). Fixed:
   - id=140 Basking Shark: `[TuckedCardSolo]` → `[FishFromHand]`
   - id=144 Bluering Angelfish: `[TuckedCardSolo]` → `[FishFromHand]`
   - id=186 Rough Abyssal Grenadier: `[ConsumeFish]` → `[FishFromHand]`
   - id=213 Blue Antimora: `[TuckedCardSolo]` → `[FishFromHand]`

   **`[FishFromHand]` icon visual signature**: blue/teal card border with white fish silhouette inside, red zigzag/torn lower border. Distinct from `[DrawCard]` (solid blue filled rectangle) and `[TuckedCardSolo]` (which has no valid ability-string usage in the current card set).

8. **Missing `[SchoolFeederMove]` in WHEN PLAYED ability** (`cards.json`): id=145 Bonnethead Shark had only one icon in its ability where the PDF clearly shows two. Fixed:
   - id=145 Bonnethead Shark: `[PurpleCoral]` → `[PurpleCoral][SchoolFeederMove]`

9. **Missing `[FishFromHand]` in WHEN PLAYED "(all players)" ability** (`cards.json`): id=203 Tiger Shark was missing the middle icon in a three-icon ability. Fixed:
   - id=203 Tiger Shark: `(all players) [FishHatch][AllPlayers]` → `(all players) [FishHatch][FishFromHand][AllPlayers]`

10. **`[NoCost]` used as ability text instead of actual effect icon** (`cards.json`): id=205 Toothy Goby is an IF ACTIVATED card where activation costs nothing (free). The NoCost icon appears in the PDF cost strip to indicate free activation — it is NOT the ability effect. The actual IF ACTIVATED box in the PDF shows `[PurpleCoral]`. Fixed:
    - id=205 Toothy Goby: `ability: "[NoCost]"` → `ability: "[PurpleCoral]"`
    - Note: `[NoCost]` should never appear in an `ability` field — it's a cost-strip display element that our app doesn't render.

### PDF Page Order vs JSON ID Order
The S&R PDF is in alphabetical order within each section. The JSON IDs (136–215) are NOT strictly alphabetical — there is at least one confirmed block where the ordering diverges:
- PDF pages 25–27 (0-indexed): Gray Reef Shark (page 25) → Great Barracuda (page 26) → Great Hammerhead (page 27)
- JSON IDs: Great Barracuda (id=161) → Great Hammerhead (id=162) → Gray Reef Shark (id=163)

The formula `page_idx = card_id - 136` breaks here. Always verify card names when auditing via PDF page crops.

11. **Over-counted `[UnSchoolFish]` in all-players ability** (`cards.json`): id=162 Great Hammerhead had 4x UnSchoolFish but PDF shows only 1. Fixed:
    - id=162 Great Hammerhead: `(all players) [UnSchoolFish][UnSchoolFish][UnSchoolFish][UnSchoolFish][FishFromHand][AllPlayers]` → `(all players) [UnSchoolFish][FishFromHand][AllPlayers]`

12. **Wrong icons in Leopard Shark ability** (`cards.json`): First icon was `[UnSchoolFish]` (should be `[PurpleCoral]`) and middle icon was `[Discard]` (should be `[UnSchoolFish]`). Fixed:
    - id=169 Leopard Shark: `[UnSchoolFish][Discard][ConsumeFish]` → `[PurpleCoral][UnSchoolFish][ConsumeFish]`

13. **`[Discard]` used instead of `[ConsumeFish]` in IfActivated abilities** (`cards.json`): Multiple S&R cards had `[Discard]` (hand dropping card) where the PDF clearly shows the fish-skeleton-in-blue-box icon = `[ConsumeFish]`. This affects both cost and reward positions. ALL occurrences of `[Discard]` in S&R ability strings were wrong. Fixed:
    - id=138 Armored Searobin: cost `[Discard]` → `[ConsumeFish]`
    - id=148 Daggertooth: reward `[Discard]` → `[ConsumeFish]`
    - id=157 Furry Coffinfish: cost `[Discard]` → `[ConsumeFish]`
    - id=166 Jensen's Skate: cost `[Discard]` → `[ConsumeFish]`
    - id=178 Owlfish: cost `[Discard]` → `[ConsumeFish]`
    - id=198 Striated Frogfish: reward `[Discard]` → `[ConsumeFish]`
    - id=211 African Coelacanth: `[Discard][Discard][Discard][Discard][Discard]` → `[ConsumeFish][ConsumeFish][ConsumeFish][ConsumeFish][ConsumeFish]`

    **Note**: `[Discard]` (hand dropping a card) does not appear in any S&R ability. All S&R fish-eating cost/reward icons use `[ConsumeFish]` (fish skeleton in blue box).

14. **`only [FreePlayFishFromHand]` abilities had wrong icon order and missing condition icon** (`cards.json`): Six S&R GAME END / WhenPlayed cards used `"only [FreePlayFishFromHand]"` but the PDF shows FreePlayFishFromHand as the EFFECT icon (first), followed by a condition icon, then "only" text. Each card has a different condition icon. Fixed:
    - id=149 Dusky Shark: `only [FreePlayFishFromHand]` → `[FreePlayFishFromHand] only [Estuary]`
    - id=150 Dwarf Lanternshark: `only [FreePlayFishFromHand]` → `[FreePlayFishFromHand] only [Bioluminescent]`
    - id=156 Frilled Shark: `only [FreePlayFishFromHand]` → `[FreePlayFishFromHand] only [Estuary]`
    - id=170 Lollipop Catshark: `only [FreePlayFishFromHand]` → `[FreePlayFishFromHand] only [Estuary]`
    - id=192 Shortnose Demon Catshark: `only [FreePlayFishFromHand]` → `[FreePlayFishFromHand] only [Estuary]`
    - id=200 Swell Shark: `only [FreePlayFishFromHand]` → `[FreePlayFishFromHand] only [TuckedCardSolo]`

15. **`[FreePlayFishFromHand] if no [X]` ability had wrong condition icon and was missing effect icon** (`cards.json`): id=141 Blackmouth Angler's GAME END ability had `FreePlayFishFromHand` as the condition but the PDF shows it as the EFFECT icon, with `AnyCoral` (pie chart) as the condition. Fixed:
    - id=141 Blackmouth Angler: `if no [FreePlayFishFromHand] in this fish's dive site` → `[FreePlayFishFromHand] if no [AnyCoral] in this fish's dive site`

16. **Missing icon in WhenPlayed ability** (`cards.json`): id=151 Epaulette Shark had only `[UnSchoolFish]` but PDF shows BlueCoral first. Fixed:
    - id=151 Epaulette Shark: `[UnSchoolFish]` → `[BlueCoral][UnSchoolFish]`

17. **Under-counted UnSchoolFish** (`cards.json`): id=146 Broadnose Sevengill Shark PDF shows 3 UnSchoolFish, JSON had only 2. Fixed:
    - id=146 Broadnose Sevengill Shark: `[UnSchoolFish][UnSchoolFish]` → `[UnSchoolFish][UnSchoolFish][UnSchoolFish]`

18. **Reversed icon order in WhenPlayed ability** (`cards.json`): id=176 Ninja Lanternshark PDF shows YoungFish (top) then UnSchoolFish (bottom). Fixed:
    - id=176 Ninja Lanternshark: `[UnSchoolFish][YoungFish]` → `[YoungFish][UnSchoolFish]`

19. **Wrong first icon in WhenPlayed ability** (`cards.json`): id=179 Portuguese Dogfish PDF shows YoungFish (dark fish, white eye) as first icon, not ConsumeFish. Fixed:
    - id=179 Portuguese Dogfish: `[ConsumeFish][FishFromHand]` → `[YoungFish][FishFromHand]`

20. **`[AnyCoral]` used where specific coral type is correct** (`cards.json`): Two cards had `[AnyCoral]` (pie chart) in their ability but the PDF shows a specific coral color. Fixed:
    - id=185 Rose-veiled Fairy Wrasse: `[AnyCoral]` → `[BlueCoral]`
    - id=201 Sydney's Pygmy Pipehorse: `[AnyCoral]` → `[PurpleCoral]`

### Known Data Patterns
- **`also, if` ability format**: `"[CostIcon] also, if [CoralIcon] in this dive site: [EffectIcon]"` — cost icon BEFORE "also, if", reward icon AFTER colon
- **GameEnd wave bonus format**: `"N [Wave] if [AnyCoral] condition"` (wave bonus amount first)
- **`only` keyword format**: `"[EffectIcon] only [ConditionIcon]"` — effect icon FIRST, then "only", then the condition icon (Estuary, Bioluminescent, TuckedCardSolo, etc.)
- **`if no [X]` GAME END format**: `"[EffectIcon] if no [ConditionIcon] in this fish's dive site"` — effect icon FIRST, condition icon AFTER "if no"
- **All-players abilities**: Pattern `"(all players) [Icon]"` in WhenPlayed — triggers for all players, not just the active player
- **Coral "on each" format**: `"(all players) [CoralIcon][CoralIcon] on each [AllPlayers]"` — two coral icons because each player receives one coral token
- **Coral + FishFromHand format**: `"[CoralIcon][FishFromHand]"` — places coral in the dive site AND allows each player to play a fish from hand. Not to be confused with `[SchoolFeederMove]`.
- **S&R never uses `[Discard]`**: All S&R cards use `[ConsumeFish]` (fish skeleton in blue box) for fish-eating actions. `[Discard]` (hand dropping a card) only appears in the base game.
- **Starter set PDF**: Cards 211–215 are in `new_materials/extracted/starter_set/S&R_starter_fish_r5.pdf` (6 pages: 5 cards + back page). NOT in the main S&R PDF.
