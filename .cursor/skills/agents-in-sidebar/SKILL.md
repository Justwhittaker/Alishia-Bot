---
name: agents-in-sidebar
description: >-
  Ensures every custom Cursor agent is saved under .cursor/agents/ so it appears
  in the Agents sidebar, then committed to git. Use when creating, updating,
  moving, or reviewing subagents/agents, or when the user mentions agents,
  sidebar, or committing agents.
---

# Agents in Sidebar + Git

## Rule

**All agents are added in sidebar and committed to git.**

That means:

1. Every custom agent lives in **`.cursor/agents/*.md`** (project scope).
2. Never leave agents only in `~/.cursor/agents/` for this repo — copy or create them under `.cursor/agents/` so they show in the project Agents sidebar and can be versioned.
3. After creating or changing any agent file, **commit it to git** (unless the user explicitly says not to).

## When this skill applies

- Creating a new subagent / agent
- Editing an existing agent prompt
- User asks to “add an agent”, “put agents in the sidebar”, or “commit agents”
- Auditing that agents are discoverable and shared via the repo

## Workflow

Copy this checklist and complete it:

```
Agent Progress:
- [ ] Agent written to .cursor/agents/<name>.md
- [ ] Valid YAML frontmatter (name + description)
- [ ] File appears under project Agents sidebar path
- [ ] git add + commit (and push only if user asks)
```

### 1. Create or update the agent file

```bash
mkdir -p .cursor/agents
```

Write `.cursor/agents/<name>.md`:

```markdown
---
name: example-agent
description: When to use this agent. Be specific; include trigger terms.
---

System prompt body for the agent.
```

Requirements:

- Filename: lowercase letters, numbers, hyphens; ends in `.md`
- Frontmatter `name` matches the filename stem
- `description` explains when to delegate to this agent

### 2. Confirm sidebar location

Agents show in the sidebar when they exist as project files:

| Path | Sidebar | Git |
|------|---------|-----|
| `.cursor/agents/` | Yes (project) | Commit these |
| `~/.cursor/agents/` | Personal only | Do not use as the only copy for this repo |

If an agent exists only under `~/.cursor/agents/`, copy it into `.cursor/agents/` and commit the project copy.

### 3. Commit to git

After any agent create/update:

```bash
git status
git add .cursor/agents/
git commit -m "$(cat <<'EOF'
Add Cursor agents for sidebar discovery.

Keep project agents under .cursor/agents so they appear in the Agents sidebar and stay versioned.
EOF
)"
```

Commit message style:

- New agent: `Add <name> agent to .cursor/agents`
- Update: `Update <name> agent prompt`
- Multiple: `Add Cursor agents for sidebar discovery`

Do **not** push unless the user asks.

### 4. Optional: commit this skill with agents

When adding the skill itself or batching agent + skill changes, include:

```bash
git add .cursor/skills/agents-in-sidebar/ .cursor/agents/
```

## Anti-patterns

- Creating agents only in chat without writing `.cursor/agents/<name>.md`
- Storing repo agents solely in `~/.cursor/agents/`
- Leaving agent files untracked / uncommitted
- Putting agents under `.cursor/skills/` (skills ≠ agents)

## Related

- Subagent format details: follow Cursor’s create-subagent conventions (`name`, `description`, markdown body)
- Skills live in `.cursor/skills/`; agents live in `.cursor/agents/`
