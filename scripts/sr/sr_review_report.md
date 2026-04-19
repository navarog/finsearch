# S&R Card Visual Review Report

**Cards reviewed:** 80  
**OK / data fixed:** 79  
**CSS issues only:** 1  
**Mixed (data + CSS):** 0  
**Errors / skipped:** 0  

---

## CSS / Rendering Issues (Require Manual Fix in Card.scss / Card.jsx)

### Card 188: Sablefish
- **Severity:** medium
- **File:** `src/card/Card.scss`
- **Selector:** `.ability-container .ability.also-if`
- **Current:** `padding: 1cqw 0 1cqw 0; gap: 0.7cqw; img { height: 5cqw; max-height: 5cqw; }`
- **Suggested:** `Consider increasing min-height or allowing the also-if box to grow; or reduce img height to 4cqw when 3+ icons are present to ensure all icons fit without clipping`
- **Description:** The 'also, if' conditional box clips the third coral icon when 3 icons are stacked. The combined height of 3 icons (3×5cqw) + gaps (2×0.7cqw) + padding (2×1cqw) ≈ 18.4cqw may exceed available space in the right-side ability column due to the card's aspect ratio and two-box IfActivated layout. Either the min-height of the also-if section should be increased, or the icon size should be reduced slightly to ensure all icons remain visible.

## Data Fixes Applied

None.

## Outstanding Data Issues (Not Auto-Fixed)

### Card 188: Sablefish `[css_issues]`
- **[medium]** The third [PurpleCoral] icon in the 'also, if' conditional section is not visible in the webapp. The JSON correctly encodes [PurpleCoral][PurpleCoral][PurpleCoral], and the PDF shows all three, but only two are rendered. The '.also-if' ability box appears to clip or overflow the third icon due to insufficient height or the outer ability-container layout constraints.
  - Expected: `3 purple coral icons visible in the 'also, if' section`
  - Actual: `Only 2 purple coral icons visible; third is clipped/hidden`
