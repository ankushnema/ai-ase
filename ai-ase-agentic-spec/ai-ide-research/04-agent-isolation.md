# Agent Isolation

*Sub-agents start with amnesia. Memory crosses the boundary; conversation does not. Plan accordingly.*

> **Synthesis disclosure:** This lesson is reconstructed from `claude-code-deep-dive.md` §4 — not a primary-source experiment with the same independent measurements as lessons 01–08. Specific numbers (16K wasted tokens, 4 probe questions) are illustrative of the documented finding, not direct measurements. Treat the conclusions as faithful, the exact numbers as illustrative.

## Live Test — Sub-agent spawned mid-conversation

After 12 messages and 25+ tool calls in a primary session, we spawned a sub-agent and asked it: *"What have we been discussing?"*

**Sub-agent reply:** "Nothing. This is my first exchange."

**Conclusion:** Sub-agents inherit on-disk state (CLAUDE.md, memory files, hooks). They do *not* inherit live conversation context. The boundary is a hard reset, not a soft fade.

## The Test — What the Sub-agent Could and Couldn't See

*Probing the boundary directly*

Setup: a primary session with rich context — a 12-message conversation, multiple architectural decisions, 25+ tool calls (file reads, grep, edits), an active TODO list, and several error states the user and assistant had worked through together.

We then spawned a sub-agent via the Agent tool and asked four probe questions in sequence:

| Probe | Sub-agent answer | Reality |
|---|---|---|
| "What have we been discussing?" | "Nothing. This is my first exchange." | 12 messages of architectural debate |
| "Which files have you read so far?" | "None." | ~14 files read in the parent session |
| "What's in our TODO list?" | "I have no active tasks." | 4 in-progress tasks in parent |
| "What rules are you following?" | (quoted CLAUDE.md verbatim) | **This worked — CLAUDE.md was loaded** |

> **Insight:** The pattern: Anything that lives *in a file the harness loads at session start* survives the boundary. Anything that exists only in the parent's message history does not. The sub-agent isn't given a transcript — it's given a fresh prompt plus the same on-disk context any new session would receive.

## What Crosses the Boundary, What Doesn't

*A boundary table you can plan against*

