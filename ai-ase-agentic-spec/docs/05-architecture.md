# Architecture

**Read time:** 6 minutes.

This is the design map — how the parts fit. For *how to build it*, see [spec/](../spec/) and the build path in [spec/00-build-path.md](../spec/00-build-path.md).

---

## The shape

```
   ── on-disk sources ──            ── runtime ──             ── on-disk record ──

   ┌──────────────────┐                                         ┌──────────────────┐
   │ rules/*.yaml     │──┐                                  ┌──►│ audit.jsonl      │
   │ (71 rules)       │  │                                  │   │ checkpoints.jsonl│
   └──────────────────┘  │                                  │   │ session.log      │
                         │                                  │   └──────────────────┘
   ┌──────────────────┐  │     ┌──────────────────────┐     │
   │ skills/*.md      │──┤     │ Governance Kernel    │     │
   │ (21 skills)      │  ├────►│ - 8 immutable rules  │     │
   └──────────────────┘  │     │ - active phase       │     │
                         │     │ - relevant rules     │     │
   ┌──────────────────┐  │     │ - triggered skills   │     │
   │ phase.json       │──┤     └──────────┬───────────┘     │
   │ trust.json       │  │                │ injected via    │
   │ settings         │  │                │ UserPromptSubmit│
   └──────────────────┘  │                ▼                 │
                         │     ┌──────────────────────┐     │
                         │     │   AI IDE / agent     │     │
                         │     └──────────┬───────────┘     │
                         │                │ tool call       │
                         │                ▼                 │
                         │     ┌──────────────────────┐     │
                         └────►│   PreToolUse hook    │     │
                               │   - phase gate       │     │
                               │   - skill artifact   │     │
                               │   - rule scan        │     │
                               │   - trust check      │     │
                               └──────────┬───────────┘     │
                                          │ ALLOW/BLOCK/WARN│
                                          ▼                 │
                               ┌──────────────────────┐     │
                               │   Tool execution     │─────┤
                               └──────────┬───────────┘     │
                                          │ result          │
                                          ▼                 │
                               ┌──────────────────────┐     │
                               │   PostToolUse hook   │─────┘
                               │   (Quality skills)   │
                               └──────────────────────┘
```

Four facts to internalize:

1. **Everything left of the runtime is a file.** Rules, skills, phase state, settings — all grep-able, git-able, yours. (V7.)
2. **The kernel is small and fires every turn.** Not a sermon — a contract reminder.
3. **The hooks are the teeth.** The kernel shapes behavior; hooks shape outcomes.
4. **Skills are on-demand expertise.** Loaded by the kernel when triggered, consulted by hooks when blocking, idle otherwise. (V5.)

## The 5 Phases

Every non-trivial change moves through five phases. Each has a single purpose, a read/write policy, and a hand-off gate that requires explicit human approval to advance.

| # | Phase | Purpose | R/W |
|---|---|---|---|
| 1 | **Archaeologist** | Understand the code as it is. | Read-only |
| 2 | **Guardian** | Identify the business and security guardrails that apply. | Read + write `business-guardrails.md` only |
| 3 | **Architect** | Design the change. Get human alignment. | Read + write design docs |
| 4 | **Critic** | Attack the design. Find what breaks. | Read-only |
| 5 | **Reflector** | Implement. The only phase where production code is written. | Full write |

Phase state lives in `phase.json`. Advancing requires that the current phase's required artifacts exist *and* the human has explicitly approved.

**Why five, not three or seven?** Three collapses Critic into the implementer — exactly the failure the framework prevents. Seven adds ceremony without proportional safety. Five separates *understanding* from *governance scoping* from *design* from *adversarial review* from *execution*.

Detail: [docs/06-five-phases.md](../docs/06-five-phases.md).

## Skills — on-demand expertise

A **skill** is a single-purpose, single-file capability the agent invokes when its trigger matches. Skills exist because the governance kernel can't carry every piece of expert knowledge — a 50-line kernel won't hold the full procedure for, say, an adversarial code review. Skills park that knowledge on disk and load it only when needed.

21 skills ship with AI-ASE. They fall into six types:

| Type | Count | What they do | Example |
|---|---|---|---|
| **Enforcement** | 1 | Always-on governance, fires once per session | `challenge-me` (alignment interview at session start) |
| **Phase** | 5 | One per phase — produces the artifact required to advance | `business-rule-extraction` (Archaeologist) |
| **Gate** | 3 | Blocking structural check on a specific event | `code-review-gate` (fires on new controller/service file) |
| **Quality** | 5 | Verify the change is correct, not just compliant | `mutation-testing`, `anti-hallucination-audit` |
| **Feedback** | 1 | Turn human corrections into framework rules | `car-feedback-loop` |
| **Utility** | 6 | Scheduled or on-demand operations | `trust-score-analysis`, `session-log-management` |

