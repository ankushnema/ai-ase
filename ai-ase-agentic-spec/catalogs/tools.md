# Catalog — The 9 MCP Tools

Tools AI-ASE exposes via the Model Context Protocol. Any MCP-compatible AI IDE can call them.

**Why MCP?** One tool definition, many IDE consumers. The same `validate_code` tool the AI calls during a chat session is also invoked by the PreToolUse hook and the CLI scanner.

---

## At a glance

| # | Tool | Purpose | Reads from | Writes to |
|---|---|---|---|---|
| 1 | `validate_code` | Check code before write | rule catalog | — |
| 2 | `get_active_rules` | List rules applicable to file/profile | rule catalog | — |
| 3 | `governance_profile` | Detect risk level of a change | embedded regex | — |
| 4 | `check_business_rule` | Look up a single rule by ID | rule catalog | — |
| 5 | `compute_trust_score` | Compute trust 0-100 from signals | embedded weights | — |
| 6 | `get_skill` | Load a skill's instructions on demand | skill catalog | — |
| 7 | `report_generation` | Audit-trail entry for AI changes | — | `audit-log.jsonl` |
| 8 | `check_policy` | Permission check for a tool call | embedded tables | `policy-audit.jsonl` |
| 9 | `dry_run_preview` | Preview a tool call without executing | rule catalog | — |

---

## 1. `validate_code`

**Purpose.** Scan a code blob against the active rule catalog. Returns findings.

**Args:**
- `content: str` — the code to scan
- `path: str` (optional) — file path, used to filter rules by file type
- `profile: str` (default `feature`) — `patch` / `feature` / `migration` / `incident`

**Algorithm:**
1. Load rules; filter by `applies_to` matching the file type derived from `path`.
2. For each rule, run its regex against `content`. Collect matches.
3. Each match → `Finding { rule_id, severity, action, line, message, fix }`.
4. Sort by line. Group by severity.
5. Return: findings list + summary (`{ BLOCK: n, WARN: m }`).

**Output:** Markdown report. BLOCK findings appear first. Each finding has rule id, line, fix.

---

## 2. `get_active_rules`

**Purpose.** Show which rules would apply to a given file or profile. Used by the agent to "know what to look for" before writing.

**Args:**
- `path: str` (optional) — file path
- `profile: str` (default `feature`)

**Algorithm:**
1. Load rules.
2. Filter by `applies_to` (file type) and `profile` (some rules apply only in `migration`).
3. Return the filtered list as a compact table (id, name, action).

---

## 3. `governance_profile`

**Purpose.** Classify a change as `patch` / `feature` / `migration` / `incident` based on what it touches.

**Args:**
- `files_changed: list[str]`
- `commit_message: str` (optional)

**Algorithm:**
1. Apply heuristic regex against file paths and commit message.
2. Returns first matching profile (in priority order: `incident` > `migration` > `feature` > `patch`).

Heuristics:
- `migration`: schema/migration paths, `db/migrate`, `alembic/`, `flyway/`, > 10 files touched
- `incident`: branch name or commit contains `hotfix|incident|p0|p1`
- `feature`: new service/controller/entity created
- `patch`: everything else

---

## 4. `check_business_rule`

**Purpose.** Get the full details of one rule.

**Args:**
- `rule_id: str` (e.g., `"VR-01"`)

**Algorithm:**
1. Load rules; linear search for first match.
2. If not found, return list of first 20 available IDs.
3. If found, render rule fields as markdown.

**Output example:**
```
## Rule: VR-01 — Hardcoded Password

**Action:** BLOCK | **Severity:** critical
**Applies to:** ALL
**Guardrails:** G-SDLC-5, G2.1
**Groups:** security-critical

**Rationale:** Passwords in source code end up in version control.
**Fix:** Store passwords in a secret manager.
**Acceptance Criteria:**
  GIVEN a source file of any type
  WHEN a password/passwd/pwd is assigned a literal string
  THEN the scanner MUST block the commit
```

---

## 5. `compute_trust_score`

**Purpose.** Compute a 0–100 trust score from observed quality signals.

**Args (all 0–100 unless noted):**
- `scanner_pass_rate: float` (required)
- `test_coverage: float` (optional)
- `mutation_kill_rate: float` (optional)
- `business_rule_coverage: float` (optional)
- `human_review_depth: float` (optional; 0=none, 50=glance, 100=deep)
- `drift_delta_count: int` (optional; inverse — converted to score)
- `hallucination_flags: int` (optional; inverse)

