# MyNDIS.wiki Visual Design System & Assets (`visual/`)

This directory contains the visual identity, brand guidelines, CSS theme variables, interactive showcases, and scalable vector assets for the **MyNDIS.wiki** project.

**Tagline**: *The People's Guide to the NDIS — A human to human disability resource.*

---

## 📁 Directory Structure

```text
visual/
├── README.md                            # Directory overview & documentation index
├── guide/                               # Brand guidelines & interactive showcase pages
│   ├── brand-guidelines-d1.md           # Draft 1 specification document
│   ├── brand-guidelines-d2.md           # Draft 2 persistent brand guidelines & WCAG matrix
│   ├── design-system-showcase-d1.html   # Draft 1 interactive HTML showcase
│   └── design-system-showcase-d2.html   # Draft 2 interactive HTML showcase page
├── theme/                               # CSS custom properties & theme stylesheets
│   ├── theme-variables-d1.css           # Draft 1 CSS color tokens
│   └── theme-variables-d2.css           # Draft 2 persistent CSS theme variables
└── assets/                              # Scalable vector SVG logo & icon assets
    ├── logo-mark.svg                    # Primary heart-handshake Navy vector icon mark
    ├── logo-mark-white.svg              # White vector mark for dark headers/footers
    ├── logo-horizontal.svg              # Combination logo mark + serif title typography
    └── favicon.svg                      # Browser tab 32x32 SVG favicon
```

---

## 📌 Quick Reference & Persistent Documents

- **Brand & Visual Guidelines**: [`guide/brand-guidelines-d2.md`](guide/brand-guidelines-d2.md)  
  *Detailed specification covering color codes, WCAG AA/AAA accessibility contrast ratings, typography hierarchy, link states, button styles, and concept tags.*
- **Interactive HTML Showcase**: [`guide/design-system-showcase-d2.html`](guide/design-system-showcase-d2.html)  
  *Self-contained HTML page demonstrating live colors, route cards, notice callout boxes, and concept tags in browser.*
- **CSS Theme Variables**: [`theme/theme-variables-d2.css`](theme/theme-variables-d2.css)  
  *Ready-to-use CSS Custom Properties mapping all color codes, font stacks, and layout borders.*
- **Vector Assets Directory**: [`assets/`](assets/)  
  *Folder containing scalable SVG logo variants and favicons.*

---

## 🎨 Core Brand Palette

| Swatch | Color Role | Color Name | Hex Code | Contrast Ratio vs `#F5F6F3` | WCAG Rating |
| :---: | :--- | :--- | :--- | :--- | :--- |
| <span style="background-color:#172A52; border:1px solid #D0D7DE; display:inline-block; width:36px; height:22px; border-radius:4px; vertical-align:middle;"></span> | **Primary** | Navy | `#172A52` | **11.8 : 1** | **AAA (Headings & Links)** |
| <span style="background-color:#171717; border:1px solid #D0D7DE; display:inline-block; width:36px; height:22px; border-radius:4px; vertical-align:middle;"></span> | **Body Copy** | Black | `#171717` | **17.2 : 1** | **AAA (Paragraph Text)** |
| <span style="background-color:#2E8C59; border:1px solid #D0D7DE; display:inline-block; width:36px; height:22px; border-radius:4px; vertical-align:middle;"></span> | **Highlight** | Vibrant Green | `#2E8C59` | **4.6 : 1** | **AA (Primary Buttons & Tag Text)** |
| <span style="background-color:#D96F5F; border:1px solid #D0D7DE; display:inline-block; width:36px; height:22px; border-radius:4px; vertical-align:middle;"></span> | **Secondary Accent** | Coral | `#D96F5F` | **3.8 : 1** | **AA (UI Borders & Headers)** |
| <span style="background-color:#F5F6F3; border:1px solid #D0D7DE; display:inline-block; width:36px; height:22px; border-radius:4px; vertical-align:middle;"></span> | **Background** | Cool Off-White | `#F5F6F3` | Canvas | **Anti-Glare Surface** |

---

## 🔄 Draft & Versioning Guidelines

To ensure project history is preserved and existing work is never accidentally overwritten during design iterations:
1. **Never Overwrite Existing Drafts**: When proposing modifications or new design iterations, create a new draft file with an incremented suffix (e.g., `brand-guidelines-d3.md`, `design-system-showcase-d3.html`, `theme-variables-d3.css`).
2. **Update Directory README**: Point the persistent links in `visual/README.md` and root `README.md` to the newest approved draft version while keeping previous drafts intact in `visual/guide/` and `visual/theme/`.
3. **Asset Files**: Vector assets in `visual/assets/` may be updated or added with new variant names as needed.
