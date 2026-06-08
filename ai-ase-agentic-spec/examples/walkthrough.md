# End-to-End Walkthrough — One Change, All Five Phases

This walks through a single, realistic change end-to-end so you can see what AI-ASE actually feels like in a session. It is **not** a copy-pasteable script — the IDE prompts and AI replies vary by tool. It is the *shape* of a governed session.

> **Scenario.** A payments team is adding a new endpoint: `POST /refunds`. It must look up the original charge, refuse refunds older than 90 days, write a `refund` row, and emit an `audit.refund.created` event.

---

## Phase 0 — `ai-ase init` (one time per repo)

```bash
$ pip install ai-ase
$ ai-ase init
✓ Wrote .ai-ase/profile.json (profile: feature)
✓ Wrote .ai-ase/phase.json (phase: archaeologist)
✓ Wrote .ai-ase/trust.json (trust: 70)
✓ Wrote .mcp.json (governance server registered)
✓ Installed hooks (PreToolUse, PostToolUse, UserPromptSubmit, SessionStart)
```

What just happened: the framework wrote four small files on disk and a hook config the IDE will pick up next session.

---

## Phase 1 — Archaeologist

**Developer** opens the AI IDE, types:

> "Add a `POST /refunds` endpoint to charges-service."

What the session shows:

1. **SessionStart hook fires.** The kernel + active phase (`archaeologist`) are injected into the prompt.
2. **`challenge-me` skill activates.** The AI asks:
   - Who is the human authority for this rule? (engineering manager? product?)
   - Is the 90-day window a business rule or a regulatory one?
   - Does an existing audit topic exist, or do we need a new one?
3. **`business-rule-extraction` skill activates.** The AI proposes additions to `business-guardrails.md`:

```markdown
### [B042] Refund window
GIVEN a charge older than 90 days
WHEN a refund is requested
THEN the system MUST refuse with 422 and reason "refund_window_expired"
Authority: payments-pm@company
```

4. **Phase gate.** AI says: "I've drafted B042. I cannot advance to Guardian until you (a qualified human) approve `business-guardrails.md`. Approve?"
5. **Developer** edits the file, commits, types `phase advance`.

**What was produced:** an entry in `business-guardrails.md`. No code yet.

---

## Phase 2 — Guardian

The phase changes to `guardian`. The kernel + a different active-phase string get re-injected on the next prompt.

1. **`guardrail-compliance-check` skill activates.** The AI loads the relevant rule subset for the file patterns it expects to touch (controllers, services, migrations). It reports which BLOCK rules apply (VR-05, VR-10/10b, VR-15) and which WARN rules are likely (logging-sensitive-data, missing-timeout-on-external-call).
2. The AI proposes the *constraints* the eventual code must satisfy. No code is written.
3. **Phase gate.** Developer approves. Advance.

**What was produced:** a short compliance note in the session log. Nothing else.

---

## Phase 3 — Architect

Phase changes to `architect`.

1. **`architecture-design` skill activates.** The AI drafts:
   - A sequence diagram: controller → service → repository → event publisher.
   - An ADR: "Refund eligibility check belongs in the service layer, not the controller, so we can reuse it from the admin-reversal path."
   - Decisions on idempotency (request-ID header), retry behaviour (none — refunds are not retried automatically), and event schema.
2. **Phase gate.** Developer reviews the ADR, asks a clarifying question, AI updates, developer approves.

**What was produced:** `docs/adr/0042-refund-eligibility.md` + a design sketch in the session log.

---

## Phase 4 — Critic

Phase changes to `critic`. The AI is now in *adversarial* mode.

1. **`adversarial-review` skill activates.** The AI argues against its own design:
   - "If the original charge is in a non-USD currency, the 90-day window may be wrong — some EU regulations require 14 days. Confirm scope is USD only."
   - "If the audit publisher is down, what happens? My current design silently drops the event. Decide: queue, retry, or fail the refund."
   - "B042 doesn't say what happens to *partial* refunds older than 90 days where the original part is fresh. Underspecified."
2. **Phase gate.** Developer responds: "USD only is fine. Use the outbox pattern for the audit event. Partial refunds are out of scope — fail closed." AI updates the ADR. Advance.

**What was produced:** a risk report appended to the session log + a small ADR update.

---

## Phase 5 — Reflector

