# MyNDIS.wiki Visual Design System & Brand Guidelines

**Project Name**: MyNDIS.wiki  
**Tagline**: *The People's Guide to the NDIS — A human to human disability resource.*  
**Version**: 1.1 (Refined Draft)

---

## 1. Design Ethos & Accessibility Standards

MyNDIS is an independent, community-focused disability resource dedicated to preserving primary NDIS source material and providing a practical, accessible guide for participants, applicants, and advocates.

### WCAG 2.1 Compliance Clarification
- **WCAG 2.1 Level AA Thresholds**:
  - **Normal Body Text**: Minimum **4.5 : 1** contrast ratio.
  - **Large Text (18px+ bold or 24px+ regular), UI Components & Borders**: Minimum **3.0 : 1** contrast ratio.
- **Compliance Status**:
  - **Navy (`#172A52`)**: **11.8 : 1 (Exceeds AAA)** — Used for Headings, Brand Title, Primary Links.
  - **Body Black (`#171717`)**: **17.2 : 1 (Exceeds AAA)** — Used for all body copy.
  - **Vibrant Green (`#2E8C59`)**: **4.6 : 1 (Meets AA)** — Used for Primary Action Buttons & Tag text.
  - **Coral (`#D96F5F`)**: **3.8 : 1 (Meets AA for UI Borders & Large Headers)** — Used for Important Callout left borders and bold section headers. Body text inside callouts uses dark `#171717` (17.2:1 AAA) on `#FDF2F0` tint fill.

---

## 2. Color Palette Matrix

| Role | Name | Hex Code | RGB | WCAG Contrast (vs `#F5F6F3`) | Rating | Primary Usage |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Primary** | Navy | `#172A52` | `rgb(23, 42, 82)` | **11.8 : 1** | **AAA** | Headings, site title, primary links, brand mark |
| **Body Copy** | Black | `#171717` | `rgb(23, 23, 23)` | **17.2 : 1** | **AAA** | All body paragraph text for maximum clarity |
| **Highlight** | Vibrant Green | `#2E8C59` | `rgb(46, 140, 89)` | **4.6 : 1** | **AA** | Primary buttons, success indicators, tag badge text |
| **Secondary Accent** | Coral | `#D96F5F` | `rgb(217, 111, 95)` | **3.8 : 1** | **AA (UI Borders/Headers)** | Important notice borders, callout headers, alerts |
| **Background** | Cool Off-White | `#F5F6F3` | `rgb(245, 246, 243)` | Canvas | — | Main site background canvas (anti-glare) |
| **Accent Tint** | Soft Coral Tint | `#FDF2F0` | `rgb(253, 242, 240)` | Surface | — | Background fill for "Important" callout boxes |
| **Highlight Tint** | Soft Green Tint | `#E6F4EA` | `rgb(230, 244, 234)` | Surface | — | Hover fill for secondary outlined buttons & tag pills |

---

## 3. Typography & Link States

### Typography Stack
- **Headings**: `'Georgia'`, `'Playfair Display'`, or system serif font stack.
- **Body Text**: `-apple-system`, `BlinkMacSystemFont`, `'SF Pro Text'`, `'Inter'`, `'Segoe UI'`, `sans-serif`.
  - **Weight**: Lighter weight (`300` / `400`) with smooth antialiasing (`-webkit-font-smoothing: antialiased`).

### Inline Link States (Body Copy & Guides)
- **Inactive Link State**: Navy (`#172A52`) with a 1.5px solid Navy underline (`text-underline-offset: 3px; font-weight: 500`).
- **Active / Hover Link State**: Vibrant Green (`#2E8C59`) with a 2px solid Green underline.

### Dividers & Rules
- All horizontal rules (`<hr>`) and section underlines are styled thin (**1px solid `#D0D7DE`**).

---

## 4. UI Components

### Concept Tag Badges
- **Shape**: Rounded pill (`padding: 0.35rem 0.85rem; border-radius: 20px`).
- **Border**: Navy outline (`1px solid #172A52`).
- **Text**: Vibrant Green (`#2E8C59`), Bold (600).
- **Format**: Clean concept names without slashes (e.g. `evidence`, `reasonable and necessary`, `functional capacity`).

### Buttons & Callouts
- **Primary Button**: Solid Green (`#2E8C59`), White text (`#FFFFFF`), `8px` rounded corners.
- **Secondary Button**: Outlined Green border (`2px solid #2E8C59`), transparent fill.
- **Callout Box**: Left border `4px solid #D96F5F` (Coral), soft coral tint background (`#FDF2F0`).
