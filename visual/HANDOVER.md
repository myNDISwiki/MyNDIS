# MyNDIS.wiki Visual Design Package — Handover Document

**Date**: 2026-09-14  
**Status**: Staged & Committed on `main` and `designd1`  
**Current Active Revision**: **Draft 2 (`-d2`)**

---

## 📋 Overview of Work Completed Today

1. **Established Design Directory Architecture**:
   - `/visual/guide/`: Guidelines & interactive HTML showcase pages.
   - `/visual/theme/`: CSS Custom Properties & stylesheets.
   - `/visual/assets/`: Scalable vector SVG logos and favicons.
2. **Refined Brand Identity & Color Tokens (Draft 2)**:
   - **Navy (`#172A52`)**: Primary Headings & Links (WCAG 11.8:1 AAA).
   - **Body Copy Black (`#171717`)**: Lighter antialiased body text (weight 300, WCAG 17.2:1 AAA).
   - **Vibrant Green (`#2E8C59`)**: Primary Action Buttons & Tag text (WCAG 4.6:1 AA — *Updated for brightness & vibrancy to balance Coral*).
   - **Coral (`#D96F5F`)**: Important Notice Callout Borders & Accents (WCAG 3.8:1 AA for UI borders).
   - **Cool Off-White (`#F5F6F3`)**: Anti-glare background canvas.
3. **Interactive Components & Showcases**:
   - Created `visual/guide/design-system-showcase-d2.html` featuring live route cards, notice callout boxes, concept tag badges (Navy outline, Green text, no slashes), inline body link states (Inactive Navy vs Active/Hover Green), thinner 1px HR dividers, and clean footer layout.
4. **Draft Versioning System Implemented**:
   - All revisions preserved with explicit draft suffixes (`-d1`, `-d2`) across `visual/guide/` and `visual/theme/`.

---

## 🚨 Open Action Items for Tomorrow

### 1. 🔴 HIGH PRIORITY: Replace Temporary SVG Logo Assets
- **Issue**: The current SVG files in `visual/assets/` (`logo-mark.svg`, `logo-mark-white.svg`, `logo-horizontal.svg`, `favicon.svg`) are temporary auto-traced vectors. They contain minor point irregularities and stroke artifacts.
- **Action**: Have a graphic designer or team member export clean, hand-crafted SVG vector line art directly from **Figma**, **Adobe Illustrator**, or **Inkscape** using smooth cubic Bezier curves.
- **Target Location**: Overwrite or replace files in `visual/assets/`.

### 2. 🟡 MEDIUM PRIORITY: Maintainer Review of Draft 2
- **Action**: Open `visual/guide/design-system-showcase-d2.html` in browser and review `visual/guide/brand-guidelines-d2.md`.
- **Feedback**: Verify whether any additional color tokens, font sizes, or button variants are required.

### 3. 🟡 MEDIUM PRIORITY: Docusaurus Setup & Theme Wiring
- **Action**: Import `visual/theme/theme-variables-d2.css` into the public wiki repository setup (e.g. `src/css/custom.css`).
- **Footer Disclaimer**: Implement the mandatory legal disclaimer in the global Docusaurus layout footer:
  > *MyNDIS is an independent information project and is not an official Australian Government or NDIA website. Information is maintained and updated as carefully as possible, but may become outdated or contain errors. Always check relevant official sources when making decisions about your NDIS supports, rights, or obligations.*

### 4. 🟢 LOW PRIORITY: Future Design Revisions
- **Rule**: If further visual changes are requested, create new files with `-d3` suffixes (e.g. `brand-guidelines-d3.md`, `design-system-showcase-d3.html`, `theme-variables-d3.css`) and update `visual/README.md` persistent links. Do **not** overwrite `-d1` or `-d2` files.

---

## 🔗 Quick File Reference

| Purpose | Persistent Draft 2 Location |
| :--- | :--- |
| **Directory Index** | [`visual/README.md`](README.md) |
| **Subfolder Index: Guides** | [`visual/guide/README.md`](guide/README.md) |
| **Subfolder Index: Theme** | [`visual/theme/README.md`](theme/README.md) |
| **Subfolder Index: Assets** | [`visual/assets/README.md`](assets/README.md) |
| **Brand Guidelines** | [`visual/guide/brand-guidelines-d2.md`](guide/brand-guidelines-d2.md) |
| **Interactive Showcase** | [`visual/guide/design-system-showcase-d2.html`](guide/design-system-showcase-d2.html) |
| **CSS Theme Variables** | [`visual/theme/theme-variables-d2.css`](theme/theme-variables-d2.css) |
