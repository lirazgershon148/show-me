#!/usr/bin/env python3
"""
show-me scanner

Reads the user's Claude Code setup and builds a JSON model dict that the
renderer turns into a markmap. Strict translation: literal headings and
literal content lines — no paraphrase.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any


HOME = Path.home()
GLOBAL_CLAUDE = HOME / ".claude"

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)
HEADING_RE = re.compile(r"^(#+)\s+(.+?)\s*$")
AT_REF_RE = re.compile(r"@([A-Za-z0-9_./\-]+)")


def read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def parse_frontmatter(text: str) -> dict[str, str]:
    """Parse minimal YAML frontmatter for `name:` and `description:`. Supports
    a leading `>` block-scalar marker on description."""
    m = FRONTMATTER_RE.search(text)
    if not m:
        return {}
    body = m.group(1)
    out: dict[str, str] = {}
    current_key: str | None = None
    block_lines: list[str] = []
    block_indent: int | None = None

    for raw_line in body.split("\n"):
        if current_key and (raw_line.startswith("  ") or raw_line.startswith("\t")):
            # continuation of block scalar
            stripped = raw_line.lstrip()
            if block_indent is None:
                block_indent = len(raw_line) - len(stripped)
            block_lines.append(stripped)
            continue
        if current_key and block_lines:
            out[current_key] = " ".join(s for s in block_lines if s).strip()
            current_key, block_lines, block_indent = None, [], None
        if ":" in raw_line:
            key, _, value = raw_line.partition(":")
            key = key.strip()
            value = value.strip()
            if value == ">" or value == "|":
                current_key = key
                block_lines = []
                block_indent = None
            else:
                out[key] = value
    if current_key and block_lines:
        out[current_key] = " ".join(s for s in block_lines if s).strip()
    return out


def strip_frontmatter(text: str) -> str:
    """Remove a leading YAML frontmatter block (--- ... ---) if present."""
    m = FRONTMATTER_RE.search(text)
    if m and m.start() == 0:
        return text[m.end():]
    return text


def headings_and_sections(text: str, max_lines_per_section: int = 4) -> list[dict[str, Any]]:
    """Return [{level, text, content_lines}] in document order.
    content_lines = up to N literal first lines under the heading
    (skips blanks and fenced code blocks)."""
    out: list[dict[str, Any]] = []
    in_code = False
    current: dict[str, Any] | None = None
    for raw_line in text.split("\n"):
        if raw_line.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        m = HEADING_RE.match(raw_line)
        if m:
            if current is not None:
                out.append(current)
            level = len(m.group(1))
            current = {"level": level, "text": m.group(2), "content_lines": []}
            continue
        if current is not None and len(current["content_lines"]) < max_lines_per_section:
            stripped = raw_line.strip()
            if stripped:
                current["content_lines"].append(stripped)
    if current is not None:
        out.append(current)
    return out


def scan_skill_dir(skill_dir: Path) -> dict[str, Any] | None:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return None
    text = read_text(skill_md) or ""
    fm = parse_frontmatter(text)
    body = strip_frontmatter(text)
    body_headings = headings_and_sections(body)

    # Reference files: every .md in the skill dir other than SKILL.md
    ref_files = sorted(
        p for p in skill_dir.iterdir()
        if p.is_file() and p.suffix == ".md" and p.name != "SKILL.md"
    )
    refs_detail: list[dict[str, Any]] = []
    for ref_path in ref_files:
        ref_text = read_text(ref_path) or ""
        refs_detail.append({
            "filename": ref_path.name,
            "file_path": str(ref_path),
            "headings": headings_and_sections(ref_text),
        })

    return {
        "name": fm.get("name", skill_dir.name),
        "description": fm.get("description", "").strip(),
        "file_path": str(skill_md),
        "refs": [r["filename"] for r in refs_detail],
        "body_headings": body_headings,
        "refs_detail": refs_detail,
    }


def scan_skills_dir(skills_root: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not skills_root.exists() or not skills_root.is_dir():
        return out
    for d in sorted(skills_root.iterdir()):
        if not d.is_dir():
            continue
        if d.name.endswith("-workspace"):
            continue
        meta = scan_skill_dir(d)
        if meta:
            out.append(meta)
    return out


def scan_plugin_skills(manifest_path: Path, enabled_plugin_keys: list[str]) -> dict[str, list[dict[str, Any]]]:
    """Read ~/.claude/plugins/installed_plugins.json and, for each enabled
    plugin, walk its installPath/skills/ via scan_skills_dir. Returns
    {plugin_display_name: [skill_dicts]} keyed by the bare plugin name
    (the part before '@marketplace' in enabledPlugins keys)."""
    out: dict[str, list[dict[str, Any]]] = {}
    if not manifest_path.exists():
        return out
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return out
    installs = manifest.get("plugins", {}) if isinstance(manifest, dict) else {}
    for key in enabled_plugin_keys:
        entries = installs.get(key)
        if not entries or not isinstance(entries, list):
            continue
        install_path = entries[0].get("installPath") if isinstance(entries[0], dict) else None
        if not install_path:
            continue
        skills_dir = Path(install_path) / "skills"
        skills = scan_skills_dir(skills_dir)
        if not skills:
            continue
        plugin_name = key.split("@", 1)[0]
        for s in skills:
            s["plugin_source"] = plugin_name
        out[plugin_name] = skills
    return out


def scan_agents_dir(agents_root: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not agents_root.exists() or not agents_root.is_dir():
        return out
    for f in sorted(agents_root.iterdir()):
        if not f.is_file() or f.suffix != ".md":
            continue
        text = read_text(f) or ""
        fm = parse_frontmatter(text)
        body = strip_frontmatter(text)
        out.append({
            "name": fm.get("name", f.stem),
            "description": fm.get("description", "").strip(),
            "filename": f.name,
            "file_path": str(f),
            "body_headings": headings_and_sections(body),
        })
    return out


def scan_settings(settings_path: Path) -> dict[str, Any]:
    out: dict[str, Any] = {"hooks": [], "mcp_servers": [], "enabled_plugins": [], "disabled_plugins": []}
    if not settings_path.exists():
        return out
    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return out
    if isinstance(data.get("hooks"), dict):
        out["hooks"] = sorted(data["hooks"].keys())
    if isinstance(data.get("mcpServers"), dict):
        out["mcp_servers"] = sorted(data["mcpServers"].keys())
    plugins = data.get("enabledPlugins") or {}
    if isinstance(plugins, dict):
        for name, enabled in plugins.items():
            (out["enabled_plugins"] if enabled else out["disabled_plugins"]).append(name)
        out["enabled_plugins"].sort()
        out["disabled_plugins"].sort()
    return out


def parse_at_references(text: str) -> list[str]:
    """Find @path/to/file.md references in markdown text (deduped, ordered)."""
    seen: set[str] = set()
    out: list[str] = []
    for m in AT_REF_RE.finditer(text):
        ref = m.group(1)
        if not (ref.endswith(".md") or ref.endswith(".json")):
            continue
        if ref in seen:
            continue
        seen.add(ref)
        out.append(ref)
    return out


def scan_claude_md(path: Path) -> dict[str, Any]:
    out: dict[str, Any] = {"path": str(path), "exists": path.exists(), "lines": 0,
                           "headings": [], "at_references": []}
    if not path.exists():
        return out
    text = read_text(path) or ""
    out["lines"] = len(text.splitlines())
    out["headings"] = headings_and_sections(text)
    out["at_references"] = parse_at_references(text)
    return out


def scan_referenced_file(path: Path) -> dict[str, Any]:
    out: dict[str, Any] = {"path": str(path), "exists": path.exists(),
                           "is_prose": False, "first_line": "", "headings": []}
    if not path.exists():
        return out
    text = read_text(path) or ""
    headings = headings_and_sections(text)
    if not headings:
        out["is_prose"] = True
        for line in text.split("\n"):
            stripped = line.strip()
            if stripped:
                out["first_line"] = stripped
                break
    else:
        out["headings"] = headings
    return out


TREE_SKIP_DIRS = {
    "node_modules", ".git", ".venv", "venv", "dist", "build",
    ".next", ".turbo", "__pycache__", ".cache", ".pytest_cache",
}

MARKDOWN_SUFFIXES = {".md", ".mdx"}


def scan_project_tree(root: Path, max_depth: int = 6, max_per_dir: int = 60) -> list[dict[str, Any]]:
    """Recursive literal file tree, dirs-first then files (alphabetical).
    Mirrors what the user sees in their IDE sidebar. Skips well-known noise
    directories but keeps hidden ones the user works with (.claude/, .vscode/,
    etc.). Each entry: {name, is_dir, children: [entries]}; files have no
    children key."""
    if not root.exists():
        return []

    def walk(path: Path, depth: int) -> list[dict[str, Any]]:
        if depth > max_depth:
            return []
        try:
            kids = sorted(
                (c for c in path.iterdir() if c.name != ".DS_Store"),
                key=lambda p: (not p.is_dir(), p.name.lower()),
            )[:max_per_dir]
        except OSError:
            return []
        out: list[dict[str, Any]] = []
        for child in kids:
            entry: dict[str, Any] = {"name": child.name, "is_dir": child.is_dir()}
            if not child.is_dir():
                entry["file_path"] = str(child)
            if child.is_dir():
                if child.name in TREE_SKIP_DIRS:
                    entry["children"] = []
                else:
                    entry["children"] = walk(child, depth + 1)
            elif child.suffix.lower() in MARKDOWN_SUFFIXES:
                text = read_text(child) or ""
                headings = headings_and_sections(text)
                if headings:
                    entry["headings"] = headings
                else:
                    preview: list[str] = []
                    for line in text.split("\n"):
                        stripped = line.strip()
                        if stripped and not stripped.startswith("```"):
                            preview.append(stripped)
                            if len(preview) >= 5:
                                break
                    if preview:
                        entry["preview_lines"] = preview
            out.append(entry)
        return out

    return walk(root, 1)


def scan(project_dir: str | None = None) -> dict[str, Any]:
    project_root = Path(project_dir).resolve() if project_dir else Path.cwd()

    # Global
    global_claude_md = scan_claude_md(GLOBAL_CLAUDE / "CLAUDE.md")
    global_skills = scan_skills_dir(GLOBAL_CLAUDE / "skills")
    global_agents = scan_agents_dir(GLOBAL_CLAUDE / "agents")
    global_settings = scan_settings(GLOBAL_CLAUDE / "settings.json")
    global_plugin_skills = scan_plugin_skills(
        GLOBAL_CLAUDE / "plugins" / "installed_plugins.json",
        global_settings["enabled_plugins"],
    )

    # Project
    project_claude_md = scan_claude_md(project_root / "CLAUDE.md")
    project_skills = scan_skills_dir(project_root / ".claude" / "skills")
    project_agents = scan_agents_dir(project_root / ".claude" / "agents")
    project_settings = scan_settings(project_root / ".claude" / "settings.local.json")

    # @-references
    refs: list[dict[str, Any]] = []
    for ref in project_claude_md.get("at_references", []):
        ref_path = project_root / ref
        info = scan_referenced_file(ref_path)
        info["ref"] = ref
        refs.append(info)

    # Tree
    tree = scan_project_tree(project_root)

    # Overrides — collide against standalone AND plugin-bundled global skills
    global_skill_names = {s["name"] for s in global_skills}
    for plug_skills in global_plugin_skills.values():
        global_skill_names |= {s["name"] for s in plug_skills}
    overrides = [s["name"] for s in project_skills if s["name"] in global_skill_names]

    return {
        "user": os.environ.get("USER", "user"),
        "project_root": str(project_root),
        "project_name": project_root.name,
        "global": {
            "claude_md": global_claude_md,
            "skills": global_skills,
            "plugin_skills": global_plugin_skills,
            "agents": global_agents,
            "settings": global_settings,
        },
        "project": {
            "claude_md": project_claude_md,
            "skills": project_skills,
            "agents": project_agents,
            "settings": project_settings,
            "at_references": refs,
            "tree": tree,
        },
        "overrides": overrides,
    }


def main() -> None:
    project_dir = sys.argv[1] if len(sys.argv) > 1 else None
    model = scan(project_dir)
    json.dump(model, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