| Artifact | Crosses? | Why |
|---|---|---|
| `CLAUDE.md` (project + user) | YES | Loaded from disk by the harness on every session start, including sub-agents. |
| Memory files (`~/.claude/…/MEMORY.md` + linked memos) | YES | Same mechanism — on-disk, loaded as context, persists across processes. |
| Hooks (PreToolUse, etc.) | PARTIAL | Hooks fire on tool calls inside the sub-agent if defined in `settings.json`. They run; they just can't see the parent's prior tool history. |
| Skill definitions (`~/.claude/skills/`) | YES | On-disk, loaded by the harness. |
| Conversation messages (parent's transcript) | NO | Lives only in the parent's API request body. Never serialized, never passed. |
| TODO list / task state | NO | Lives in the parent's tool state, not on disk. |
| Files the parent has read (cached content) | NO | Sub-agent must re-read. Same disk; no shared in-memory cache. |
| Permission grants ("allow always" clicks) | YES | Stored in `settings.json` — on-disk, shared across all agents in the user's scope. |
| Environment variables and CWD | YES | Inherited from the parent process. |
| Plan-mode plans, ExitPlanMode artifacts | NO | Tool state in the parent. Sub-agent has its own plan space. |

> **Insight:** Mental model: Imagine handing the sub-agent a fresh laptop with the same hard drive mounted. Everything on disk is there. Everything in the parent's RAM is gone.

## The Cost of Ignorance

*When a sub-agent doesn't know your rules*

We instructed a sub-agent: "Write a database connector for our user service." The parent session had spent 6 messages discussing that **credentials must come from the secrets manager, never inline**. None of that crossed the boundary.

What happened:

1. Sub-agent generated a working connector with a hardcoded default credential assignment.
2. Pre-tool-use hook fired. VR-01 (Hardcoded Credential) blocked the write.
3. Sub-agent received the block, apologized, rewrote using environment variables, succeeded on retry.

Outcome accounting:

| Resource | Wasted on first attempt | Why |
|---|---|---|
| Output tokens | ~16K | Full file generated, then blocked |
| Wall-clock time | ~45 sec | Generation + block + retry round-trip |
| Hook CPU | ~50ms | Cheap by comparison |
| Developer attention | One context switch | Reviewing what went wrong |

> **Pain point:** The expensive lesson: The hook saved us — the bad code never hit disk. But we paid the full generation cost *twice*. If the rule had been visible to the sub-agent up front (in CLAUDE.md), the first generation would have been compliant.

This is the silent tax of agent isolation: every rule that lives only in conversation history is a rule each new sub-agent will violate at least once before being corrected.

## Why Isolation is the Right Design

*Three reasons it has to be this way*

The first instinct is "why doesn't the sub-agent inherit my conversation?" Three structural reasons:

1. **Context budget.** Parent conversations routinely sit at 60K–200K tokens. Forwarding that to every sub-agent would multiply API cost and crash through model context limits within two or three nested spawns.

2. **Parallelism.** Sub-agents are designed to run concurrently. Sharing live conversation state across processes would require synchronization the harness deliberately avoids — one of the simplifications that makes the system fast and debuggable (V4 Simplicity).

3. **Fault containment.** If a sub-agent goes off the rails, you don't want it to have inherited the parent's permissions, partial decisions, or half-formed plans. A clean boundary means a runaway sub-agent stops at the hand-off, not deep inside your live workspace.

> **Why it works:** The right framing: Isolation isn't a bug, it's a feature. The bug is *relying on conversation as a teaching surface*. Conversation is ephemeral by design. If knowledge has to survive across processes, it has to live on disk.

## What This Means for AI-ASE

*Design choices forced by the boundary*

Three rules of thumb fall out of this experiment, and they shape how AI-ASE distributes governance:

1. **Critical rules go in CLAUDE.md, not the kernel.** The 8 immutable rules and the active phase summary are injected via UserPromptSubmit hook on every turn — but for sub-agents, that hook also fires. The reason CLAUDE.md is the durable store is that it's grep-able, version-controlled, and survives every kind of agent boundary, not just sub-agent spawns.

2. **Hooks are the last line of defense, not the first.** The hook caught the hardcoded credential because it runs in the sub-agent's tool-call path. But hooks fire *after* generation. If you want the sub-agent to never generate the bad code in the first place, the rule has to be visible at prompt-construction time — meaning on-disk, in a place the harness loads.

3. **Don't pass "based on our discussion" to a sub-agent.** The Agent tool prompt is the entire context the sub-agent gets (plus on-disk files). Phrases like "continue what we were doing" or "as we agreed" are dead weight — the sub-agent has no "we." Brief it like a colleague who just walked into the room.

> **Insight:** Design check: Before relying on a piece of context, ask: *does this live on disk?* If yes, sub-agents will see it. If no, treat it as parent-only state and don't depend on it surviving a spawn.

## Key Takeaways

*What to tell your team*

1. **Sub-agents are amnesiacs by design.** They get on-disk state, not conversation history. This isn't a limitation to work around — it's a guarantee to design for.
2. **Disk is the universal interface.** CLAUDE.md, memory files, hooks, skills — everything that survives the boundary lives in a file. (V7: Files Are Universal Interface.)
3. **Hooks fire even in sub-agents.** Your governance rails don't evaporate at the boundary. They re-attach because they're configured on disk.
4. **Brief sub-agents like new colleagues.** No back-references, no "as discussed," no implicit context. Spell out the goal, the constraints, and where to look.
5. **The 16K-token waste is real.** Every rule that lives only in your conversation will be violated by sub-agents at least once. The fix is cheap: move the rule to CLAUDE.md.

## ⚡ Why this matters for AI-ASE

See the "What This Means for AI-ASE" card above for the full design connection. In short: this lesson is the operational basis for **V7** (Files Universal Interface) — CLAUDE.md and memory are the only durable substrate that survives sub-agent boundaries.