Three properties matter architecturally:

- **Triggered, not loaded.** Skills don't enter the model's context until their trigger fires (an event, a phase change, a file pattern). This is V5 (Context is King) at work.
- **Some are blocking.** A blocking skill that hasn't produced its artifact prevents phase advancement. That's how rule 2 (Phase Gates) and rule 7 (Business Authority Gate) are enforced mechanically rather than via prompt.
- **They're files, not code.** Each skill is a Markdown file with frontmatter. Adding a skill means writing a file, not deploying anything.

The full catalog lives in [catalogs/skills.md](../catalogs/skills.md). The trigger-to-skill mapping per hook event is in [spec/12-skills-system.md](../spec/12-skills-system.md).

**Where skills fit in the diagram above:** they're consulted at three points — the kernel mentions any triggered skill in its injection, the PreToolUse hook checks for required artifacts before allowing a write, and PostToolUse may activate Quality skills against the result.

## The 11 Enforcement Layers

The kernel and the phases are the visible architecture. Underneath, eleven concrete mechanisms enforce the values.

| # | Layer | What it does | Where |
|---|---|---|---|
| 1 | Governance Kernel | Injects 8 rules + active phase + context every turn | UserPromptSubmit |
| 2 | Context Assembler | Maps file patterns to relevant guardrails | UserPromptSubmit |
| 3 | RAG Retriever (TF-IDF) | Scores rules against the prompt; surfaces top 5 | UserPromptSubmit |
| 4 | Skill Trigger Engine | Evaluates events against 21 skills; auto-activates matches | UserPromptSubmit / SessionStart / PreToolUse |
| 5 | Challenge-Me Protocol | Mandatory alignment interview at session start | SessionStart |
| 6 | Phase Gate Enforcement | 5-phase state machine; read-only until Reflector | PreToolUse |
| 7 | Skill Artifact Enforcement | Blocking skills must produce artifacts before advancement | PreToolUse |
| 8 | Guardian Governance Allowlist | Guardian may write only `business-guardrails.md` / `COMPLIANCE.md` | Policy module |
| 9 | Multi-Agent Critic | Spawns sub-agent verifiers on high-risk writes | PreToolUse |
| 10 | Journey-Log Automation | Appends checkpoints; surfaces summary next session | PostToolUse / SessionStart |
| 11 | Trust Score Auto-Enforcement | Recomputes trust from last 20 writes; degrades on drop | PreToolUse |

A layer absent from this list is not "in AI-ASE."

## How a turn flows end-to-end

1. User types a prompt.
2. **UserPromptSubmit** fires → kernel + active phase + assembled context + retrieved rules + triggered skill names injected as `additionalContext`.
3. The agent reads the prompt + injected context and decides what to do. If a skill was triggered, the agent loads its body now.
4. If the agent calls a tool, **PreToolUse** fires:
   - Phase gate: is this tool allowed in the current phase?
   - Skill artifact gate: does the active phase have an unsatisfied blocking skill?
   - Rule scan: does the proposed write violate any BLOCK rule?
   - Trust check: does the agent have permission for this action?
   - On any failure → BLOCK with a structured reason.
5. If allowed, the tool runs.
6. **PostToolUse** fires. Result logged. Quality skills may activate against the result. If a checkpoint is warranted, appended to the journey log.
7. The agent sees the result and produces the next response.

Steps 2 and 4 are the only places where governance has teeth. Everything else is observation.

## Why MCP

MCP (Model Context Protocol) is the integration boundary. AI-ASE exposes its rule scanner, policy checker, and audit reader as MCP tools. The same governance works in any MCP-compatible AI IDE. Tool definitions live in [catalogs/tools.md](../catalogs/tools.md) — a single source. Adding a new IDE is a config change, not a fork.

## Why the kernel is 50 lines, not 750

A 750-line kernel competes with the user's actual prompt for the model's attention. A 50-line kernel injects the contract; the rest (rule details, skill bodies, phase mechanics) loads on-demand via skills and RAG. V5 (Context is King) made concrete.

---

**Next:** [docs/06-five-phases.md](../docs/06-five-phases.md) — what each phase does, what it must produce, how it advances.