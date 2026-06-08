# AI-ASE Examples

| File | What it shows |
|------|---------------|
| `01_basic_scan.py` | Programmatic code scanning with the rule engine |
| `02_mcp_integration.json` | MCP server config for Claude Code / VS Code |
| `03_claude_code_hooks.sh` | Installing deterministic hook enforcement |
| `04_trust_and_policy.py` | Trust scoring and policy decision engine |

## Quick CLI examples

```bash
# Scan current directory
ai-ase scan .

# Scan with specific profile (patch/feature/migration/infrastructure)
ai-ase scan src/ --profile migration

# List all active rules for a profile
ai-ase rules --profile feature

# Generate CI workflow
ai-ase adapter ci --profile feature

# View governance dashboard
ai-ase dashboard
```
