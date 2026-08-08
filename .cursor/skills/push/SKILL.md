---
name: push
description: >-
  Auto-commits all newest local changes with a sensible message, then pushes
  commits to GitHub on the current branch. Use when the user invokes /push,
  asks to commit and push everything, or wants an automatic save-to-GitHub.
disable-model-invocation: true
---

# /push — commit all newest changes and push to GitHub

## Goal

When the user runs `/push`, **immediately**:

1. Commit **all newest** safe changes in every dirty git repo in the workspace
2. Push those commits to `origin` on the current branch

Do not ask for confirmation. `/push` is the explicit go-ahead to commit and push.

## Workflow

Copy and track:

```
Push:
- [ ] 1. Discover dirty git repos in the workspace
- [ ] 2. For each repo: status + diff + log (parallel)
- [ ] 3. Stage safe files (exclude secrets / junk)
- [ ] 4. Commit with HEREDOC message (skip if nothing to commit)
- [ ] 5. Push current branch to origin
- [ ] 6. Brief summary of commits + remote URLs
```

### 1. Discover repos

Check each workspace root (and nested project folders that are their own git
repos, e.g. `justin-bot` and `PRO4-Mealdeals`). For every path that has a
`.git` directory / is a git work tree and has changes **or** unpushed commits,
run the full flow.

If a multi-root workspace has several dirty repos, process **all** of them.

### 2. Inspect (required before each commit)

In each repo, run in parallel:

```bash
git status -sb
git status --porcelain
git diff
git diff --cached
git log -5 --oneline
git rev-parse --abbrev-ref HEAD
git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null || true
```

Also note untracked files. Follow the repo's recent commit-message style.

### 3. Stage safe files

Stage all newest changes relevant to the work:

```bash
git add -A
```

Then **unstage / never commit** secrets and junk if present:

| Never commit | Examples |
|--------------|----------|
| Secrets | `.env`, `.env.*` (except `*.env.example`), `credentials.json`, `*.pem`, `id_rsa` |
| Dependencies | `node_modules/`, `.venv/`, `venv/` |
| Build / cache | `.next/`, `dist/`, `build/`, `__pycache__/`, `*.pyc`, `.turbo/` |
| Runtime noise | `celerybeat-schedule`, `*.log`, `.DS_Store` |
| Local DB dumps unless clearly intentional | `*.sqlite3` |

If a secret was staged, unstage it and warn in the summary. Prefer relying on
`.gitignore`, but actively filter obvious secret paths.

If personal skills were updated under `~/.cursor/skills/` and the workspace
has a versioned `.cursor/skills/` (e.g. justin-bot), **copy the updated skill
folders into the repo** before staging so `/push` keeps them on GitHub too.

### 4. Commit

If there are staged changes:

```bash
git commit -m "$(cat <<'EOF'
Concise subject focused on why.

Optional 1-sentence body if needed.
EOF
)"
```

Commit message rules:

- 1–2 sentences, focus on **why**
- Match repo style (`Add …`, `Fix …`, `Update …`)
- Summarize the full staged set accurately (feature / fix / refactor / chore)

If commit fails due to a hook, **fix the issue and create a NEW commit**
(do not `--amend` unless the amend safety rules below all pass).

If there is nothing to commit but the branch is ahead of remote, skip commit
and still push.

If clean and already synced with remote: say so; do not create an empty commit.

### 5. Push

```bash
git push -u origin HEAD
```

Use required permissions for network / git write as needed.

**Push safety:**

- Do **not** `git push --force` / `--force-with-lease` unless the user
  explicitly asked for a force push in the same message
- Do **not** force-push `main` / `master`
- Do **not** change git config
- Do **not** skip hooks (`--no-verify`) unless the user explicitly asked
- Do **not** use interactive flags (`-i`)

### Amend safety (rare)

Only `git commit --amend` when **all** are true:

1. User explicitly asked to amend, **or** the previous commit succeeded but a
   hook auto-modified files that must be included
2. HEAD was created by you in this conversation
3. Commit has **not** been pushed

Otherwise make a new commit.

## Multi-repo summary

After all repos are done, report briefly:

```
/push
- repo-name: committed <sha> — <subject> → pushed <branch>
- other-repo: nothing to commit; pushed N commits
- other-repo: already up to date with origin
```

Include the GitHub compare / repo URL when useful.

## Rules

- `/push` means commit **and** push — both steps
- Process every dirty workspace repo, not just the first one
- Never commit secrets
- Never force-push unless explicitly requested
- Keep the final chat reply short
