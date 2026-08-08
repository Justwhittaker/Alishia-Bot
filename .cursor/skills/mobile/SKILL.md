---
name: mobile
description: >-
  Universal Mobile UI/UX fixer. Ensures margins and banners stretch and minimize
  to the screen size, centres content unless otherwise specified, fits all
  content to the viewport with no left-right scrolling, and follows worldwide
  mobile standards (WCAG, Apple HIG, Material). Use when the user invokes
  /mobile, asks for mobile UI fixes, responsive layout, overflow scrolling, or
  mobile UX cleanup.
disable-model-invocation: true
---

# /mobile — universal Mobile UI/UX fixer

## Goal

When the user runs `/mobile`, audit and fix the current project's UI so it is
a **proper mobile experience**:

- **Margins and banners stretch and minimize to the size of screen**
- **Centre content unless otherwise specified**
- **All content fits to screen and there is no left right scrolling**
- Work stays **inline with global standards** (WCAG / Apple HIG / Material)

Prefer small, focused CSS/layout fixes in the existing design system. Do not
redesign the product unless asked.

## Non-negotiables (FORCE)

1. **No horizontal scrolling** on phones — `overflow-x` must not appear for
   normal content. Fix root causes (fixed widths, negative margins, 100vw
   traps, wide media, long unbroken strings). Do not paper over with
   `overflow-x: hidden` on `body` unless a third-party widget forces it, and
   document that exception.
2. **Full-bleed banners / heroes / headers** use the screen width (`width:
   100%` / `100%` of the content column), with padding that **minimizes** on
   small screens (tighter gaps, not desktop margins).
3. **Centre content unless otherwise specified** — primary columns, empty
   states, CTAs, and marketing blocks are horizontally centered
   (`margin-inline: auto` / flex/grid `justify-items/place-items: center` /
   `text-align: center` where typography should center). Keep start-aligned
   body copy in dense reading UIs (forms, tables, chat) when that is clearly
   intentional.
4. **Everything fits the viewport width** — images, videos, cards, tables,
   code blocks, ads, and carousels shrink or wrap within the screen.
5. **Touch-friendly** — interactive targets meet global minimums (see
   Standards).
6. **Safe areas** — respect notches / home indicators
   (`env(safe-area-inset-*)`) for fixed headers, footers, banners, and
   bottom sheets.

## Worldwide standards (follow these)

Align fixes with current global guidance:

| Standard | Apply |
|----------|--------|
| **WCAG 2.2** | Reflow to 320 CSS px wide without horizontal scroll (Success Criterion 1.4.10). Target size ≥ **24×24 CSS px** minimum; prefer **44×44** where practical (2.5.8 / prior AAA guidance). |
| **Apple HIG** | Minimum touch target **44×44 pt**. Readable Dynamic Type–friendly sizing. Layout margins that tighten on compact widths. |
| **Material Design 3** | Touch/click targets **48×48 dp** preferred. Responsive layout grids; content padding from edge. |
| **Viewport** | Correct meta viewport: `width=device-width, initial-scale=1` (add `viewport-fit=cover` only if using safe-area bleed). |
| **Responsive web** | Fluid widths, relative units, media queries / container queries. Avoid device-sniffing CSS. |

**Reference widths to verify against:** 320, 360, 375, 390, 414 (phones),
then 768 (tablet). Primary acceptance: **375** and **320** with **no
horizontal scroll**.

## Workflow

Copy and track:

```
Mobile UI/UX:
- [ ] 1. Detect stack + global layout / banner / chrome files
- [ ] 2. Audit overflow + fixed widths + banner margins
- [ ] 3. Apply layout fixes (stretch/minimize, centre, fit)
- [ ] 4. Safe areas + touch targets + typography
- [ ] 5. Smoke-check at 320 / 375 (no left-right scroll)
- [ ] 6. Summarize files changed
```

### 1. Detect project

- Framework (Next.js / React / etc.) and styling system (Tailwind, CSS
  modules, global CSS, styled-components)
- Root layout / shell: `layout.tsx`, `globals.css`, header, footer, banners,
  cookie/newsletter popups, ads
