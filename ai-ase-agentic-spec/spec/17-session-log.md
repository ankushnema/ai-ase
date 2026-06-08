# Session Log

## Purpose

`session_log.py` generates a per-session HTML record of everything that happened: phases, skills fired, files touched, decisions made, the audit log distilled into a human-readable timeline.

It is the **post-hoc forensic surface** of the framework. Six months after a change, the session log is what someone reads to understand what the AI and the human did, in what order, and why.

V2 (Transparency) made into a single file you can email.

## File location

`.ai-ase/sessions/<session-id>.html` (one file per session).

## Triggers

1. `session-log-management` skill fires on `session-start` — creates the empty log.
2. The same skill fires on `deliverable-created` — appends to the log.
3. `ai-ase session export <session-id>` — regenerates the HTML from audit events (idempotent).

## Public interface

```python
def create_session_log(session_id: str) -> Path: ...

def update_session_log(session_id: str) -> None: ...

def export(session_id: str, *, format: str = "html") -> Path: ...
    # format: "html" | "markdown"
```

## Algorithm: `export(session_id)`

```
1. events = audit.filter(session_id=session_id)        # iterator over audit entries
2. timeline = group_by_phase(events)
3. summary = build_summary(events)                     # counts, durations, decisions
4. trust_history = [e for e in events if e["event"] == "trust_score"]
5. files_touched = unique([e["file"] for e in events if "file" in e])
6. corrections = [e for e in events if e["event"] == "car_rule_added"]
7. html = render_template("session-log.html.tmpl", summary, timeline,
                          trust_history, files_touched, corrections)
8. path = Path(".ai-ase/sessions") / f"{session_id}.html"
9. path.parent.mkdir(parents=True, exist_ok=True)
10. path.write_text(html, encoding="utf-8")
11. return path
```

## HTML layout

Single self-contained file (no external CSS/JS). Sections, in order:

1. **Header** — session ID, profile, start/end timestamps, duration, final trust score.
2. **Summary** — counts: phases completed, files written, BLOCK violations, WARN violations, CAR rules added.
3. **Phase timeline** — for each phase: when it started/ended, who approved, what skills fired.
4. **Files touched** — table of file path × first write × last write × violations triggered.
5. **Decisions** — every BLOCK decision (file, rule, AI's response).
6. **Corrections** — every CAR rule added with the source diff.
7. **Trust history** — sparkline + table of every `trust_score` event.
8. **Full audit timeline** — collapsible JSONL excerpt.

Use semantic HTML (`<table>`, `<details>/<summary>`, `<time datetime="">`). No JavaScript required. Style with inline `<style>` using the tokyonight palette for visual consistency with the dashboard (see [19-DASHBOARD.md](../spec/19-dashboard.md)).

## Template location

`src/ai_ase/templates/session-log.html.tmpl`

The reference vendor doesn't ship this template (the implementation rendered inline). Build it from the section list above using semantic HTML and the tokyonight palette.

## Markdown export

For email-friendly logs:

```
ai-ase session export <session-id> --format markdown > session.md
```

Same data, simpler rendering. Sections become `##` headings, tables become Markdown tables. No images, no styling.

## Tests

- `create_session_log()` creates an empty file with correct frontmatter.
- `export()` is idempotent — same audit events produce identical output (assuming stable timestamps).
- Missing audit log produces a clear error, not a crash.
- Markdown export is valid CommonMark.
- HTML output passes basic well-formedness check.

## Anti-patterns

| Don't | Because |
|---|---|
| Stream-write the HTML as events occur | Regenerate from audit on each export. Idempotent. |
| Include credentials / file contents | Logs are circulated. Strip sensitive fields. |
| Require a browser-side library | Single-file HTML. Open it locally, email it, attach to a ticket. |
| Lose phase/skill cross-references | The log is for forensics. Show what fired, when, and why. |

## Ground truth

No vendored template ships with the reference implementation. Build from the section list and styling guidance above.