# Project skills (Customize → Skills)

Custom Cursor skills for Alishia Bot. Each skill is a folder with `SKILL.md`
under `.cursor/skills/` and appears in **Customize → Skills → Workspace** when
this repo is open in Cursor Desktop / Cloud.

| Skill | Command / use |
|-------|----------------|
| `admin` | `/admin` — staff admin portal scaffold |
| `agents-in-sidebar` | Keep agents in `.cursor/agents/` and commit |
| `cookie` | `/cookie` — GDPR cookie consent |
| `lesson` | `/lesson` — save durable lessons |
| `metric-monitor` | `/metric_monitor` — scrape metrics canvas |
| `mobile` | `/mobile` — mobile UI/UX fixer |
| `preview` | `/preview` — open localhost:3000 in browser panel |
| `push` | `/push` — commit all and push |
| `scrape` | `/scrape` — hospitality scrape refresh |
| `shopify-csv` | `/shopify_csv <csv path>` — repair/convert CSV to Shopify import, always unlisted (+ `**custom edits**`) |
| `shopify-csv-live` | `/shopify_csv_live <csv path>` — same as `/shopify_csv` but `Status=active` + `Published=true` |

## Where Customize finds them

| Scope | Path |
|-------|------|
| **Workspace** | `.cursor/skills/<name>/SKILL.md` (this folder — committed) |
| **User** (this machine) | `~/.cursor/skills/<name>/SKILL.md` |

After pulling `main` on Desktop: open **Customize → Skills**, filter **Workspace**.

Source: mirrored from Justin Bot’s `.cursor/skills/` (plus Shopify skills for this repo).