- Any existing breakpoints — extend them; do not invent a parallel system

### 2. Audit (find the mobile breaks)

Search for common overflow causes:

- Hard-coded widths: `width: 1200px`, `min-width` larger than viewport
- `100vw` on elements inside padded containers (classic scrollbar overflow)
- Flex/grid children that cannot shrink (`flex-shrink: 0`, missing `min-w-0`)
- Images/video without `max-width: 100%` / `height: auto`
- Tables or pre/code without wrapping or horizontal containment **inside**
  a card (prefer wrap; if scroll is required, isolate it to that component
  only — never the page)
- Absolute/fixed banners wider than the screen or with large side margins
- Negative margins that pull content past the viewport edge

### 3. Apply layout fixes

**Page shell**

- Content column: `width: 100%`, `max-width` for desktop, `margin-inline: auto`
- Horizontal page padding: minimize on small screens (e.g. `16px` → `12px` on
  very small), still enough for WCAG/Material edge spacing
- Prefer `min()` / `clamp()` for fluid spacing and type

**Margins and banners stretch and minimize to the size of screen**

- Banners, alert bars, promo strips, heroes: span the usable content width
  (full-bleed to screen edges when the design is edge-to-edge; otherwise
  full width of the centred column)
- Reduce oversized desktop padding/margins at mobile breakpoints
- Sticky/fixed bars: `left: 0; right: 0; width: 100%` plus safe-area padding

**Centre content unless otherwise specified**

- Main marketing sections, logos, primary CTAs, empty states: centred
- Forms: centre the form container; labels/fields may stay start-aligned for
  readability (global form UX standard)
- If a component or copy explicitly says left/right aligned, keep that

**Fit + no left-right scrolling**

```css
/* Media */
img, video, canvas, svg {
  max-width: 100%;
  height: auto;
}

/* Flex/Grid children that overflow */
.min-w-0 { min-width: 0; } /* ensure applied on overflowing flex children */

/* Long strings */
.break-words { overflow-wrap: anywhere; word-break: break-word; }
```

- Prefer `%`, `max-width: 100%`, `fr`, `auto-fit` over fixed px widths
- Replace `width: 100vw` with `width: 100%` unless truly viewport-bleed and
  tested without horizontal scroll
- Wide components (maps, embeds, data tables): constrain to parent; allow
  **local** `overflow-x: auto` only on that widget, never on `body`/`html`

### 4. Safe areas, touch, type

```css
padding-left: max(12px, env(safe-area-inset-left));
padding-right: max(12px, env(safe-area-inset-right));
padding-bottom: max(12px, env(safe-area-inset-bottom));
```

- Buttons / links / icon hits: aim **44×44 px** (Apple) / **48×48 dp**
  (Material); never below WCAG **24×24**
- Keep body text ≥ 16px on inputs where possible (reduces iOS focus zoom)
- Spacing between tappable controls: enough to avoid mis-taps (~8px+)

### 5. Verify

For the pages you touched:

1. Resize or emulate **320** and **375** wide
2. Confirm **no left-right page scrolling**
3. Confirm banners/headers span correctly and margins feel minimized
4. Confirm primary content is centred (unless specified otherwise)
5. Confirm fixed bottom/top UI clears the home indicator

If a browser MCP / preview is available, open the local app and spot-check;
otherwise rely on code inspection + reasoned CSS fixes.

### 6. Done criteria

Tell the user:

- Which screens/components were fixed
- That content fits the screen with **no left-right scrolling**
- That banners/margins stretch and minimize to the screen
- That content is centred unless a noted exception applies
- Which standards informed the choices (WCAG reflow, HIG/Material targets)

## Do not

- Introduce horizontal page scroll
- Leave fixed desktop widths on mobile
- Centre every label in dense data forms by default
- Hide overflow instead of fixing width bugs (except documented third-party)
- Break desktop layout unnecessarily — use responsive breakpoints
- Commit or push unless the user asks (or runs `/push`)

## Optional (only if asked)

- Add a dedicated small-screen regression checklist to the repo
- Tune tablet (768+) layouts
- Dark mode / large-text (Dynamic Type) passes
