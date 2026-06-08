# Package Configuration

## Purpose

`pyproject.toml`, test invocation, version policy. The "boring infrastructure" that makes the package installable and testable.

## `pyproject.toml`

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "ai-ase"
version = "1.3.0"
description = "Governance-as-a-service for AI-generated code"
readme = "README.md"
license = "Apache-2.0"
requires-python = ">=3.10"
authors = [{ name = "AI-ASE contributors" }]
keywords = ["ai", "governance", "mcp", "code-quality", "guardrails", "security"]
classifiers = [
  "Development Status :: 4 - Beta",
  "License :: OSI Approved :: Apache Software License",
  "Programming Language :: Python :: 3.10",
  "Programming Language :: Python :: 3.11",
  "Programming Language :: Python :: 3.12",
  "Topic :: Software Development :: Quality Assurance",
  "Topic :: Security",
]
dependencies = [
  "pyyaml>=6.0",
  "mcp[cli]>=1.0.0",
]

[project.optional-dependencies]
dev = ["pytest>=7.0", "pytest-cov>=4.0", "ruff>=0.4.0"]

[project.scripts]
ai-ase = "ai_ase.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["src/ai_ase"]

[tool.hatch.build]
include = [
  "src/ai_ase/**/*.py",
  "src/ai_ase/**/*.yaml",
  "src/ai_ase/**/*.yml",
  "src/ai_ase/**/*.md",
  "src/ai_ase/**/*.json",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--strict-markers -ra"

[tool.ruff]
line-length = 100
target-version = "py310"
```

## Decisions

| Decision | Choice | Reason |
|---|---|---|
| Build tool | Hatchling | PEP 621, no setup.py, simple |
| Min Python | 3.10 | `match`/`case`, union types, dataclass slots |
| Runtime deps | `pyyaml`, `mcp[cli]` only | V4 — every added dep is a maintenance liability |
| Wheel includes | `*.yaml`, `*.md`, `*.json` under the package | bundled rules / skills / templates ship with the wheel |
| Console script | `ai-ase = ai_ase.cli:main` | the single entry point |

## Test surface (minimum)

Target counts per module — meeting these means the module is "done":

| File | Tests | Covers |
|---|---|---|
| `test_engine.py` | ≥ 44 | validation, language detection, profile filtering, regex compilation graceful failure |
| `test_policy.py` | ≥ 54 | allow/deny/escalate, trust degradation, path/command boundaries |
| `test_trust.py` | ≥ 33 | weight redistribution, bands, policy integration |
| `test_audit.py` | ≥ 22 | JSONL append-only, correlation IDs, event schema |
| `test_skills.py` | ≥ 22 | registry, loader, trigger engine, event match |
| `test_phase_orchestrator.py` | ≥ 20 | transitions, `skills_satisfied()`, gate blocking |
| `test_server_tools.py` | ≥ 49 | every MCP tool + dry-run side-effect proofs |
| `test_hooks.py` | ≥ 25 | each hook event, BLOCK rejection, exit code 0 |
| `test_adapters.py` | ≥ 24 | copilot + ci generators, profile variants |
| `test_dashboard.py` | ≥ 15 | CLI + HTML output, confidence indicators |
| `test_mutation.py` | ≥ 16 | anti-circular-validation, boundary probes |
| `test_claim_integrity.py` | ≥ 27 | doc-to-runtime CI gate (claims in docs match the code) |

**Total target: ≥ 350 tests.** If you have fewer, you're probably missing something.

## Running tests

```bash
pip install -e ".[dev]"
pytest
pytest --cov=ai_ase --cov-report=term-missing
```

## Version policy

| Version | Meaning |
|---|---|
| 1.3.x | current stable line |
| 1.4.x | community feedback incorporated, additive |
| 2.0.0 | breaking change to schema / wire format |

The on-disk schemas (rule YAML, profile YAML, audit JSONL) are versioned independently — see each schema's spec. A package bump does not always bump those.

## Ground truth

No vendored file for this spec — `pyproject.toml` doesn't exist in `artifacts/`. Use this spec as the source.