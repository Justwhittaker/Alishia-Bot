---
name: admin
description: >-
  Fast-builds a staff admin portal to list customers/merchants, edit profiles,
  add/edit/delete deals, and remove accounts. Use when the user invokes /admin,
  asks for an admin portal, staff console, merchant management, or reusable
  admin CRUD for a website.
disable-model-invocation: true
---

# /admin — universal staff admin portal (fast build)

## Goal

When the user runs `/admin`, scaffold (or extend) a **staff admin portal** so
ops can:

- Load **customer / merchant profiles**
- **Edit** profiles
- **Add / edit / delete deals**
- **Remove accounts** from the website

Build against the **current project stack**. Prefer Next.js App Router + a
JSON API (FastAPI / Express / etc.). Match existing design tokens; do not invent
a second visual system.

This skill is the reusable playbook for Justin’s other planned websites.

## Non-negotiables (FORCE)

1. **Separate staff auth** from end-user / merchant login (role `admin`).
2. **Server-side secret** for admin API mutations (`ADMIN_API_KEY` →
   `X-Admin-Key`). Never expose the key to the browser.
3. **BFF / proxy** (Next.js `/api/admin/[...path]`) checks session role, then
   forwards with the admin key.
4. **Delete account** removes the entity and cascaded content (or soft-deletes
   if the product already uses soft delete — say so in the summary).
5. Confirm destructive actions in the UI.
6. Do not commit secrets; update `.env.example` only.

## Env contract (every site)

**API**

```bash
ADMIN_API_KEY=dev-admin-key-change-me
```

**Web**

```bash
ADMIN_EMAILS=you@example.com
ADMIN_PASSWORD=change-me-admin-password
ADMIN_API_KEY=dev-admin-key-change-me   # same as API
```

## Architecture (copy this shape)

```
/admin                     → merchant/customer list
/admin/merchants/[id]      → edit profile + deals + delete account
/admin/merchants/[id]/deals/new
/admin/deals               → all deals
/admin/deals/[id]/edit
/api/admin/[...path]       → session-gated proxy → /api/v1/admin/*
```

```
API: /api/v1/admin/*
  GET    /health
  GET    /merchants?q=
  POST   /merchants
  GET    /merchants/{id}
  PATCH  /merchants/{id}
  DELETE /merchants/{id}          # remove account
  GET    /merchants/{id}/deals
  GET    /deals?q=
  POST   /deals                   # staff create (bypass slot limits)
  GET    /deals/{id}
  PATCH  /deals/{id}
  DELETE /deals/{id}
```

Auth:

- Credentials provider `admin-login` allowlisted by `ADMIN_EMAILS` +
  `ADMIN_PASSWORD`
- JWT/session `user.role = "admin"`
- Merchant/user providers must **not** issue `role: admin`
- Admin layout: no admin session → staff sign-in; merchant dashboards should
  redirect admins to `/admin`

## Workflow

Copy and track:

```
Admin portal:
- [ ] 1. Detect stack (Next.js? API? existing auth?)
- [ ] 2. Add ADMIN_* env + API key dependency
- [ ] 3. Add /api/v1/admin/* CRUD behind X-Admin-Key
- [ ] 4. Extend session auth with admin role
- [ ] 5. Add BFF /api/admin/[...path]
- [ ] 6. Build /admin UI (list → detail → deal forms → delete)
- [ ] 7. Smoke: sign-in, edit profile, CRUD deal, delete account
- [ ] 8. Summarize URLs + env for the user
```

### 1. Detect

- Framework + auth (NextAuth, Clerk, custom)
- Domain entities (Merchant/User/Customer + Deal/Post/Listing)
- Existing list/update/delete endpoints to reuse vs wrap

### 2–3. API gate

```python
# FastAPI pattern
async def require_admin_key(x_admin_key: str | None = Header(None, alias="X-Admin-Key")):
    expected = settings.admin_api_key
    if not expected or not x_admin_key or not hmac.compare_digest(x_admin_key, expected):
        raise HTTPException(401, "Invalid or missing X-Admin-Key")
```

Staff deal creates should **bypass** product slot / paywall limits (or mark
`slot_exempt`) so ops can fix the live site without billing friction.

### 4–6. Frontend

Mirror dashboard chrome: top nav, centred `max-w-5xl`, mobile-safe
`max-w-[100vw] overflow-x-clip`.

Minimum UI:

| Screen | Actions |
|--------|---------|
| Merchants list | search/filter, open Manage |
| Merchant detail | edit fields, save, **Delete account**, deals table |
| Deal form | create/edit title, prices, active flag |
| All deals | cross-merchant inventory |

Client mutations call **`/api/admin/...` only** (never the raw admin key).

### 7. Verify

1. Wrong password → rejected
2. Merchant session cannot call `/api/admin/*`
3. Edit profile persists
4. Add / edit / deactivate / delete deal works
5. Delete account removes merchant (+ deals) and returns to list

## MealDeals reference (this monorepo)

Already implemented:

- Backend: `backend/app/api/v1/endpoints/admin.py`
- Frontend: `frontend/app/(admin)/…`, `frontend/lib/admin-api.ts`,
  `frontend/app/api/admin/[...path]/route.ts`
- Auth: `frontend/lib/auth.ts` provider `admin-login`
- Env examples: `backend/.env.example`, `frontend/.env.example`

Open: **`/admin`**

## Do not

- Reuse merchant `session.user.id` as staff identity
- Put `ADMIN_API_KEY` in `NEXT_PUBLIC_*`
- Skip confirmations on delete
- Build a second design system
- Commit real passwords/keys

## Done criteria

Tell the user:

- Admin URL (`/admin`)
- Which env vars to set
- What they can do (profiles, deals CRUD, remove accounts)
- That the same `/admin` skill can be re-run on the next website
