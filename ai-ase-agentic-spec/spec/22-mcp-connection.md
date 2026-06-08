# MCP Connection

## Purpose

This is the **client-side** wiring spec — what file an AI IDE needs to find the MCP server, and what it looks like. Not a Python module. The CLI's `ai-ase init` generates this file; users may also write it by hand.

## The contract

The MCP standard says: an AI IDE reads a config file (`.mcp.json`, or a tool-specific equivalent) on startup, finds entries under `mcpServers`, and spawns each as a subprocess. Communication is JSON-RPC over stdio.

For AI-ASE that means: the file points at `ai-ase serve`, which is the CLI subcommand that runs the FastMCP server (see [05-MCP-SERVER.md](../spec/05-mcp-server.md)).

## Canonical `.mcp.json` (workspace root)

```json
{
  "mcpServers": {
    "ai-ase-governance": {
      "command": "ai-ase",
      "args": ["serve"]
    }
  }
}
```

Three things to notice:

1. **`command` is the package's installed entry point.** No absolute paths — works on any machine after `pip install ai-ase`.
2. **`args` is just `serve`.** No flags. The server discovers everything (rules, profile, audit path) from the current working directory.
3. **The server is keyed by name (`ai-ase-governance`).** Multiple MCP servers can coexist in the same `.mcp.json`.

## Per-IDE locations

| AI IDE | Where the file lives |
|---|---|
| Claude Code | `.mcp.json` at workspace root |
| VS Code (MCP-enabled) | `.mcp.json` at workspace root |
| Cursor | `.cursor/mcp.json` |
| Others (Continue, Cline, etc.) | check the IDE's docs; format is the same |

`ai-ase init` writes `.mcp.json` to the workspace root by default. For Cursor, run `ai-ase init --output .cursor/mcp.json` (the CLI accepts an `--output` flag for this).

## How it actually works

```
1. IDE startup
   → reads .mcp.json
   → finds "ai-ase-governance"
   → spawns subprocess: `ai-ase serve`

2. Server announces capabilities (JSON-RPC initialize handshake)
   ← server writes tool list to stdout
   → IDE registers tools in its tool palette

3. During a coding session
   → AI decides to call `validate_code(...)`
   → IDE writes JSON-RPC request to server stdin
   ← server runs the tool, writes response to stdout
   → IDE incorporates response into the AI's context

4. Session ends
   → IDE sends shutdown notification
   → server exits cleanly
   → subprocess closes
```

The subprocess stays alive for the duration of the IDE's session. It's stateless from request to request (each tool call is independent), but it caches loaded rules in-memory.

## Worked example: a tool call

```jsonc
// IDE → server (request)
{
  "jsonrpc": "2.0",
  "id": 42,
  "method": "tools/call",
  "params": {
    "name": "validate_code",
    "arguments": {
      "code": "password = \"hunter2\"",
      "filename": "auth.py",
      "profile": "feature"
    }
  }
}

// Server → IDE (response)
{
  "jsonrpc": "2.0",
  "id": 42,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "## Scan Result: auth.py\n**Profile:** feature  **Status:** BLOCKED (1 BLOCK)\n\n### BLOCK\n| Rule | Line | Issue |\n|---|---|---|\n| VR-01 | 1 | Hardcoded password ... |\n\n### Fix Guidance\n**VR-01:** Use os.environ.get('PASSWORD') ..."
      }
    ]
  }
}
```

## Discovery hints (optional, recommended)

Some IDEs surface a description for each MCP server. Add a sibling file `.ai-ase/server-metadata.json` (the CLI writes this):

```json
{
  "name": "ai-ase-governance",
  "description": "AI-ASE governance — code validation, rule lookup, trust scoring",
  "version": "1.3.0",
  "tools": [
    "validate_code", "get_active_rules", "governance_profile",
    "check_business_rule", "compute_trust_score", "get_skill",
    "report_generation", "check_policy", "dry_run_preview"
  ]
}
```

IDEs that read this surface a nicer card in their MCP panel. IDEs that don't, ignore it harmlessly.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| "MCP server failed to start" | `ai-ase` not on PATH. Run `which ai-ase` (Linux/macOS) or `where ai-ase` (Windows). |
| "Tool not registered" | The IDE's MCP support is off or in a "preview" flag. Check IDE settings. |
| Tools listed but never called | The AI IDE's system prompt doesn't mention them. Check `.github/copilot-instructions.md` or equivalent. |
| Tools called but returning errors | Look at `.ai-ase/audit-log.jsonl` for the corresponding `tool_call` events; check stderr from the subprocess. |
| Hooks fire but server doesn't | `serve` and hooks are independent. Hooks run via `ai-ase hook handle`, not the MCP server. |

## What this spec does NOT cover

- The MCP protocol itself (a separate standard — see the MCP spec).
- How to add a new tool (see [05-MCP-SERVER.md](../spec/05-mcp-server.md)).
- IDE-specific MCP configuration UI (check the IDE's docs).

## Ground truth

[artifacts/examples/02_mcp_integration.json](../artifacts/examples/02_mcp_integration.json) — the working example from the reference implementation.