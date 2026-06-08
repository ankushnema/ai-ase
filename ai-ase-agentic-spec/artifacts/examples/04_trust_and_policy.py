"""Example: Use trust scoring and policy decisions programmatically."""

from ai_ase.trust import compute
from ai_ase.policy import evaluate

# Trust score: weighted combination of quality signals
result = compute(
    scanner_pass_rate=95.0,       # 95% of guardrail rules pass
    test_coverage=82.0,           # 82% test coverage
    mutation_kill_rate=80.0,      # 80% mutation kill rate
    human_review_depth=50.0,      # cursory review
)

print(f"Trust score: {result.score}/100")
print(f"Trust band: {result.band.value}")
print(f"Components: {[c.name for c in result.components]}")
print()

# Policy engine: maps (tool + phase + profile + trust) -> allow/deny/escalate
decision = evaluate(
    tool_name="Write",
    phase="reflector",
    profile="feature",
    trust_score=result.score,
)

print(f"Policy decision: {decision.decision.value}")
print(f"Reason: {decision.reason}")
print(f"Matched policy: {decision.policy_id}")
print()

# Low trust triggers denial
low_trust = evaluate(
    tool_name="Write",
    phase="reflector",
    profile="migration",
    trust_score=25.0,
)
print(f"Low trust decision: {low_trust.decision.value}")
print(f"Reason: {low_trust.reason}")