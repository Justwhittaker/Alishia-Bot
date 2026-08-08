---
name: preview
description: >-
  Opens http://localhost:3000 in Cursor's right-side browser panel. Use when
  the user invokes /preview, asks to preview the app, open localhost:3000, or
  show the local frontend in the IDE browser.
disable-model-invocation: true
---

# /preview — open localhost:3000 in the browser panel

## Goal

When the user runs `/preview`, **immediately** open the local app at
`http://localhost:3000` in Cursor's **right browser panel**. Do not wait for
extra confirmation.

Canonical URL: `http://localhost:3000`  
(Accept `http://127.0.0.1:3000` as equivalent if needed.)

## Workflow

Copy and track:

```
Preview:
- [ ] 1. Quick port check on :3000
- [ ] 2. Open URL in IDE browser panel (required)
- [ ] 3. One-line confirmation to the user
```

**Hard requirement:** Step 2 is mandatory on every `/preview` run.
Do **not** only tell Justin to open the URL manually.

### 1. Quick port check

```bash
curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 1 http://localhost:3000/ || true
```

- If reachable (any HTTP response): proceed to open.
- If not reachable: still open the browser panel to `http://localhost:3000`, and
  mention in the confirmation that nothing answered on `:3000` yet (do not
  auto-start a server unless the user asks).

### 2. Open in the right browser panel (required)

Prefer this order:

**A. Cursor IDE browser (best — side/browser panel)**

1. `GetMcpTools` for `cursor-ide-browser` / `browser_navigate` (discover schema).
2. Call `browser_navigate` with:
   - `url`: `http://localhost:3000`
   - Do **not** treat this as background-only automation — the panel should be
     visible so Justin can see the preview.
3. If a tab already exists, navigate that tab to `http://localhost:3000`
   (check `browser_tabs` with `action: "list"` first when useful).

**B. Fallback — workbench opener**

If `cursor-ide-browser` is unavailable / not connected:

```text
CallMcpTool server=cursor-app-control toolName=open_resource
arguments: { "uri": "http://localhost:3000" }
```

**C. Last resort**

Tell Justin to run Command Palette → **Simple Browser: Show** →
`http://localhost:3000`, and that the automated open failed.

### 3. Confirmation

One short line, e.g.:

- `Preview open: http://localhost:3000`  
- or `Preview open: http://localhost:3000 (nothing listening on :3000 yet)`

## Rules

- Default host/port is always **localhost:3000** unless the user names another
  port in the same message (e.g. `/preview 8000` → `http://localhost:8000`).
- Do not commit, push, or edit project files for a plain `/preview`.
- Do not start `npm run dev` / Docker / etc. unless the user also asks to start
  the server.
- Keep the chat reply brief — the browser panel is the deliverable.
