# Multi-Agent Verification

## Purpose

`agents.py` coordinates the 4-agent verification model (Generator → Verifier → Attacker → Auditor) used in the Reflector phase. The architectural property: agents see each other's *outputs*, never each other's *reasoning*. This prevents circular self-validation (AI judging its own work).

## The 4 agents

| Agent | Sees | Produces | Notes |
|---|---|---|---|
| Generator | task description + business rules + ADR | source code | the "writer" |
| Verifier | business rules + GIVEN/WHEN/THEN (NOT source code reasoning) | test files | writes tests that verify rules are met |
| Attacker | interface contracts only (NOT implementation details) | adversarial test files | designed to BREAK the implementation |
| Auditor | outputs of 1–3 + governance rules | audit report | checks protocol compliance, flags anomalies |

## Context isolation

Each agent runs in a fresh sub-agent boundary. They cannot see:

- Each other's chat history.
- The main session's accumulated context.
- The other agents' internal monologue.

They can only see what is passed in via the briefing prompt + tool results. This is the same isolation property described in [ai-ide-research/04-agent-isolation.md](../ai-ide-research/04-agent-isolation.md).

Implementation: when the host AI IDE supports sub-agent spawning (most do), use it. Otherwise, simulate isolation by clearing context between roles. The point is the same: no agent should be able to argue from another's reasoning.

## Public interface

```python
@dataclass
class AgentBriefing:
    role: str                       # "generator" | "verifier" | "attacker" | "auditor"
    task: str
    visible_artifacts: list[Path]   # what this agent is allowed to read
    depth: str                      # "minimal" | "standard" | "maximum" | "post-hoc"

@dataclass
class AgentRun:
    role: str
    artifacts_produced: list[Path]
    started_at: str
    completed_at: str
    notes: str

def brief(role: str, *, task: str, depth: str, prior_outputs: list[Path]) -> AgentBriefing: ...

def run_chain(task: str, depth: str) -> list[AgentRun]: ...
```

## Algorithm: `brief(role, task, depth, prior_outputs)`

```
1. visible = {
     "generator": [task_file, "business-guardrails.md", "docs/adr/*"],
     "verifier":  ["business-guardrails.md"],   # no source visibility
     "attacker":  [interface_contracts(prior_outputs)],   # public API only
     "auditor":   prior_outputs + ["rules/*", "audit-log.jsonl"],
   }[role]
2. return AgentBriefing(role, task, visible, depth)
```

`interface_contracts(prior_outputs)` extracts type signatures / API surface from generator output but strips bodies. Implementation: language-specific parsers (Python `ast`, Java/JS via regex). MVP: regex extraction of `def`, `class`, `interface`, `public` declarations.

## Algorithm: `run_chain(task, depth)`

```
1. gen = run_agent(brief("generator", task=task, depth=depth, prior_outputs=[]))
2. ver = run_agent(brief("verifier",  task=task, depth=depth, prior_outputs=gen.artifacts_produced))
3. att = run_agent(brief("attacker",  task=task, depth=depth, prior_outputs=gen.artifacts_produced))
4. aud = run_agent(brief("auditor",   task=task, depth=depth,
                         prior_outputs=gen.artifacts_produced + ver.artifacts_produced + att.artifacts_produced))
5. return [gen, ver, att, aud]
```

`run_agent()` is the host integration point. The MVP shells out to the AI IDE's sub-agent API (Claude Code's `Task` tool, similar facilities elsewhere). When unavailable, it logs a clear capability-missing notice and degrades to single-agent operation.

## Depth scaling by profile

| Profile | Generator | Verifier | Attacker | Auditor |
|---|---|---|---|---|
| `patch` | writes fix | basic check | 1 edge case | protocol pass |
| `feature` | writes code | full tests | 5–10 adversarial | full audit |
| `migration` | writes code | exhaustive | maximum battery | full + compliance |
| `incident` | writes fix | full tests | full battery | full audit (post-hoc, 48 h) |

`depth` parameter maps to per-agent prompt detail (which sections to include) and acceptance thresholds (mutation kill rate, hallucination tolerance).

## Anti-circular-validation tests

`test_mutation.py` is the keystone:

1. Take a clean fixture, run the chain, capture all outputs.
2. Mutate a non-trivial part of the Generator's output (e.g., flip a condition).
3. Re-run only Verifier + Attacker + Auditor with the mutated Generator output.
4. Assert at least ONE of (Verifier, Attacker, Auditor) flags the mutation.

If none catch it, the agents are colluding (probably context leakage). Fail loud.

## Tests (target ≥ 25)

- Each role briefs with the correct visible artifact set.
- `interface_contracts()` strips bodies from Python / Java samples.
- `run_chain()` produces 4 `AgentRun` entries.
- Mutation probe: a flipped condition is caught by Attacker tests.
- Depth scaling: `patch` → minimal acceptance criteria, `migration` → maximum.
- Audit log: each agent run produces a `tool_call` event.

## Anti-patterns

| Don't | Because |
|---|---|
| Pass the full chat history to each agent | Defeats isolation. Each agent gets a fresh briefing. |
| Use the same model role for all four | Diversity helps. Use different temperatures or different models when available. |
| Skip the auditor when in a hurry | The auditor is the protocol-compliance check. Skipping it lets the other three drift. |
| Allow attacker to see the test files | Attacker designs tests to break the implementation, blind to what verifier already wrote. Otherwise you re-test the same thing. |

## Ground truth

No standalone vendored file. The behavior is defined by this spec; see [ai-ide-research/04-agent-isolation.md](../ai-ide-research/04-agent-isolation.md) for the empirical basis.