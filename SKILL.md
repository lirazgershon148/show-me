---
name: show-me
description: Render an interactive HTML X-ray of the user's Claude Code setup — global skills/agents/MCPs/hooks/plugins under ~/.claude/, project-level config under ./.claude/, project @-references from CLAUDE.md (with the actual content of those files), and override resolution between global and project. Produces a static HTML file with a Runwai-styled markmap visualization, filter buttons (All / Global / Project), and full content drill-down (each heading shows its literal section content). Trigger whenever the user wants to see "what's loaded", "what's active in my Claude Code", "x-ray my setup", "what overrides what", "show me my architecture", or simply says "show me" / "תראה לי" / "מה טעון אצלי" / "מה משפיע על התשובה" in a Claude Code context. Trigger even for casual mentions of wanting to visualize the setup, audit installed skills, see global-vs-project layers, or understand how plugins and MCPs combine — even if the user doesn't say "X-ray" or "show me" explicitly.
---

# show-me

A scan-and-render skill that produces an interactive HTML "X-ray" of the user's Claude Code configuration. It's like a CT scan for a Claude Code environment: see every layer (global, project, plugins), every file Claude touches via @-pointers, and the actual content inside those files — all in one navigable markmap.

## Why this exists

Claude Code's configuration lives across many layers — `~/.claude/CLAUDE.md`, project `CLAUDE.md`, skills (standalone + plugin-bundled), agents, MCP servers, hooks, settings, and `@`-referenced docs. Users lose track of what's actually loaded, what overrides what, and what the agent has access to *right now*. `show-me` translates the filesystem into a visual map.

## When to use

Use this skill whenever:
- The user says "show me", "תראה לי", "x-ray my setup", "מה טעון אצלי", "what's loaded", "what's active".
- The user wants to audit installed skills, agents, MCPs, or plugins.
- The user asks how global and project layers interact, or what overrides what.
- The user is debugging context — "why isn't this skill triggering?", "what's loaded in this project?".
- The user mentions visualizing, mapping, or seeing their Claude Code architecture.

If the user wants a one-off summary in chat, you can also output a text tree — but the primary deliverable is the HTML markmap.

## What this skill produces

A self-contained HTML file at `~/.claude/snapshots/show-me-<timestamp>.html`. Open with `open <path>`.

The HTML has:
- **Runwai-styled chrome** — toolbar (eyebrow + display headline + subtitle + filter buttons), legend with interaction hints, hairline borders, no drop shadows.
- **Filter buttons** — `All` / `Global` / `Project` — JS toggles which branches are visible.
- **Search input** — type to filter the tree to branches containing the query. Search composes with the active filter and prunes the tree so only matching nodes and their ancestor paths remain. Match count appears under the input. `Esc` clears.
- **Zoom controls** — small pill at bottom-right with `−` / FIT / `+`, wired to `mm.rescale()` and `mm.fit()`.
- **Keyboard shortcuts** — `+` / `=` zoom in, `-` zoom out, `0` fit, `/` focus search, `Esc` clear search. Shortcuts ignore typing inside the search input (so `/` and `-` work normally there).
- **Chips** — every section header (Skills · standalone, Plugins, Agents, MCP, etc.) carries a neutral hairline count chip indicating how many items expand from it. Project skills that collide with a global or plugin-bundled skill name show an amber `OVERRIDES GLOBAL` chip — visually distinct from the count chip so the warning state never gets confused with volume.
- **Markmap tree** — rendered via `markmap-lib` + `markmap-view` from a CDN (`jsdelivr`). Default expansion: 2 levels. Node click area is widened via JS event delegation (`HIT_RADIUS = 28`) without altering the visible circle, so markmap's native expand/collapse stroke encoding stays intact.
- **Deep project tree** — the Project file tree mirrors the IDE sidebar: recursive walk up to 6 levels, same names, same hierarchy. Every `.md` / `.mdx` file in the tree expands to its headings — nested by heading level so H2s sit under H1s, H3s under H2s, with the first content line of each section visible. Prose `.md` files without any headings show their first 5 non-blank lines as a preview, so even unstructured docs are drillable.

## Procedure

Three steps. The scripts handle the work; this file tells you when and how to invoke them.

### Step 1 — Scan

Run the scanner. It builds a JSON model of the user's setup:

```bash
python3 ~/.claude/skills/show-me/scripts/scan.py [project_dir]
```

- If `project_dir` is omitted, the scanner uses `$PWD`.
- Outputs JSON to stdout. Pipe to a file or directly to the renderer.

What the scanner reads:
- Global: `~/.claude/CLAUDE.md`, `~/.claude/skills/*/SKILL.md`, `~/.claude/agents/*.md`, `~/.claude/settings.json`.
- Plugins: enabled plugins listed in `~/.claude/settings.json` under `enabledPlugins`.
- Plugin-bundled skills: reads `~/.claude/plugins/installed_plugins.json` (the manifest) and, for each enabled plugin, walks its `installPath/skills/`. Each skill is tagged with `plugin_source` so the renderer can nest it under the parent plugin and the override detector can flag collisions.
- Project: `./CLAUDE.md`, `./.claude/skills/*/SKILL.md`, `./.claude/agents/*.md`, `./.claude/settings.local.json`.
- Project @-references: parses `./CLAUDE.md` for `@path/to/file.md` patterns, then reads each referenced file's headings and the first content line after each heading.
- Project tree: lists top-level directories and files in the project root.

### Step 2 — Render