Phase changes to `reflector`. **This is the only phase that writes application code.**

1. **`business-authority-gate` skill activates.** Verifies `business-guardrails.md` is approved (Rule 7). It is. Continue.
2. **`code-generation` skill activates.** The AI writes the files.
3. **Every `Write` and `Edit` triggers `PreToolUse`.** A worked example:

```jsonc
// Hook stdin
{
  "hook_event_name": "PreToolUse",
  "tool_name": "Write",
  "tool_input": {
    "file_path": "src/charges/refund_service.py",
    "content": "...\nrefund.amount = float(charge.amount)\n..."
  }
}

// Hook stdout
{
  "permissionDecision": "deny",
  "permissionDecisionReason": "VR-10 BLOCK: float for money. Use Decimal."
}
```

The write is rejected. The AI sees the reason in its tool result, rewrites with `Decimal`, retries. The retry passes. The file lands.

4. **`PostToolUse` re-scans on disk** — belt for the suspenders — and appends a `validation` event to `.ai-ase/audit-log.jsonl`.
5. **`anti-hallucination-audit` skill runs after the batch.** It opens every imported module and confirms it exists. (One time, it caught `from charges.repository import find_by_id` — the function was actually `get_by_id`. The AI fixed it.)
6. **`mutation-testing` skill runs.** Kill rate: 78 %. Passes the 70 % threshold so `adversarial-testing` activates and writes 6 additional negative-path tests.
7. **`manifest-reconciliation` skill runs at end.** Compares planned files (from the ADR) against actually-touched files. One drift: AI touched `src/charges/__init__.py` to add an export. Surfaced as a `WARN` for human review.
8. **`car-feedback-loop` skill (deferred).** Developer notices the AI named the new event `refund.created` instead of `audit.refund.created` per house convention. Corrects it. AI proposes a *new framework rule* (Rule 6 — every correction becomes a rule), not just a code fix:

```yaml
- id: VR-89
  name: "Audit events must be prefixed with audit."
  action: WARN
  file-types: [PYTHON, JAVA]
  pattern: |
    publish\(["'](?!audit\.)[a-z]+\.[a-z]+["']
```

Developer accepts. New rule lands in `rules/code-quality/`. Next time anyone forgets, the scanner catches it.

---

## What the audit log shows

After the session, `.ai-ase/audit-log.jsonl` contains (excerpt):

```jsonl
{"ts":"2026-06-08T10:02:11Z","event":"session_start","session_id":"s-9f3a","profile":"feature"}
{"ts":"2026-06-08T10:02:14Z","event":"phase_change","from":"archaeologist","to":"guardian","approver":"dev@company"}
{"ts":"2026-06-08T10:14:02Z","event":"validation","file":"src/charges/refund_service.py","decision":"deny","violations":["VR-10"]}
{"ts":"2026-06-08T10:14:09Z","event":"validation","file":"src/charges/refund_service.py","decision":"allow","violations":[]}
{"ts":"2026-06-08T10:17:33Z","event":"trust_score","score":82,"band":"good","components":{"scanner_pass_rate":0.94,"mutation_kill_rate":0.78,"hallucination_flags":0}}
{"ts":"2026-06-08T10:18:01Z","event":"car_rule_added","rule_id":"VR-89","trigger":"human correction"}
```

Six months later, when somebody asks *"why does refund_service.py use Decimal?"*, the audit log answers it without a meeting.

---

## What this walkthrough is meant to teach

- **The phases are doing work even when no code is written.** Archaeologist, Guardian, Architect, Critic produce constraints. Reflector consumes them.
- **The hooks are the teeth.** A WARN in the kernel is a suggestion. A BLOCK in `PreToolUse` is a wall.
- **The catalog of things that fire is small.** A single change session is touched by maybe 10 of the 21 skills, never all of them at once.
- **The audit log is the receipt.** If you can't reconstruct *why* something looks the way it does six months later, you don't have governance — you have prompts.

---

## See also

- [examples/quickstart.md](../examples/quickstart.md) — the 60-second demo (a single BLOCK violation, no phases).
- [examples/source-mapping.md](../spec/source-mapping.md) — which file in the repo implements each piece you saw above.
- [docs/06-five-phases.md](../docs/06-five-phases.md) — phases as a concept.
- [docs/05-architecture.md](../docs/05-architecture.md) — the runtime picture.
