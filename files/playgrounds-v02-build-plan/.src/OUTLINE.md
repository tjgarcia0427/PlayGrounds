# Playgrounds v0.2 Build Plan — outline

Section: Executive decision
Claim: v0.2 should make Playgrounds a measured, central-orchestrator system that defaults to one agent and earns the right to add specialists.
Source: Current MVP/GOAL files; Nature scaling study; Anthropic research system report.

Section: What changes from v0.1
Claim: Preserve the working protocol, dashboard, credits, and MCP connector while replacing heuristic routing, free-form outputs, and binary reputation with auditable contracts.
Source: MVP README, server.py, mcp_server.py, credit-economy design.

Section: Eight research implications become eight product rules
Claim: Each research finding maps to a concrete v0.2 behavior, schema, metric, and release gate.
Source: AI-agent research sweep; primary sources in References.

Section: The orchestrator becomes the control plane
Claim: A hub-and-spoke orchestrator with task and progress ledgers contains coordination errors and makes replanning explicit.
Source: Magentic-One; Nature scaling study; MAST failure taxonomy.

Section: Contracts replace chat as the unit of work
Claim: Structured task envelopes and immutable artifact records reduce duplication, ambiguity, and unverifiable claims.
Source: A2A specification; Anthropic research system; CAID.

Section: A2A discovers agents; MCP stays the tool boundary
Claim: Agent Cards and A2A task semantics complement, rather than replace, the existing MCP connector.
Source: Official A2A and MCP specifications.

Section: Routing learns from verified outcomes
Claim: The router should estimate task-agent utility from outcomes, cost, latency, and task structure instead of ranking declared model names.
Source: RouteLLM; Nature scaling study; current suggest_agents heuristic.

Section: Four agents is the standing playground ceiling
Claim: Solo execution is the baseline; only low-coupling, decomposable tasks may fan out, and no playground may exceed four registered agents. The MVP already enforces the cap in registration and exposes capacity in the dashboard.
Source: User decision; current server.py and dashboard.html; Nature scaling study; Anthropic research system; AgentPrune.

Section: Verification controls both trust and learning
Claim: Deterministic checks and evidence-backed review must gate task completion, reputation updates, router labels, and payouts.
Source: c-CRAB; CAID; current human verification flow.

Section: Reputation absorbs noise instead of punishing every miss
Claim: Capability-specific, confidence-weighted scores with a neutral deadband are safer than a global success rate.
Source: Current agent_stats design; noisy verifier evidence from research sweep.

Section: Credits pay for marginal verified utility
Claim: Bounties should fund independently attributable contributions and verification, not token usage or mere participation.
Source: Current escrow economy; research implications on redundancy and verification.

Section: Trust gates public exposure
Claim: Tenant isolation, authenticated agent identity, scopes, sandboxing, signed receipts, and abuse controls are prerequisites, not later polish.
Source: A2A discovery security guidance; MCP architecture; project constraints.

Section: Six implementation increments ship v0.2 safely
Claim: Schema and observability come first; routing and economics run in shadow mode before they control real assignments or payouts.
Source: Engineering synthesis of the above.

Section: Acceptance metrics decide whether v0.2 worked
Claim: A matched-budget local evaluation must show higher verified utility per credit without worse security or operational reliability.
Source: Nature matched-compute evaluation; research sweep operational hypothesis.

Section: Avatar production follows the platform refinements
Claim: The visual system should fuse the responsive feel of the Muse assistant avatar with an original stuffed-animal/chibi character language, then map stable platform states to restrained, readable animation.
Source: User design decision; planned dashboard and ledger state model.
