# Examples

Concrete walk-throughs that ground the spec in real usage. If the rest of `publish/` is the blueprint, this folder is the photo of the finished building.

| File | What it shows | Read time |
|---|---|---|
| [quickstart.md](../examples/quickstart.md) | The 60-second story: install, init, scan, watch a hook block a real change. Best entry point if you want to *try* AI-ASE rather than read about it. | 3 min |
| [walkthrough.md](../examples/walkthrough.md) | An end-to-end feature delivery through all 5 phases (Archaeologist → Guardian → Architect → Critic → Reflector) for a sample payments endpoint. Shows the audit log entries, the phase gates, and the CAR feedback loop in action. | 8 min |

Both files reference governance behaviour described in [docs/05-architecture.md](../docs/05-architecture.md) and [docs/06-five-phases.md](../docs/06-five-phases.md), and they use rules from [catalogs/rules.md](../catalogs/rules.md). Cross-reference back to those when something in the walkthrough is unclear.

The implementation crosswalk \u2014 which module produces each audit event, which spec section owns each phase transition \u2014 lives in [spec/source-mapping.md](../spec/source-mapping.md).