Pipe the scan output into the renderer:

```bash
python3 ~/.claude/skills/show-me/scripts/scan.py [project_dir] | \
python3 ~/.claude/skills/show-me/scripts/render_html.py
```

Or combine in one call:

```bash
python3 -c "from scripts import scan, render_html; render_html.main(scan.scan())"
```

The renderer reads `assets/template.html` and substitutes:
- `{{headline}}` — the count summary (e.g., "16 global skills · 18 project skills · 5 project agents …")
- `{{markmap_md}}` — the markmap markdown content built from the scan model.

Output: `~/.claude/snapshots/show-me-<timestamp>.html` (creates the directory if missing).

### Step 3 — Open

```bash
open ~/.claude/snapshots/show-me-<timestamp>.html
```

Or on Linux: `xdg-open …`. The renderer prints the full path so the caller can chain it.

## Output format — markmap structure

The markmap is a tree with three top-level branches (these are what the filter buttons toggle):

```
# Claude Code · <user>

## ~/.claude/ — Global
### 📄 CLAUDE.md (lines, headings)
### 🔧 Skills · standalone <chip:N>
### 🧩 Plugins <chip:M> enabled <chip:K> plugin-bundled
  - **<plugin-name>** · <skill-count>
    - **<bundled-skill-name>**
      - description, body, refs
### 🤖 Agents · global <chip:K>
### 🔌 MCP servers · local <chip:P>
### 🪝 Hooks

## ./<project>/ — Project
### 📁 Project file tree (literal)
### 🔧 Skills · project-level <chip:N>
### 🤖 Agents · project-level <chip:K>
### ⚖️ Override resolution
```

For each skill, include its frontmatter `description` (first sentence) + 2-3 example triggers + any sub-reference files. For each @-referenced doc, include its literal headings (extracted via `grep -E "^#+ "`) and 2-3 lines of content under each heading. **Do not paraphrase** — the X-ray metaphor is broken if the output is curated.

## Strict translation rule

The X-ray must be a faithful translation of what exists, not a summary. Specifically:
- Use literal headings as they appear in the file (extract with `grep`).
- Show literal first lines of each section, not paraphrased summaries.
- If a file has no headings (prose document), state that explicitly and show the first line verbatim.
- Don't add commentary like "ux-mentor's contract" — the filename is the label.
- Don't add transient state like "currently open in IDE".
- Counts and stats are OK when literal (line count, file count); editorialized counts are not.

This rule exists because the user explicitly corrected an earlier paraphrased version. The skill exists to *show what's there*, not to interpret.

## Filter UI behavior

The HTML template ships with 3 buttons (`All`, `Global`, `Project`). `All` is active by default.

The filter is implemented in JS that mutates the markmap root's children:
- `All` → restore all children
- `Global` → keep only children whose content contains "global" or "x-ray"
- `Project` → keep only children whose content contains "project" or "x-ray"

The "🩻 Reading this X-ray" branch is always visible (filter ignores it) — it's meta-content, not scoped to a layer.

## Override detection

After scanning both global and project skills, the scanner flags any project skill whose name matches a global skill name. The markmap marks these with `← OVERRIDES global` next to the project skill name and dims (or de-emphasizes) the global version in the Override resolution section.

If no overrides exist, the Override resolution section simply lists the counts and notes "No name collisions."

## Where to look next

- `scripts/scan.py` — the scanner. Handles all filesystem reads and the model construction.
- `scripts/render_html.py` — the renderer. Builds the markmap markdown and substitutes into the template.
- `assets/template.html` — the HTML template (Runwai chrome + markmap-lib + filter JS).

## Versioning

- v1: initial release — static snapshot, English output, HTML only, scanned standalone skills only.
- v1.1 (2026-05-14 afternoon): plugin-bundled skills via `installed_plugins.json` manifest; chip-based count and override badges; visible zoom controls; JS-based widened node hit area (preserves markmap stroke); 12px Inter node text; removed the generic "🩻 Reading this X-ray" branch per the strict-translation rule.
- v1.2 (2026-05-16): search input that prunes the tree to matching branches (composes with the filter, shows match count, `Esc` clears); keyboard shortcuts (`+`/`-`/`0` zoom, `/` focus search, `Esc` clear); Hebrew + English labels for both.
- v1.3 (2026-05-16): search now visibly expands the path to each match — search prunes the tree in place on the original node references and toggles `initialExpandLevel` via `setOptions`, so deep matches no longer stay collapsed inside ancestor branches. Project file tree now goes deep, mirroring the IDE sidebar. Skips noise dirs (`node_modules`, `.git`, `.venv`, `dist`, `build`, `.next`, `.turbo`, `__pycache__`, `.cache`, `.pytest_cache`) but keeps `.claude/` and `.vscode/`.
- v1.4 (2026-05-16): tree depth bumped from 4 to 6 levels so deeply-nested projects render in full. Every `.md` / `.mdx` file in the tree now expands to its headings (first 12, with first content line per section) — same treatment as the root CLAUDE.md, via the existing `headings_and_sections` and `fmt_headings_with_content` helpers.
- v1.5 (2026-05-16): heading levels now drive markmap nesting — H2s under H1s, H3s under H2s — so the visual tree reflects the markdown structure. Prose `.md` files (no headings) fall back to a 5-line content preview so the leaf still surfaces real content, not nothing.
- v2 (deferred): live indicator (which skills are *actually* loaded in the current conversation), Excalidraw export, CLI text-tree fallback.
