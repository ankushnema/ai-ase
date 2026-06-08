# Dashboard — Design Document

## Purpose

Show developers what's wrong with their code, why, how to fix it, and whether they can commit. Two output modes:
- **CLI**: Grouped-by-rule violations with fix guidance, trust score with confidence
- **HTML**: Standalone dark-themed report with SVG gauge, per-file violations, active rules

## Problem

- A developer runs a scan and gets raw violations — no grouping, no context, no next step
- Trust score exists but without confidence indicator it's misleading (1/7 signals ≠ reliable)
- Warnings fire without context (H2 in dev isn't a problem, H2 in production is)
- All files treated equally (a failing TradeService.java is worse than a failing test helper)

## Solution

```
ai-ase dashboard                    # Terminal report (grouped by rule)
ai-ase dashboard --html report.html # HTML governance report
ai-ase dashboard --profile patch    # Profile-specific scan
```

## Data Model

```python
@dataclass
class DashboardData:
    session_id: str           # Correlation ID
    total_events: int         # Total JSONL lines parsed
    trust_scores: list[dict]  # [{timestamp, score, band}]
    policy_decisions: dict    # {allow: N, deny: N, escalate: N}
    violations_summary: dict  # {block: N, warn: N}
    tool_invocations: dict    # {tool_name: count}
    files_scanned: int        # Unique filenames in validation events
```

## Data Source

Reads `.ai-ase/audit-log.jsonl` — the same file written by MCP server tools (validate_code, check_policy, compute_trust_score, etc.).

### Event Types Consumed

| Event Type | What We Extract |
|------------|----------------|
| `trust_score` | score, band, timestamp → trust history chart |
| `policy_check` | decision (allow/deny/escalate) → decision breakdown |
| `validation` | filename, violations_found, decision → violation counts |
| All | tool_name → invocation counts |

## CLI Output

Uses Unicode box-drawing and block characters:
- `═` for headers, `─` for dividers
- `█` for filled bars, `░` for empty bars
- Truncates to last 10 trust scores for readability

## HTML Output

### Visual Design
- **Palette**: Tokyonight (bg `#1a1b26`, text `#c0caf5`)
- **Layout**: Single-column, card-based sections
- **Charts**: Inline SVG (trust score polyline) + CSS-only bars (policy/tools)
- **Typography**: Monospace (SF Mono / Fira Code / JetBrains Mono)

### Sections
1. **Header** — Session ID, event count, time range
2. **Violations Summary** — 4 stat cards (BLOCK, WARN, Files, Events)
3. **Trust Score History** — SVG polyline with band threshold lines
4. **Policy Decisions** — CSS horizontal bar chart
5. **Tool Invocations** — CSS horizontal bar chart
6. **Trust Score Timeline** — Table with time/score/band

### Trust Score Chart (SVG)
- Polyline connecting score points over time
- Horizontal dashed lines at thresholds (85, 70, 50)
- Color-coded dots: green (85+), blue (70+), yellow (50+), red (<50)
- No external library (pure SVG elements)

## Key Design Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Group by rule, not file | Developer sees 1 problem once, not 11 identical lines | Reduces noise, actionable |
| Trust score confidence | Show "low/medium/high" based on signals available | Prevents misleading "Excellent" with only 1/7 signals |
| Severity weighting | Service/Model 3x, Controller 2x, rest 1x | A failing TradeService is worse than a failing config |
| Profile-aware warnings | VR-62 (H2) only fires on migration | H2 is fine in dev, only problematic going to prod |
| WARN fix text shown | Each warning rule shows its fix guidance | Without it, developer can't act on warnings |
| SVG gauge (HTML) | Circular arc with glow, not a flat bar | Modern, instantly readable score visualization |
| No MCP audit in main view | Policy/tool data in separate audit log | Developer cares about code quality, not AI plumbing |

## CLI Output Structure

```
============================================================
  AI-ASE Governance Report
============================================================
  Profile: feature | Files: 44 | Status: FAIL
  Trust: 88/100 (low confidence, 1/7 signals)
  11 violations across 4 files must be fixed

BLOCKING (1 rule):
------------------------------------------------------------
  VR-05: Float/Double for Money (11 places, 4 files)
  Fix: Use BigDecimal for all monetary fields.
  Files:
    backend/.../Trade.java         lines 29, 36, 64
    backend/.../TradeService.java   lines 48, 55

WARNINGS (29 total, 3 rules, won't block):
  VR-39: REST Endpoint Without Metrics (24x)
       Add @Timed or @Counted (Micrometer) annotations.
  VR-25: console.log in Production (3x)
       Replace with structured logger (winston/pino).

------------------------------------------------------------
  Ready to commit: NO -- fix 11 BLOCK violations first
============================================================
```

## HTML Report Structure

1. **Status line** — PASS/FAIL, rule count, file count
2. **Progress bar** — X/Y files clean (Z%)
3. **Blocking section** — grouped by rule: risk (rationale), fix, file list
4. **Trust Score gauge** — SVG arc, confidence level, component breakdown, missing signals
5. **Warnings** — table grouped by rule with fix text
6. **Next step** — specific action to take

## Files

- `src/ai_ase/dashboard.py` — Parse + render logic (enrich_with_scan, render_cli, render_html)
- `tests/test_dashboard.py` — 27 tests
- `src/ai_ase/cli.py` — CLI integration (dashboard subcommand)