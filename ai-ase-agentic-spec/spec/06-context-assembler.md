# Context Assembler

## Purpose

`context.py` builds the prompt context the AI sees on every turn. It assembles:

1. The **50-line governance kernel** (immutable).
2. The **active phase + profile** strings (substituted into the kernel template).
3. **File-pattern-matched guardrail documents** (loaded on-demand based on what the AI is about to edit).
4. **Phase-specific context** (loaded based on which phase is active).

This is how the framework keeps the system prompt at ~50 lines while still giving the AI the right context.

## Why this matters

The system-prompt tax is real (see [ai-ide-research/05-system-prompt-tax.md](../ai-ide-research/05-system-prompt-tax.md)). A 748-line always-loaded prompt forces the AI to choose between remembering rule 12 (top) and reasoning about the user's actual request (bottom). The assembler's job: **load only what's relevant to THIS turn**.

## Public interface

```python
def inject_kernel(profile: str, phase: str, budget: int) -> str: ...

def context_for_file(filepath: str) -> list[str]: ...   # list of guardrail doc paths

def context_for_phase(phase: str) -> list[str]: ...

def assemble(profile: str, phase: str, file_hints: list[str] | None = None) -> str: ...
```

## Algorithm: `inject_kernel(profile, phase, budget)`

```
1. Read packaged base-prompt.md (the 50-line kernel template).
2. Substitute {{PROFILE}}, {{PHASE}}, {{BUDGET}} placeholders.
3. Return the rendered string.
```

Caller hands the result to `UserPromptSubmit` hook for injection (see [15-HOOKS-RUNTIME.md](../spec/15-hooks-runtime.md)).

## Algorithm: `context_for_file(filepath)`

```
1. Read context/assembler.yaml (cached, mtime-keyed).
2. For each mapping entry:
     if fnmatch_any(filepath, entry["pattern"]):
       yield from entry["load"]    # list of paths to guardrail docs
3. De-dup, preserve order.
```

The `pattern` field uses glob syntax with `|` for alternation:

```
"**/*Controller.java|**/*Resource.java|**/*Endpoint.java"
```

Implement `fnmatch_any(path, pipe_separated_patterns)` as: split on `|`, check `fnmatch.fnmatch()` against each.

## Algorithm: `context_for_phase(phase)`

```
1. Read context/assembler.yaml.
2. Return doc["phase-context"][phase] or [].
```

## Algorithm: `assemble(profile, phase, file_hints)`

```
1. parts = [inject_kernel(profile, phase, budget_for(profile))]
2. parts += [read(doc) for doc in context_for_phase(phase)]
3. for f in file_hints or []:
     parts += [read(doc) for doc in context_for_file(f)]
4. return "\n\n".join(parts) [trimmed to budget]
```

Budget is from the profile (see [08-PROFILES.md](../spec/08-profiles.md)): patch=100, feature=300, migration=500, incident=100. If the assembled context exceeds budget, drop the lowest-priority file-pattern docs first; never drop the kernel.

## File layout

```
src/ai_ase/context/
├── base-prompt.md      # the 50-line kernel template
└── assembler.yaml      # file-pattern → guardrail map + phase-context
```

`base-prompt.md` is a Markdown file with `{{PROFILE}}`, `{{PHASE}}`, `{{BUDGET}}` placeholders. The reference version (verbatim) is in [artifacts/context/base-prompt.md](../artifacts/context/base-prompt.md).

`assembler.yaml` is the file-pattern map. Reference: [artifacts/context/assembler.yaml](../artifacts/context/assembler.yaml).

## Tests

- Kernel placeholders substitute correctly.
- Kernel length ≤ 60 lines after substitution (allow small margin).
- `context_for_file("src/UserController.java")` returns the REST API design doc.
- `context_for_file("Dockerfile")` returns the container guardrails.
- `context_for_phase("critic")` returns the critic's three docs.
- Assembled context fits under the profile budget.
- Caching: mtime change re-reads the YAML.

## Anti-patterns

| Don't | Because |
|---|---|
| Inline the kernel as a Python constant | It must be editable without redeploying. Keep it as a packaged Markdown file. |
| Skip the budget enforcement | Without it, you re-invent the 748-line prompt and lose V5. |
| Match patterns case-sensitively on Windows | Filesystem case-insensitivity is real. Lowercase before fnmatching. |
| Load all phase contexts at once | Only the active phase's. |

## Ground truth

[artifacts/context/base-prompt.md](../artifacts/context/base-prompt.md) and [artifacts/context/assembler.yaml](../artifacts/context/assembler.yaml).