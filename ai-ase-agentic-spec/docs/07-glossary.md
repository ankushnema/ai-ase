# Glossary

Quick reference. Alphabetical. Definitions are intentionally terse.

---

**ADR.** Architecture Decision Record. Short doc capturing one architectural decision: context, decision, consequences.

**Agent (sub-agent).** A spawned process running as a separate AI session. Inherits on-disk state but not the parent's conversation.

**Audit log.** JSONL file (`audit.jsonl`) recording every tool call, hook decision, and policy outcome. Source of truth for "what actually happened."

**BLOCK.** Rule severity: the PreToolUse hook refuses the operation. The agent cannot proceed.

**CAR.** Correction → Audit → Rule. Every human correction becomes a framework rule, not just a code fix. Rule 6.

**Challenge-Me.** Mandatory alignment interview at session start. Confirms goals and constraints before work begins.

**Context Assembler.** Layer 2. Maps file patterns to the guardrail subsets relevant to those files (`assembler.yaml`).

**Governance Kernel.** The ~50-line prompt injected via UserPromptSubmit on every turn. The 8 immutable rules + active phase + pointers.

**Hook.** A shell command or script the AI IDE executes on a defined event. Four standard events: SessionStart, UserPromptSubmit, PreToolUse, PostToolUse.

**MCP.** Model Context Protocol. The integration boundary AI-ASE uses to expose its tools to any compatible AI IDE.

**Phase.** One of five stages of work: Archaeologist, Guardian, Architect, Critic, Reflector. State in `phase.json`. Only Reflector writes production code.

**Phase Gate.** Blocking check requiring explicit human approval to advance phases.

**PHASE_SKILLS.** Map from phase to required skill artifacts. Used by `skills_satisfied()` to gate phase advancement.

**Profile.** Pre-configured ceremony level: `patch` (minimal), `feature` (default), `migration` (highest), `incident` (fast-path with mandatory post-hoc audit).

**RAG Retriever.** Layer 3. TF-IDF scoring of the rule catalog against the active prompt; surfaces top-N most relevant rules.

**Read-only verbs.** Verbs ("analyze", "review", "compare", "check") that mean *report*, not *act*. Rule 5.

**Rule Catalog.** YAML library of governance rules. Canonical reference: [catalogs/rules.md](../catalogs/rules.md).

**Session Log.** Per-session record of work, decisions, tool calls. Rule 1: no work begins before it exists.

**Skill.** Markdown file describing an on-demand capability. Loaded by the IDE when its trigger fires. 21 in total.

**Skill Artifact.** A file a skill must produce. Used to gate phase advancement.

**Trust Score.** 0–100 metric over the last 20 writes. Drops on violations, partial edits, or human overrides. Below 50 → read-only.

**TF-IDF.** Term Frequency–Inverse Document Frequency. Text-similarity algorithm for rule retrieval. Chosen over embeddings for V4 (Simplicity).

**UserPromptSubmit hook.** Fires on every user message before the agent sees it. Where kernel, phase summary, and retrieved rules are injected.

**VR-NN.** Rule identifier (e.g., VR-01, VR-67). "VR" = Validation Rule.

**WARN.** Rule severity: hook flags the operation but does not block. Agent should surface to user.