**Algorithm:**
1. Component weights:
   ```
   scanner_pass_rate       0.20
   test_coverage           0.20
   mutation_kill_rate      0.20
   business_rule_coverage  0.15
   human_review_depth      0.10
   drift_delta_count       0.10
   hallucination_flags     0.05
   ```
2. Convert inverse metrics: `drift_score = max(0, 100 - count * 20)`; `hallucination_score = max(0, 100 - count * 25)`.
3. Drop unprovided components; redistribute weights so the remaining sum to 1.
4. `total = Σ(value × adjusted_weight)`; round to integer.

**Rating bands:**
- 85+ Excellent
- 70+ Good
- 50+ Acceptable
- <50 FAILING (read-only mode triggered)

---

## 6. `get_skill`

**Purpose.** Load a skill's full instructions on demand. Called when a skill's trigger fires.

**Args:**
- `skill_id: str` (e.g., `"code-review-gate"`)

**Algorithm:**
1. Load `_registry.yaml`. Find skill by id.
2. If not found, return list of all skill IDs.
3. Resolve instruction file path; read SKILL.md.
4. Return: metadata (name, description, scope, triggers) + full instructions body.

See the [skills catalog](../catalogs/skills.md) for the registry.

---

## 7. `report_generation`

**Purpose.** Write an entry to the audit log after the AI generates code. Used by PostToolUse.

**Args:**
- `files_created: list[str]`
- `files_modified: list[str]`
- `reasoning: str`
- `business_rules_covered: list[str]` (optional)

**Algorithm:**
1. Construct entry with ISO timestamp + all args.
2. Append as a single JSON line to `.ai-ase/audit-log.jsonl`.

**Side effect:** writes to `.ai-ase/audit-log.jsonl` (append-only).

**Audit format:**
```json
{"timestamp":"2026-05-05T14:32:01","files_created":["src/PaymentService.java"],"files_modified":[],"business_rules_covered":["B001"],"reasoning":"...","total_files_touched":1}
```

---

## 8. `check_policy`

**Purpose.** Determine whether a specific tool call would be allowed by the policy engine.

**Args:**
- `tool_name: str`
- `phase: str` (default `reflector`)
- `profile: str` (default `feature`)
- `path: str` (optional — for file tools)
- `command: str` (optional — for run_command)
- `trust_score: float` (default 80.0)

**Algorithm:**
1. Resolve mode from phase:
   - archaeologist | guardian | architect | critic → `read_only`
   - reflector → `edit_files`
2. Profile override:
   - patch / feature / migration + reflector → `shell_limited`
   - incident + reflector → `shell_full`
3. Trust degradation:
   - trust < 30 → `deny_all`
   - trust < 50 → `read_only`
4. Check tool against mode allowlist:
   - `deny_all`: []
   - `read_only`: read_file, search_repo, list_dir, grep_search, get_active_rules, check_business_rule, compute_trust_score, detect_profile, get_skill, check_policy
   - `edit_files`: above + write_file, apply_patch, validate_code, report_generation
   - `shell_limited`: above + run_command (allowlisted)
   - `shell_full`: above + run_command (any)
5. Additional checks:
   - Path: deny `.env`, `secrets/`, `.github/`, `.key`, `.pem`, traversal `..`
   - Command (shell_limited only):
     - Allowed: `mvn test`, `gradle test`, `npm test`, `pytest`, `dotnet test`, `ai-ase-scan`
     - Denied: `rm -rf`, `sudo`, `chmod 777`, `curl`, `wget`, `docker run`, `kubectl apply`, `git push`, `git reset --hard`
6. Log to `.ai-ase/policy-audit.jsonl`.

**Side effect:** writes to `.ai-ase/policy-audit.jsonl`.

---

## 9. `dry_run_preview`

**Purpose.** Show what a tool call would do without executing it.

**Args:**
- `tool_name: str` (`write_file` / `apply_patch` / `run_command`)
- `phase`, `profile`, `path`, `content`, `command` (as needed)

**Algorithm:**
1. Run `check_policy` to determine if the action would be allowed.
2. Tool-specific preview:
   - `write_file`: file exists? overwrite vs create. Count bytes/lines. Run `validate_code` on `content`.
   - `run_command`: classify against allowlist/denylist.
   - `apply_patch`: show diff that would result.
3. Risk assessment table (severity + detection mechanism).
4. Return policy result + preview + risks. No side effects.

---

## Configuration

How AI-ASE exposes the tools over MCP is in [spec/05-mcp-server.md](../spec/05-mcp-server.md). How an AI IDE connects to the server is in [spec/22-mcp-connection.md](../spec/22-mcp-connection.md).