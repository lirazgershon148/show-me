#!/usr/bin/env python3
"""
show-me renderer

Reads the scan model (from scan.py, either on stdin or by calling scan.scan()
directly) and produces a self-contained HTML file with a Runwai-styled
markmap visualization.

Output: ~/.claude/snapshots/show-me-<timestamp>.html
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote

SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = SCRIPT_DIR.parent / "assets" / "template.html"
SNAPSHOTS_DIR = Path.home() / ".claude" / "snapshots"


LABELS = {
    "en": {
        "dir": "ltr",
        "filter_all": "All",
        "filter_global": "Global",
        "filter_project": "Project",
        "global_branch": "~/.claude/ — Global",
        "project_branch": "./{project_name}/ — Project",
        "xray_branch": "🩻 Reading this X-ray",
        "claude_md_title": "📄 CLAUDE.md",
        "claude_md_units": "lines",
        "claude_md_headings_label": "headings",
        "claude_md_refs_label": "@-refs",
        "claude_md_missing": "📄 CLAUDE.md · not present",
        "skills_standalone": "🔧 Skills · standalone",
        "skills_project": "🔧 Skills · project-level",
        "plugins_label": "🧩 Plugins",
        "plugins_enabled_label": "enabled",
        "plugin_disabled": "disabled",
        "agents_global": "🤖 Agents · global",
        "agents_project": "🤖 Agents · project-level",
        "mcp_local": "🔌 MCP servers · local",
        "hooks_title": "🪝 Hooks",
        "hooks_none": "None configured",
        "project_tree_title": "📁 Project file tree",
        "content_referenced": "📚 Project content · @-referenced",
        "files_label": "files",
        "no_headings": "No headings — prose document",
        "first_line_label": "First line",
        "missing_marker": "(missing)",
        "override_title": "⚖️ Override resolution",
        "override_summary": "{g} global + {p} project = {t} skills in scope",
        "override_with": "{n} project skill(s) override global: {names}",
        "override_without": "No name collisions between global and project skills",
        "xray_loaded_every": "Loaded into every prompt",
        "xray_loaded_triggered": "Loaded only when triggered",
        "xray_not_loaded": "Not loaded at all",
        "claude_md_project_line": "Project CLAUDE.md ({lines} lines)",
        "claude_md_global_line": "Global CLAUDE.md ({lines} lines)",
        "skill_desc_line": "Skill descriptions (frontmatter only) — scanned at session start",
        "system_prompt_line": "The system prompt + tool definitions",
        "skill_bodies_line": "Skill bodies — {g} global + {p} project + plugin-bundled",
        "mcp_schemas_line": "MCP tool schemas — fetched on demand via ToolSearch",
        "skill_refs_line": "Skill reference files — read by the skill itself",
        "empty_global_claude_line": "Global CLAUDE.md (empty or missing)",
        "disabled_plugins_line": "Disabled plugins",
        "workspace_line": "skill-creator workspace artifacts",
        "skill_count_word": "global skills",
        "plugin_skill_count_word": "plugin-bundled",
        "project_skill_count_word": "project skills",
        "project_agent_count_word": "project agents",
        "global_agent_count_word": "global agents",
        "plugins_count_word": "plugins",
        "mcp_count_word": "MCP local",
        "overrides_count_word": "override(s)",
        "zoom_fit_label": "Fit",
        "search_placeholder": "Search…  (press / to focus)",
        "search_no_match": "No matches",
        "search_match_prefix": "",
        "search_match_suffix": " matches",
    },
    "he": {
        "dir": "rtl",
        "filter_all": "הכל",
        "filter_global": "גלובלי",
        "filter_project": "פרויקט",
        "global_branch": "~/.claude/ — גלובלי",
        "project_branch": "./{project_name}/ — פרויקט",
        "xray_branch": "🩻 קריאת הרנטגן",
        "claude_md_title": "📄 CLAUDE.md",
        "claude_md_units": "שורות",
        "claude_md_headings_label": "כותרות",
        "claude_md_refs_label": "@-references",
        "claude_md_missing": "📄 CLAUDE.md · לא קיים",
        "skills_standalone": "🔧 Skills · עצמאיים",
        "skills_project": "🔧 Skills · ברמת פרויקט",
        "plugins_label": "🧩 Plugins",
        "plugins_enabled_label": "מופעלים",
        "plugin_disabled": "מושבת",
        "agents_global": "🤖 Agents · גלובליים",
        "agents_project": "🤖 Agents · ברמת פרויקט",
        "mcp_local": "🔌 MCP servers · מקומיים",
        "hooks_title": "🪝 Hooks",
        "hooks_none": "אין hooks מוגדרים",
        "project_tree_title": "📁 עץ קבצי פרויקט",
        "content_referenced": "📚 תוכן פרויקט · @-references",
        "files_label": "קבצים",
        "no_headings": "אין כותרות — מסמך פרוזה",
        "first_line_label": "שורה ראשונה",
        "missing_marker": "(חסר)",
        "override_title": "⚖️ פתרון Override",
        "override_summary": "{g} גלובליים + {p} פרויקטליים = {t} skills בסקופ",
        "override_with": "{n} סקילים פרויקטליים דורסים גלובלי: {names}",
        "override_without": "אין התנגשות שמות בין גלובלי לפרויקט",
        "xray_loaded_every": "נטען בכל הודעה",
        "xray_loaded_triggered": "נטען רק כשנדרש",
        "xray_not_loaded": "לא נטען בכלל",
        "claude_md_project_line": "CLAUDE.md של הפרויקט ({lines} שורות)",
        "claude_md_global_line": "CLAUDE.md גלובלי ({lines} שורות)",
        "skill_desc_line": "תיאורי סקילים (frontmatter בלבד) — נסרקים בתחילת שיחה",
        "system_prompt_line": "ה-system prompt + הגדרות הכלים",
        "skill_bodies_line": "גוף הסקילים — {g} גלובליים + {p} פרויקטליים + plugin-bundled",
        "mcp_schemas_line": "סכמות של MCP — נטענות לפי דרישה דרך ToolSearch",
        "skill_refs_line": "קבצי reference של סקילים — נקראים ע\"י הסקיל עצמו",
        "empty_global_claude_line": "CLAUDE.md גלובלי (ריק או לא קיים)",
        "disabled_plugins_line": "Plugins מושבתים",
        "workspace_line": "תיקיות workspace של skill-creator",
        "skill_count_word": "סקילים גלובליים",
        "plugin_skill_count_word": "מצורפים לפלאגין",
        "project_skill_count_word": "סקילים פרויקטליים",
        "project_agent_count_word": "סוכני פרויקט",
        "global_agent_count_word": "סוכן גלובלי",
        "plugins_count_word": "plugins",
        "mcp_count_word": "MCP מקומי",
        "overrides_count_word": "overrides",
        "zoom_fit_label": "מרכז",
        "search_placeholder": "חיפוש…  (לחיצה על / להתמקדות)",
        "search_no_match": "אין תוצאות",
        "search_match_prefix": "",
        "search_match_suffix": " תוצאות",
    },
}


def first_sentence(text: str) -> str:
    if not text:
        return ""
    for sep in ". ", "! ", "? ":
        if sep in text:
            return text.split(sep, 1)[0].strip() + sep.strip()
    return text.strip()


def md_escape(s: str) -> str:
    """Light escape for markdown bullets — escape backslashes only, preserve
    code-style backticks (markmap renders inline code fine)."""
    return s.replace("\\", "\\\\")


def count_chip(n: int) -> str:
    return f'<span class="chip chip-count">{n}</span>'


def file_link(label: str, file_path: str | None) -> str:
    """Wrap a label in an anchor that opens the local file via file:// in a
    new browser tab. Falls back to plain escaped text when no path is given."""
    if not file_path:
        return md_escape(label)
    href = "file://" + quote(file_path)
    return f'<a href="{href}" target="_blank" class="open">{md_escape(label)}</a>'


def fmt_body_headings(headings: list[dict[str, Any]], indent: str,
                       max_top_headings: int = 12,
                       max_content_per_section: int = 4) -> list[str]:
    """Render a file's body headings as nested markmap bullets — each heading
    indented by its level relative to the file's top heading, so H2s nest
    under H1s, H3s under H2s, and section content nests under its heading."""
    lines: list[str] = []
    selected = headings[:max_top_headings]
    if not selected:
        return lines
    base_level = min(h["level"] for h in selected)
    for h in selected:
        depth = h["level"] - base_level
        h_indent = indent + ("  " * depth)
        hashes = "#" * h["level"]
        lines.append(f"{h_indent}- {hashes} {md_escape(h['text'])}")
        for content_line in h.get("content_lines", [])[:max_content_per_section]:
            if content_line.startswith("#"):
                continue
            lines.append(f"{h_indent}  - {md_escape(content_line)}")
    return lines


def fmt_skill(skill: dict[str, Any], indent: str, overrides: list[str]) -> list[str]:
    name = skill["name"]
    desc = first_sentence(skill.get("description", ""))
    refs = skill.get("refs", [])
    body_headings = skill.get("body_headings", [])
    refs_detail = skill.get("refs_detail", [])
    if name in overrides:
        suffix = ' <span class="chip chip-override">overrides global</span>'
    else:
        suffix = ""
    refs_label = ""
    if refs:
        refs_label = f" · *{len(refs)} refs: {', '.join(refs)}*"

    name_html = file_link(name, skill.get("file_path"))
    lines = [f"{indent}- **{name_html}**{suffix}{refs_label}"]
    if desc:
        lines.append(f"{indent}  - {md_escape(desc)}")
    if body_headings:
        lines.append(f"{indent}  - 📖 Body")
        lines.extend(fmt_body_headings(body_headings, indent + "    "))
    if refs_detail:
        lines.append(f"{indent}  - 📎 Refs ({len(refs_detail)})")
        for ref in refs_detail:
            ref_html = file_link(ref["filename"], ref.get("file_path"))
            lines.append(f"{indent}    - 📄 {ref_html}")
            if ref.get("headings"):
                lines.extend(fmt_body_headings(ref["headings"], indent + "      "))
            else:
                lines.append(f"{indent}      - No headings")
    return lines


def fmt_agent(agent: dict[str, Any], indent: str) -> list[str]:
    name = agent.get("name", agent.get("filename", "unknown"))
    desc = first_sentence(agent.get("description", ""))
    body_headings = agent.get("body_headings", [])
    name_html = file_link(name, agent.get("file_path"))
    lines = [f"{indent}- **{name_html}**"]
    if desc:
        lines.append(f"{indent}  - {md_escape(desc)}")
    if body_headings:
        lines.append(f"{indent}  - 📖 Body")
        lines.extend(fmt_body_headings(body_headings, indent + "    "))
    return lines


def fmt_tree_entries(entries: list[dict[str, Any]], indent: str = "") -> list[str]:
    """Recursive markmap render of the project file tree. Mirrors IDE
    sidebar shape: directories first (as expandable branches), then files.
    Markdown files expand to their headings using `fmt_headings_with_content`,
    same treatment as the project root CLAUDE.md."""
    out: list[str] = []
    for entry in entries:
        if entry["is_dir"]:
            out.append(f"{indent}- **📁 {md_escape(entry['name'])}/**")
            out.extend(fmt_tree_entries(entry.get("children", []), indent + "  "))
        else:
            name_html = file_link(entry["name"], entry.get("file_path"))
            out.append(f"{indent}- 📄 {name_html}")
            headings = entry.get("headings", [])
            preview = entry.get("preview_lines", [])
            if headings:
                out.extend(fmt_body_headings(headings, indent + "  "))
            elif preview:
                for line in preview:
                    out.append(f"{indent}  - {md_escape(line)}")
    return out


def fmt_headings_with_content(headings: list[dict[str, Any]], indent: str,
                               max_top_headings: int = 12,
                               max_content_per_section: int = 4) -> list[str]:
    """Alias for fmt_body_headings — kept for the CLAUDE.md / @-reference
    call sites so all three places get consistent heading-level nesting."""
    return fmt_body_headings(headings, indent, max_top_headings, max_content_per_section)


def build_headline(model: dict[str, Any], lang: str = "en") -> str:
    L = LABELS[lang]
    parts: list[str] = []
    parts.append(f"{len(model['global']['skills'])} {L['skill_count_word']}")
    plugin_skills_count = sum(len(v) for v in model["global"].get("plugin_skills", {}).values())
    if plugin_skills_count:
        parts.append(f"{plugin_skills_count} {L['plugin_skill_count_word']}")
    if model["project"]["skills"]:
        parts.append(f"{len(model['project']['skills'])} {L['project_skill_count_word']}")
    parts.append(f"{len(model['project']['agents'])} {L['project_agent_count_word']}")
    if model["global"]["agents"]:
        parts.append(f"{len(model['global']['agents'])} {L['global_agent_count_word']}")
    plugins = model["global"]["settings"].get("enabled_plugins", [])
    if plugins:
        parts.append(f"{len(plugins)} {L['plugins_count_word']}")
    mcp = model["global"]["settings"].get("mcp_servers", [])
    if mcp:
        parts.append(f"{len(mcp)} {L['mcp_count_word']}")
    if model["overrides"]:
        parts.append(f"{len(model['overrides'])} {L['overrides_count_word']}")
    return " · ".join(parts)


def build_markmap_md(model: dict[str, Any], lang: str = "en") -> str:
    L = LABELS[lang]
    user = model["user"]
    project_name = model["project_name"]
    overrides = model["overrides"]
    g = model["global"]
    p = model["project"]

    lines: list[str] = []
    lines.append(f"# Claude Code · {md_escape(user)}")
    lines.append("")

    # ── Global ──
    lines.append(f"## {L['global_branch']}")
    lines.append("")

    g_claude = g["claude_md"]
    if g_claude["exists"]:
        g_title = file_link(L['claude_md_title'], g_claude.get("path"))
        lines.append(
            f"### {g_title} · {g_claude['lines']} {L['claude_md_units']} · "
            f"{len(g_claude['headings'])} {L['claude_md_headings_label']}"
        )
        lines.extend(fmt_headings_with_content(g_claude["headings"], indent=""))
    else:
        lines.append(f"### {L['claude_md_missing']}")
    lines.append("")

    lines.append(f"### {L['skills_standalone']} {count_chip(len(g['skills']))}")
    for skill in g["skills"]:
        lines.extend(fmt_skill(skill, indent="", overrides=overrides))
    lines.append("")

    plugins = g["settings"].get("enabled_plugins", [])
    disabled = g["settings"].get("disabled_plugins", [])
    plugin_skills = g.get("plugin_skills", {})
    total_plugin_skills = sum(len(v) for v in plugin_skills.values())
    if plugins or disabled:
        header = f"### {L['plugins_label']} {count_chip(len(plugins))} {L['plugins_enabled_label']}"
        if total_plugin_skills:
            header += f" {count_chip(total_plugin_skills)} {L['plugin_skill_count_word']}"
        lines.append(header)
        for plug_key in plugins:
            plug_name = plug_key.split("@", 1)[0]
            skills = plugin_skills.get(plug_name, [])
            count_suffix = f" · {len(skills)}" if skills else ""
            lines.append(f"- **{md_escape(plug_key)}**{count_suffix}")
            for skill in skills:
                lines.extend(fmt_skill(skill, indent="  ", overrides=overrides))
        for plug in disabled:
            lines.append(f"- 🚫 **{md_escape(plug)}** *({L['plugin_disabled']})*")
        lines.append("")

    if g["agents"]:
        lines.append(f"### {L['agents_global']} {count_chip(len(g['agents']))}")
        for agent in g["agents"]:
            lines.extend(fmt_agent(agent, indent=""))
        lines.append("")

    mcp = g["settings"].get("mcp_servers", [])
    if mcp:
        lines.append(f"### {L['mcp_local']} {count_chip(len(mcp))}")
        for srv in mcp:
            lines.append(f"- **{md_escape(srv)}**")
        lines.append("")

    hooks = g["settings"].get("hooks", [])
    lines.append(f"### {L['hooks_title']}")
    if hooks:
        for h in hooks:
            lines.append(f"- {md_escape(h)}")
    else:
        lines.append(f"- {L['hooks_none']}")
    lines.append("")

    # ── Project ──
    lines.append(f"## {L['project_branch'].format(project_name=project_name)}")
    lines.append("")

    if p["tree"]:
        lines.append(f"### {L['project_tree_title']}")
        lines.extend(fmt_tree_entries(p["tree"]))
        lines.append("")

    p_claude = p["claude_md"]
    if p_claude["exists"]:
        p_title = file_link(L['claude_md_title'], p_claude.get("path"))
        lines.append(
            f"### {p_title} · {p_claude['lines']} {L['claude_md_units']} · "
            f"{len(p_claude['headings'])} {L['claude_md_headings_label']} · "
            f"{len(p_claude['at_references'])} {L['claude_md_refs_label']}"
        )
        lines.extend(fmt_headings_with_content(p_claude["headings"], indent=""))
        lines.append("")

    if p["at_references"]:
        lines.append(f"### {L['content_referenced']} {count_chip(len(p['at_references']))} {L['files_label']}")
        for ref in p["at_references"]:
            ref_name = ref["ref"]
            if not ref["exists"]:
                lines.append(f"- **@{md_escape(ref_name)}** *{L['missing_marker']}*")
                continue
            ref_html = file_link("@" + ref_name, ref.get("path"))
            lines.append(f"- **{ref_html}**")
            if ref.get("is_prose"):
                lines.append(f"  - {L['no_headings']}")
                if ref.get("first_line"):
                    lines.append(f"  - {L['first_line_label']}: *{md_escape(ref['first_line'])}*")
            else:
                for h in ref.get("headings", [])[:12]:
                    hashes = "#" * h["level"]
                    lines.append(f"  - {hashes} {md_escape(h['text'])}")
                    for content_line in h.get("content_lines", [])[:4]:
                        if content_line.startswith("#"):
                            continue
                        lines.append(f"    - {md_escape(content_line)}")
        lines.append("")

    if p["skills"]:
        lines.append(f"### {L['skills_project']} {count_chip(len(p['skills']))}")
        for skill in p["skills"]:
            lines.extend(fmt_skill(skill, indent="", overrides=overrides))
        lines.append("")

    if p["agents"]:
        lines.append(f"### {L['agents_project']} {count_chip(len(p['agents']))}")
        for agent in p["agents"]:
            lines.extend(fmt_agent(agent, indent=""))
        lines.append("")

    lines.append(f"### {L['override_title']}")
    lines.append(f"- {L['override_summary'].format(g=len(g['skills']), p=len(p['skills']), t=len(g['skills']) + len(p['skills']))}")
    if overrides:
        lines.append(f"- {L['override_with'].format(n=len(overrides), names=', '.join(overrides))}")
    else:
        lines.append(f"- {L['override_without']}")
    lines.append("")

    return "\n".join(lines)


def render(model: dict[str, Any], lang: str = "en", output_path: Path | None = None) -> Path:
    if lang not in LABELS:
        lang = "en"
    L = LABELS[lang]
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    headline = build_headline(model, lang)
    timestamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    markmap_md = build_markmap_md(model, lang)

    replacements = {
        "{{DIR}}": L["dir"],
        "{{PROJECT_NAME}}": model["project_name"],
        "{{HEADLINE}}": headline,
        "{{STAMP_DATE}}": timestamp,
        "{{FILTER_ALL}}": L["filter_all"],
        "{{FILTER_GLOBAL}}": L["filter_global"],
        "{{FILTER_PROJECT}}": L["filter_project"],
        "{{ZOOM_FIT_LABEL}}": L["zoom_fit_label"],
        "{{SEARCH_PLACEHOLDER}}": L["search_placeholder"],
        "{{SEARCH_NO_MATCH}}": L["search_no_match"],
        "{{SEARCH_MATCH_PREFIX}}": L["search_match_prefix"],
        "{{SEARCH_MATCH_SUFFIX}}": L["search_match_suffix"],
        "{{MARKMAP_MD}}": markmap_md,
    }
    html = template
    for placeholder, value in replacements.items():
        html = html.replace(placeholder, value)

    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    if output_path is None:
        suffix = "-he" if lang == "he" else ""
        filename = f"show-me{suffix}-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}.html"
        output_path = SNAPSHOTS_DIR / filename
    output_path.write_text(html, encoding="utf-8")
    return output_path


def main() -> None:
    # Parse args: optional --lang=he and optional project_dir
    lang = "en"
    project_dir = None
    for arg in sys.argv[1:]:
        if arg.startswith("--lang="):
            lang = arg.split("=", 1)[1].strip().lower()
        elif not arg.startswith("-"):
            project_dir = arg

    if not sys.stdin.isatty():
        model = json.load(sys.stdin)
    else:
        sys.path.insert(0, str(SCRIPT_DIR))
        import scan as scan_module  # type: ignore
        model = scan_module.scan(project_dir)

    output_path = render(model, lang=lang)
    print(str(output_path))


if __name__ == "__main__":
    main()
