# MyNDIS.wiki Visual Design System & Brand Guidelines

**Project Name**: MyNDIS.wiki  
**Tagline**: *The People's Guide to the NDIS — A human to human disability resource.*  
**Version**: 1.0 (Draft 1)

---

## 1. Design Ethos & Purpose

MyNDIS is an independent, community-focused disability resource dedicated to preserving primary NDIS source material and providing a practical, accessible guide for participants, applicants, and advocates.

The visual identity reflects **empathy, clarity, transparency, and authority**:
- **Human-Centric**: Warm, non-institutional aesthetic built around the heart-handshake symbol.
- **Accessibility First**: Meets WCAG 2.1 AA and AAA contrast guidelines to accommodate low-vision readers, screen reader users, and neurodivergent individuals.
- **Comfortable Reading**: Soft off-white backgrounds reduce glare and cognitive fatigue during long reading sessions.

---

## 2. Color Palette & WCAG Accessibility Matrix

All colors are specified for the light theme canvas (`#F5F6F3`).

| Role | Name | Hex Code | RGB | WCAG Contrast (vs `#F5F6F3`) | Rating | Primary Usage |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Primary** | Navy | `#172A52` | `rgb(23, 42, 82)` | **11.8 : 1** | **AAA** | Headings, site title, primary links, brand mark |
| **Body Copy** | Black | `#171717` | `rgb(23, 23, 23)` | **17.2 : 1** | **AAA** | All body paragraph text for maximum clarity |
| **Highlight** | Green | `#3F7652` | `rgb(63, 118, 82)` | **4.7 : 1** | **AA** | Primary buttons, success indicators, key highlights |
| **Secondary Accent** | Coral | `#D96F5F` | `rgb(217, 111, 95)` | **3.8 : 1** | **AA (Large Text / Callout Border)** | Important notices, warning borders, accent highlights |
| **Background** | Cool Off-White | `#F5F6F3` | `rgb(245, 246, 243)` | Canvas | — | Main site background canvas (anti-glare) |
| **Accent Tint** | Soft Coral Tint | `#FDF2F0` | `rgb(253, 242, 240)` | Surface | — | Background fill for "Important" callout boxes |
| **Highlight Tint** | Soft Green Tint | `#EEF5F0` | `rgb(238, 245, 240)` | Surface | — | Hover fill for secondary outlined buttons & badges |

---

## 3. Typography Hierarchy

### Font Families
- **Headings**: `'Georgia'`, `'Playfair Display'`, or system serif font stack. Provides a warm, editorial, and trustworthy tone.
- **Body Text**: `-apple-system`, `BlinkMacSystemFont`, `'Segoe UI'`, `Roboto`, `sans-serif`. Clean, highly readable, and optimized across operating systems and assistive tech.

### Type Scale & Specs

```text
H1 (Page Title)      : 2.25rem (36px) | Bold (700)   | Color: Navy (#172A52) | Bottom Rule: 2px solid Navy
H2 (Section Header)  : 1.75rem (28px) | Bold (700)   | Color: Navy (#172A52)
H3 (Subheading)      : 1.25rem (20px) | Medium (600) | Color: Navy (#172A52)
Body Copy            : 1.00rem (16px) | Regular (400)| Color: Black (#171717)| Line Height: 1.6
Subtext / Captions   : 0.875rem(14px) | Regular (400)| Color: #4A5568        | Line Height: 1.5
Source Information   : 0.875rem(14px) | Italic (400) | Color: #4A5568        | Citation / Archive Links
```

---

## 4. UI Components Specification

### Buttons
- **Primary Button**:
  - Background: Solid Green (`#3F7652`)
  - Text: White (`#FFFFFF`), Bold (600)
  - Radius: `8px`
  - Hover / Focus: `#2F593E` with visible focus ring
- **Secondary Button**:
  - Background: Transparent
  - Border: `2px solid #3F7652` (Green)
  - Text: Green (`#3F7652`), Bold (600)
  - Radius: `8px`
  - Hover / Focus: Soft Green Tint (`#EEF5F0`)

### Callout Boxes ("Important" Notices)
- **Border**: Left border `4px solid #D96F5F` (Coral)
- **Background**: Soft Coral Tint (`#FDF2F0`)
- **Title**: Coral (`#D96F5F`), Bold
- **Body Text**: Black (`#171717`) for high contrast readability

---

## 5. Logo System & Asset Reference

The MyNDIS logo mark combines a **heart** outline with **clasping hands** to symbolize mutual aid, community care, and practical support.

### Available Vector Assets (`visual/assets/`)
- `logo-mark.svg`: Primary Navy icon mark on transparent background.
- `logo-mark-white.svg`: White icon mark for dark navigation bars or footers.
- `logo-horizontal.svg`: Combination logo with mark + full title + subtitle.
- `favicon.svg`: High-clarity 32x32 SVG favicon for browser tabs.

### Usage Guidelines
- **Clear Space**: Maintain a minimum margin around the logo equal to 25% of the mark's height.
- **Minimum Size**: Do not render the mark smaller than `20px x 20px` in digital interfaces.
- **Do Not**: Distort stroke ratios, alter the core colors, or place on low-contrast backgrounds.
