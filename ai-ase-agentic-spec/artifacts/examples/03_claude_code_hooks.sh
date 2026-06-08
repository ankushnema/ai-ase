#!/usr/bin/env bash
# Example: Install AI-ASE as Claude Code hooks (global)
#
# This makes AI-ASE fire on EVERY file write/edit in Claude Code.
# Violations are caught deterministically — the AI cannot bypass them.

# Install hooks globally (applies to all projects)
ai-ase hook install --global

# Or install for current project only
ai-ase hook install

# Verify installation
ai-ase hook status

# What happens after install:
# 1. PreToolUse(Write/Edit/Bash) → scans content, blocks BLOCK violations
# 2. PostToolUse(Write/Edit) → re-scans, records findings
# 3. Pre-commit → blocks commit if unresolved BLOCK findings exist
#
# The AI sees violation feedback inline and self-corrects.
# No human intervention needed for most violations.