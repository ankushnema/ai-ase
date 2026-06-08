# Dashboard

## Purpose

`dashboard.py` is the developer-facing report surface. Two output modes:

- **CLI** — terminal output grouped by rule, with fix guidance and trust score + confidence.
- **HTML** — standalone dark-themed report with SVG trust gauge, per-file violations, active rules.

Reads `.ai-ase/audit-log.jsonl` + `.ai-ase/findings.json`. Writes nothing back. Pure consumer.

## CLI invocations

```bash
ai-ase dashboard                              # terminal report
ai-ase dashboard --html report.html           # HTML file
ai-ase dashboard --profile patch              # profile-scoped scan
ai-ase dashboard --since 2026-06-01           # only events after date
```

## Data model

```python
@dataclass
class DashboardData:
    session_id: str
    profile: str
    total_events: int
    trust_scores: list[dict]          # [{ts, score, band, confidence}]
    policy_decisions: dict            # {"allow": N, "deny": N, "escalate": N}
    violations_summary: dict          # {"block": N, "warn": N, "by_rule": {...}}
    tool_invocations: dict            # {tool_name: count}
    files_scanned: int
    files_with_violations: list[dict] # [{file, blocks, warns}]
    phases_completed: list[str]
    corrections_added: list[dict]     # CAR rule additions
```

## Public interface

```python
def build_data(*, since: datetime | None = None, profile: str | None = None) -> DashboardData: ...

def render_cli(data: DashboardData) -> str: ...

def render_html(data: DashboardData) -> str: ...
```

## CLI output structure

```
============================================================
  AI-ASE Governance Report
============================================================
  Profile: feature | Files: 44 | Status: FAIL
  Trust: 82/100 (medium confidence, 4/7 signals) ▓▓▓▓▓▓▓▓░░
  11 violations across 4 files must be fixed before commit
============================================================

  Violations by rule (grouped, with fix):

  ▶ VR-10 (BLOCK, critical) — 3 hits
    Float used for monetary value
    Fix: Use Decimal (Python) / BigDecimal (Java)
    Files:
      src/charges/refund_service.py:42
      src/charges/refund_service.py:67
      src/billing/invoice.py:118

  ▶ VR-22 (WARN, medium) — 8 hits
    Hardcoded timeout
    Fix: Move to configuration
    ...

============================================================
  Trust score history (last 10)
============================================================
   85 ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░  excellent  10:00
   82 ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░  good       10:15
   78 ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░  good       10:30
   ...

============================================================
  Policy decisions: 41 allow | 3 deny | 0 escalate
  Tool calls: validate_code(28) get_active_rules(12) ...
============================================================
```

Uses Unicode box-drawing (`═`, `─`, `▓`, `░`) for readability. No ANSI color in MVP (terminals vary too much); add color in a follow-up.

## HTML output

### Design tokens

```
Background:  #1a1b26  (tokyonight bg)
Surface:     #24283b
Text:        #c0caf5
Muted:       #565f89
Accent:      #7aa2f7  (blue)
Success:     #9ece6a  (green)
Warning:     #e0af68  (yellow)
Danger:      #f7768e  (red)
Font:        SF Mono, Fira Code, JetBrains Mono, monospace
```

### Sections (single column)

1. **Header** — session ID, profile, time range, event count.
2. **Trust gauge** — circular SVG arc, 0–100, colored by band.
3. **Violations summary** — 4 stat cards (BLOCK, WARN, Files, Events).
4. **Violations grouped by rule** — per-rule card with fix text, file list.
5. **Trust score history** — inline SVG polyline with dashed threshold lines at 85/70/50.
6. **Policy decisions** — CSS horizontal bar chart.
7. **Tool invocations** — CSS horizontal bar chart.
8. **CAR rule additions** — table of rules added during this period.
9. **Full timeline** — `<details>` collapsed by default.

### SVG trust gauge

```html
<svg viewBox="0 0 200 200" width="200" height="200">
  <circle cx="100" cy="100" r="80" fill="none" stroke="#24283b" stroke-width="16"/>
  <path d="M 100 20 A 80 80 0 {large} {sweep} {x} {y}"
        fill="none" stroke="{color}" stroke-width="16" stroke-linecap="round"/>
  <text x="100" y="105" text-anchor="middle" font-size="36" fill="#c0caf5">{score}</text>
  <text x="100" y="135" text-anchor="middle" font-size="14" fill="#565f89">{band}</text>
</svg>
```

`color` derives from band; `x`, `y`, `large`, `sweep` are arc parameters as a function of score/100.

### SVG trust history

```html
<svg viewBox="0 0 600 200" preserveAspectRatio="none">
  <line x1="0" y1="40"  x2="600" y2="40"  stroke="#565f89" stroke-dasharray="4 4"/>   <!-- 85 -->
  <line x1="0" y1="80"  x2="600" y2="80"  stroke="#565f89" stroke-dasharray="4 4"/>   <!-- 70 -->
  <line x1="0" y1="120" x2="600" y2="120" stroke="#565f89" stroke-dasharray="4 4"/>   <!-- 50 -->
  <polyline points="{x1,y1 x2,y2 ...}" fill="none" stroke="#7aa2f7" stroke-width="2"/>
  <circle cx="{x}" cy="{y}" r="3" fill="{color_by_band}"/>  <!-- one per point -->
</svg>
```

No external chart library. Single file. Email-able.

## Confidence indicator

Trust score is meaningless without confidence. Show:

```
Trust: 82/100 (medium confidence, 4/7 signals)
```

CLI: parenthetical after score.
HTML: badge next to the score, colored by confidence level.

## Severity weighting (post-MVP nice-to-have)

A failing `TradeService.java` is worse than a failing config file. Weighting:

| Pattern | Weight |
|---|---|
| `*Service*`, `*Model*`, `*Entity*`, `*Aggregate*` | 3× |
| `*Controller*`, `*Resource*`, `*Endpoint*` | 2× |
| everything else | 1× |

Applied to the "violations by file" sort order. MVP can skip; surface as a follow-up.

## Profile-aware WARN handling

Some WARN rules only make sense in some profiles. Example: `VR-62 (H2 database)` should only fire on `migration`, not on `feature` (H2 is fine in dev). The dashboard respects the rule's `profiles:` list; if the active profile isn't in the list, the violation is suppressed.

## Tests (target ≥ 15)

- `build_data()` reads audit events correctly.
- Empty audit → dashboard renders with zeros, doesn't crash.
- CLI output contains rule IDs as headers (grouping).
- HTML output is valid (parseable).
- HTML output contains exactly one trust gauge SVG.
- HTML output is self-contained (no external `<link>` / `<script src>`).
- Confidence indicator reflects signal count.
- `--since` filter excludes earlier events.

## Anti-patterns

| Don't | Because |
|---|---|
| Render with a JS chart library | Self-contained > pretty. Email-able. |
| Mix HTML and CLI generation logic | Separate `render_html` and `render_cli`. Same data, different surfaces. |
| Hide WARN fix guidance | Without it, the developer can't act on warnings — they just become noise. |
| Show trust score without confidence | Misleading. |

## Ground truth

[artifacts/dashboard-design.md](../artifacts/dashboard-design.md) is the design doc this spec implements.