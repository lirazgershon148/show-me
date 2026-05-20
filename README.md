# show-me

Interactive mind map of your Claude Code setup — global + project skills, agents, MCPs, hooks. Still in beta.

## What it does

Scans your Claude Code configuration across every layer (`~/.claude/`, project `.claude/`, plugin-bundled skills, `@`-references in `CLAUDE.md`) and renders it as a navigable HTML markmap. Filter by Global / Project, search, drill down to literal headings and content inside each file.

## Install

Clone into your global skills directory:

```bash
git clone https://github.com/lirazgershon148/show-me.git ~/.claude/skills/show-me
```

Claude Code picks it up automatically — no further config.

## Use

Inside Claude Code, ask:

- "show me"
- "x-ray my setup"
- "תראה לי"
- "what's loaded"

Or run the scripts directly:

```bash
python3 ~/.claude/skills/show-me/scripts/scan.py | \
python3 ~/.claude/skills/show-me/scripts/render_html.py
```

Output lands at `~/.claude/snapshots/show-me-<timestamp>.html`.

## Status

Beta. See `SKILL.md` for full behavior and known gaps.
