# Rule Schema

## Purpose

Defines the YAML schema every rule file must follow. The `engine.load_rules()` loader (see [03-CORE-ENGINE.md](../spec/03-core-engine.md)) consumes this schema. The catalog in [../catalogs/rules.md](../catalogs/rules.md) is the human-readable summary.

## File location

```
src/ai_ase/rules/
├── _registry.yaml                          # index of rule files
├── _groups.yaml                            # category → group mapping
├── security/
│   ├── secrets-detection.rules.yaml
│   ├── injection-prevention.rules.yaml
│   ├── crypto-standards.rules.yaml
│   └── web-security.rules.yaml
├── code-quality/
├── type-safety/
├── sre-reliability/
├── devops/
└── ai-engineering/
```

Filename convention: `{name}.rules.yaml`. The `.rules.yaml` suffix is required — the loader uses `rglob("*.rules.yaml")`.

## File-level schema

```yaml
category: "Security: Secrets Detection"
description: "Detects hardcoded credentials, API keys, and tokens"
version: "1.3.0"

rules:
  - id: ...
  - id: ...
```

## Rule-level schema (every field)

```yaml
- id: VR-01                              # REQUIRED. Catalog-wide unique. Format: VR-NN[a-z]?
  name: "Hardcoded Password"             # REQUIRED. Short human label.
  action: BLOCK                          # REQUIRED. BLOCK | WARN
  file-types:                            # REQUIRED. List. ALL | CODE | JAVA | PYTHON | JS | CSHARP | GO | RUST | RUBY | PHP | CONFIG | DOCKER
    - ALL
  skip-tests: true                       # OPTIONAL. Skip files matching */test*, *Test.java, etc. Default: false.
  pattern: |                             # REQUIRED. YAML block scalar. Raw regex. Loader strips trailing \n.
    (?i)(password|passwd|pwd)\s*[=:]\s*["'][^"']{3,}
  description: "Hardcoded password found in source code"   # REQUIRED.
  severity: critical                     # REQUIRED. critical | high | medium | low
  guardrail-ids:                         # OPTIONAL. Cross-reference IDs.
    - SEC-001
    - OWASP-A07
  profiles:                              # REQUIRED. Subset of [patch, feature, migration, incident]. BLOCK rules MUST include all four.
    - patch
    - feature
    - migration
    - incident
  groups:                                # OPTIONAL. Categorization for `_groups.yaml`.
    - security-critical
  rationale: "Credentials in source code are visible to anyone with repo access and leak to git history forever."
  fix-guidance: "Use os.environ.get('PASSWORD') or a secrets manager (AWS Secrets Manager, HashiCorp Vault)."
  given-when-then: |                     # OPTIONAL. BDD-style.
    GIVEN a developer writes code containing a credential
    WHEN the file is saved or scanned
    THEN the scanner emits a BLOCK violation
```

## Pattern rules (critical)

1. **Always use YAML block scalar `|`** — preserves the regex literally.
2. **Never use single quotes** — single quotes in YAML require doubling (`''`).
3. **Never use double quotes** — double quotes treat `\s`, `\b`, `\d` as YAML escapes.
4. **Loader strips trailing `\n`** — block scalars add one. Engine handles this.
5. **Test patterns standalone before adding** — `python -c "import re; print(re.search(r'PATTERN', 'TEST LINE'))"`.
6. **Use `(?i)` for case-insensitivity** — don't rely on YAML flags.
7. **No backreferences in performance-sensitive paths** — they're O(n²).

## Structural checks

Some rules can't be expressed as a single-line regex (e.g., "every controller has a @RequestMapping above it"). Mark these:

```yaml
pattern: |
  STRUCTURAL_CHECK
```

The engine skips `STRUCTURAL_CHECK` and `NO_PATTERN` patterns. A separate module (`structural.py`, optional, post-MVP) walks the AST for these. The MVP ships with the 8 structural checks listed in the catalog as no-ops awaiting implementation.

## Cross-referenced rules

A rule ID may appear in more than one `*.rules.yaml` file when the same pattern legitimately belongs to multiple categories. The registry counts it once, the scanner loads it once (whichever file wins the file-walk order). Current cross-references:

- **VR-43** ("String Concat in Logger") — primary in `code-quality/logging.rules.yaml`, cross-referenced from `sre-reliability/observability.rules.yaml`. Logging concern, observability concern; same regex.
- **VR-14 / VR-30** ("Thread Creation Without Pool") — appear in both `code-quality/performance.rules.yaml` and `sre-reliability/concurrency.rules.yaml`. Intentional duplicates kept separate so a profile that activates only the performance group still gets the rule.

When authoring a new rule, prefer a single canonical file. Add a cross-reference only when a profile would otherwise miss the rule.

## `_registry.yaml` format

```yaml
rules:
  - file: security/secrets-detection.rules.yaml
    category: Security
    count: 6
    block: 6
    warn: 0
  - file: security/injection-prevention.rules.yaml
    category: Security
    count: 3
    block: 3
    warn: 0
  # ... one entry per rule file
```

Used by the CLI's `ai-ase rules` command and the dashboard for fast inventory without loading every YAML.

## `_groups.yaml` format

```yaml
groups:
  security-critical:
    description: "Rules that must never be relaxed"
    rules: [VR-01, VR-02, VR-03, VR-04, VR-05, VR-06]
  monetary-types:
    description: "Money/currency type safety"
    rules: [VR-10, VR-10b, VR-11]
  # ...
```

Used for selective profile activation and reporting.

## BLOCK-vs-WARN policy

| Action | When | Profile policy |
|---|---|---|
| `BLOCK` | The violation is unambiguous, has a clear fix, and shipping it is dangerous. | Must apply to ALL profiles (patch, feature, migration, incident). |
| `WARN` | The violation is contextual, has tradeoffs, or fix is non-trivial. | May be profile-scoped. |

If you can't commit to "this should always block in production code", make it WARN.

## Schema validation tests

- Every rule file parses as YAML.
- Every rule has the required fields (`id`, `name`, `action`, `file-types`, `pattern`, `description`, `severity`, `profiles`).
- Every `pattern` compiles as a valid regex (or is `STRUCTURAL_CHECK` / `NO_PATTERN`).
- Every `id` is unique catalog-wide.
- Every BLOCK rule includes all four profiles.
- Every `severity` value is in the allowed set.
- `_registry.yaml` counts match actual file contents.

These tests live in `test_engine.py` or a dedicated `test_rule_schema.py`.

## Adding a new rule (workflow)

1. Pick a file under `rules/<category>/<filename>.rules.yaml` (create if needed).
2. Add the rule with all required fields.
3. Update `_registry.yaml` counts.
4. Add to `_groups.yaml` if it belongs to a group.
5. Add a fixture under `tests/fixtures/` that triggers the rule.
6. Add a test in `test_engine.py` asserting the violation fires.
7. PR with rationale + expected false-positive rate.

## Ground truth

The 16 rule files in [artifacts/rules/](../artifacts/rules/) are the canonical examples of this schema. Copy their shape verbatim.