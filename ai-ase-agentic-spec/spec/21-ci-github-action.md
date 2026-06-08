# CI GitHub Action

## Purpose

`action/action.yml` is the composite GitHub Action that wraps `ai-ase scan` so any repo can add governance to its PR pipeline with three lines of YAML.

## File: `action/action.yml`

```yaml
name: 'AI-ASE Governance Scan'
description: 'Scan code against AI-ASE governance rules. Fails on BLOCK violations.'
author: 'AI-ASE contributors'
branding:
  icon: 'shield'
  color: 'blue'

inputs:
  profile:
    description: 'Governance profile: patch | feature | migration | incident'
    default: 'feature'
    required: false
  path:
    description: 'Path to scan (relative to repository root)'
    default: '.'
    required: false
  python-version:
    description: 'Python version to use'
    default: '3.11'
    required: false
  ai-ase-version:
    description: 'Pin a specific ai-ase version (default: latest stable)'
    default: ''
    required: false
  fail-on-warn:
    description: 'Fail the action if any WARN-level violations are found (in addition to BLOCK)'
    default: 'false'
    required: false

outputs:
  block-count:
    description: 'Number of BLOCK violations found'
    value: ${{ steps.scan.outputs.blocks }}
  warn-count:
    description: 'Number of WARN violations found'
    value: ${{ steps.scan.outputs.warns }}

runs:
  using: 'composite'
  steps:
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: ${{ inputs.python-version }}

    - name: Install ai-ase
      shell: bash
      run: |
        if [ -n "${{ inputs.ai-ase-version }}" ]; then
          pip install "ai-ase==${{ inputs.ai-ase-version }}"
        else
          pip install ai-ase
        fi

    - name: Run scan
      id: scan
      shell: bash
      run: |
        set +e
        ai-ase scan ${{ inputs.path }} --profile ${{ inputs.profile }} --json > scan.json
        EXIT=$?
        BLOCKS=$(jq '.summary.blocks' scan.json)
        WARNS=$(jq '.summary.warns' scan.json)
        echo "blocks=$BLOCKS" >> "$GITHUB_OUTPUT"
        echo "warns=$WARNS"  >> "$GITHUB_OUTPUT"
        if [ "${{ inputs.fail-on-warn }}" = "true" ] && [ "$WARNS" -gt 0 ]; then
          exit 1
        fi
        exit $EXIT
```

## Sample workflow

`.github/workflows/ai-ase-scan.yml`:

```yaml
name: AI-ASE Governance
on:
  pull_request:
    branches: [main, master, develop]
jobs:
  scan:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write       # for the comment step
    steps:
      - uses: actions/checkout@v4
      - id: ai-ase
        uses: ai-ase/scan@v1
        with:
          profile: feature
      - if: failure()
        name: Comment violations on PR
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const data = JSON.parse(fs.readFileSync('scan.json', 'utf-8'));
            const body = formatComment(data);   // user-provided formatter
            await github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body,
            });
```

## PR comment format

The comment should be the dashboard's CLI output (no ANSI), wrapped in a `<details>` so it doesn't dominate the PR thread. Show a one-line summary in the summary, full violations in the details.

## Branching strategy

The action ships as `ai-ase/scan@v1`. The `v1` tag is moved forward as compatible versions release. Breaking changes go to `v2`.

## Security

| Concern | Mitigation |
|---|---|
| Running on PRs from forks | Use `pull_request_target` only when needed; default `pull_request` runs in the fork's permissioned context. |
| `pip install` from PyPI on every run | Pin via `ai-ase-version` input. Cache via `actions/cache` in a follow-up. |
| Posting comments on every PR | Use the `permissions:` block; least privilege. |
| Exfiltrating code via the scan | The action runs locally on the runner. No data sent off-runner. The audit log stays in the workflow workspace. |

## Tests

The action itself isn't a Python module so the Python test suite doesn't cover it. Instead:

- `.github/workflows/test-action.yml` runs the action against a fixture repo on every release tag.
- Fixture has known BLOCK violations and asserts the action exits non-zero.
- Fixture has a clean variant and asserts the action exits zero.

## Anti-patterns

| Don't | Because |
|---|---|
| Run as a Docker action | Composite is faster, simpler, no image registry to manage. |
| Hard-code Python version in `runs.steps` | Use the `python-version` input. |
| Skip `set +e` before the scan | Without it, `pipefail` aborts before you can capture exit code. |
| Add a "block all WARN" mode | `fail-on-warn: true` already does this. No new flag. |
| Post a comment for clean scans | Noisy. Comment only on violations. |

## Ground truth

No vendored file. The shape mirrors the GitHub composite-action conventions; nothing AI-ASE-specific beyond the `ai-ase scan` invocation.