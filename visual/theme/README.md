# CSS Theme Variables & Stylesheets (`visual/theme/`)

This directory contains CSS Custom Properties (CSS variables) mapping all color tokens, typography stacks, border radii, and layout specs for **MyNDIS.wiki**.

---

## 📁 Folder Contents & Draft History

| File Name | Draft Version | Description |
| :--- | :--- | :--- |
| **`theme-variables-d3.css`** | **Draft 3 (Latest Persistent)** | Current tokens and component styles for glossary callouts, typography, menu links, tables, and expanded tint colours. |
| `theme-variables-d1.css` | Draft 1 (Archived) | Initial Draft 1 CSS color variables (`#3F7652`). |

---

## 🚀 How to Use in Docusaurus / Custom Frontends

Include or import `theme-variables-d2.css` in your site's global CSS file (e.g. `src/css/custom.css` in Docusaurus):

```css
@import url('./visual/theme/theme-variables-d2.css');
```

Key tokens available:
- `--myndis-navy`: `#172A52`
- `--myndis-body-black`: `#171717`
- `--myndis-green`: `#2E8C59`
- `--myndis-coral`: `#D96F5F`
- `--myndis-bg`: `#F5F6F3`
- `--myndis-font-heading`: `'Georgia', 'Playfair Display', serif`
- `--myndis-font-body`: `-apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Inter', sans-serif`

---

## 🔄 Draft Versioning Rules

- Create new CSS revisions using incremented suffixes (e.g., `theme-variables-d3.css`).
- Never overwrite existing `-d1` or `-d2` stylesheets.
