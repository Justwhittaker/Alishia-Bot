---
name: lesson
description: >-
  Captures durable lessons from the current chat and saves them to the user's
  personal Cursor rules (skill list / memory). Use when the user invokes
  /lesson, asks to save a lesson, or wants to remember what went wrong or what
  worked.
disable-model-invocation: true
---

# /lesson — capture and save a lesson

## Goal

When the user runs `/lesson`, extract the durable takeaway from this
conversation and **save it under their personal skill/rules list** so future
agents follow it.

## Workflow

Copy and complete:

```
Lesson Progress:
- [ ] Extract 1–3 durable lessons from this chat
- [ ] List existing user rules (avoid duplicates)
- [ ] Add or update a personal rule with the lesson
- [ ] Confirm to the user what was saved
```

### 1. Extract the lesson

From the current conversation (and any user-stated preference), write:

- **Title** — short name (e.g. `Agents sidebar groups by git remote`)
- **Lesson** — 2–6 sentences: what to do / not do next time
- **When it applies** — trigger terms (sidebar, Mongo MCP, scrapes, etc.)

Prefer actionable guidance over narrative. Drop one-off incident detail.

If the user already stated the lesson text, use it **verbatim**.

### 2. Check for duplicates

Call `cursor_dialog` on `cursor-app-control`:

```json
{ "item": "rule", "scope": "user", "action": "list" }
```

If a rule already covers the same lesson, **update** that rule (`action: "update"` + `id`) instead of adding a near-duplicate.

### 3. Save to the personal rules list

**New lesson:**

```json
{
  "item": "rule",
  "scope": "user",
  "action": "add",
  "title": "<Title>",
  "content": "<Lesson>\n\nWhen it applies: <triggers>"
}
```

**Update existing:**

```json
{
  "item": "rule",
  "scope": "user",
  "action": "update",
  "id": "<id from list>",
  "title": "<Title>",
  "content": "<full updated content>"
}
```

### 4. Confirm

Tell the user:

1. The title saved
2. Whether it was **added** or **updated**
3. That it now appears in their personal rules / skill list (Cursor Settings → Rules)

## Optional: also keep a project note

Only if the lesson is codebase-specific and the user is inside a git repo with
`.cursor/rules/`, also write or update a focused `.mdc` rule there. Prefer
personal user rules for cross-project lessons (sidebar, MCP setup, etc.).

## Do not

- Invent lessons the chat did not support
- Save secrets, tokens, or full `.env` contents
- Create skills under `~/.cursor/skills-cursor/` (reserved)
- Commit or push unless the user asks
