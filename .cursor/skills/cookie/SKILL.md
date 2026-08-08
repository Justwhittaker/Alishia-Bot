---
name: cookie
description: >-
  Adds a GDPR-friendly cookie consent banner and preference center to a website,
  gates analytics/ads until opt-in, persists choice, and adds Cookie settings in
  the footer. Use when the user invokes /cookie, asks for cookie capture,
  cookie consent, GDPR cookies, or CMP-style Accept/Reject/Customize.
disable-model-invocation: true
---

# /cookie — cookie consent capture

## Goal

Add a **compliant cookie consent** flow to the current website project so:

- Necessary cookies always work
- Analytics / ads / marketing wait for opt-in
- Users can **Accept all**, **Reject non-essential**, or **Customize**
- Choice is remembered
- Site content stays usable (no Accept-all hard wall)
- Footer has **Cookie settings** to reopen preferences

Prefer matching the project's existing stack (Next.js / React first; adapt if another framework).

## Compliance rules (FORCE)

1. **No hard wall** — do not block reading the site until Accept. Soft banner / bottom sheet only.
2. **Reject as easy as Accept** — same visual weight; never Accept-only.
3. **Necessary always on** — auth, security, load balancing, essential prefs (e.g. location).
4. **Optional off by default** until consent: analytics, advertising, marketing.
5. **Persist choice** (cookie or localStorage) and respect it on later visits.
6. **Re-openable** — footer (or legal) link: Cookie settings.
7. **Do not load gated scripts** before consent (Vercel Analytics, AdSense, pixels, etc.).

This is an engineering pattern, not legal advice. If the project already has a CMP, improve it — do not install a second banner.

## Categories

| Category | Default | Examples |
|----------|---------|----------|
| `necessary` | always on | session, CSRF, auth, essential location pref |
| `analytics` | off | `@vercel/analytics`, Plausible, GA |
| `marketing` | off | AdSense, Meta/Google ads pixels, remarketing |

## Implementation workflow

Copy and track:

```
Cookie consent progress:
- [ ] Detect stack + existing consent/analytics/ads
- [ ] Add consent storage + helpers
- [ ] Add banner + customize UI
- [ ] Gate analytics/ads scripts
- [ ] Footer Cookie settings link
- [ ] Wire into root layout
- [ ] Smoke-check Accept / Reject / Customize / reopen
```

### 1. Detect project

- Framework (Next.js App Router preferred)
- Whether `@vercel/analytics`, AdSense, GTM, or other trackers already exist
- Footer / site chrome location for the settings link
- Existing cookie utilities — reuse patterns; avoid conflicting cookie names

### 2. Consent storage

Create a small client module (Next.js example paths):

- `lib/cookie-consent.ts` — types, read/write, defaults
- Storage key: `cookie_consent` (JSON)
- Shape:

```ts
type ConsentState = {
  necessary: true;          // always true
  analytics: boolean;
  marketing: boolean;
  updatedAt: string;        // ISO
};
```

Helpers:

- `getConsent()` / `setConsent(partial)` / `hasAnswered()` / `acceptAll()` / `rejectNonEssential()`
- `canUseAnalytics()` / `canUseMarketing()`
- Listen for a `cookie-consent-updated` window event (or context) so gated scripts can mount/unmount live

Persist with `localStorage` **and** a first-party cookie (1 year, `SameSite=Lax`, `Path=/`) so middleware/SSR can read if needed. Necessary functional cookies (auth/location) are separate and not gated.

### 3. UI components

Add:

- `components/cookie/CookieBanner.tsx` — first-visit banner
- `components/cookie/CookieSettings.tsx` — customize toggles (analytics / marketing)
- Optional: `components/cookie/CookieConsentProvider.tsx` if context is cleaner than events

**Banner copy (default — adapt brand name):**

- Title: Cookie preferences
- Body: We use necessary cookies to run the site. Optional analytics and marketing cookies help us improve and measure ads — only with your permission.
- Buttons: **Reject non-essential** · **Customize** · **Accept all**

**Customize panel:**

- Necessary: on, disabled toggle, short explanation
- Analytics: toggle
- Marketing: toggle
- Actions: Save choices · Accept all · Reject non-essential

Match existing design tokens / components (Button, etc.). Keep it calm — no dark-pattern urgency, no pre-ticked optional boxes.

### 4. Gate third-party scripts

**Vercel Analytics (Next.js):**

```tsx
// only render when canUseAnalytics()
import { Analytics } from "@vercel/analytics/next";
{consent.analytics ? <Analytics /> : null}
```

**AdSense / ad scripts:**

- Do not inject the AdSense loader until `canUseMarketing()` is true
- If ads already mount globally, wrap them in the consent check

**After consent changes:**

- Accept analytics → mount analytics
- Reject → ensure analytics/marketing components unmount and do not send further events (best-effort; clear optional cookies you set if applicable)

### 5. Root layout wiring

In the app root layout (e.g. `app/layout.tsx`):

1. Mount consent provider / banner client component site-wide
2. Replace always-on `<Analytics />` with consent-gated version
3. Do not SSR-load marketing pixels before consent

### 6. Footer link

Add **Cookie settings** that dispatches open-settings (custom event or context). Place beside Privacy / Contact when those exist.

### 7. Verify

1. Fresh profile / cleared storage → banner visible; page content still usable
2. Reject → no Analytics/AdSense network calls on navigate
3. Accept all → analytics (and marketing if present) load
4. Customize → only selected categories load
5. Reload → banner hidden; choice kept
6. Cookie settings → panel reopens; changes apply

## Do not

- Block the entire site behind Accept
- Pre-check analytics/marketing toggles
- Make Reject harder to find than Accept
- Load Analytics/AdSense before opt-in
- Treat location/auth cookies as “marketing” that require the banner
- Add a second CMP if one already exists
- Commit or push unless the user asks

## Optional enhancements (only if asked)

- Link banner to Privacy Policy URL
- Geo-show banner only for EEA/UK (still fine to show globally)
- GTM consent mode mapping
- Cookie policy page listing cookie names

## Done criteria

Tell the user:

- Where files were added
- Which scripts are gated
- That Reject / Accept / Customize / Cookie settings work
- That the site is not hard-walled
