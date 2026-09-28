# Multi-Agent Collaboration: Research Survey for "Playgrounds" Platform Design

**Mission:** Survey how AI researchers get LLM agents to communicate and work together effectively, to inform the design of "Playgrounds" — a platform where heterogeneous AI agents (different models — Claude, GPT, open models — owned by different people) collaborate on shared goals, with tasks delegated across agents and a credit economy.

**Date researched:** 2026-09-27 (all times UTC). Verification flags: `verified live` = confirmed in real browser this run; `index` = confirmed via search-index/abstract pages this run. Confidence per paper is noted where secondary sources were used.

---

## Summary

Five areas were surveyed with 29 papers/artifacts (2023–2026, arXiv preferred). Headline findings:

1. **Communication protocols:** The industry is converging on a two-layer stack — **A2A** (Google → Linux Foundation, spec 1.0.0) for agent↔agent delegation and **MCP** (Anthropic) for agent↔tool access; a 2025 survey (arXiv:2505.02279) adds ACP (structured messaging) and ANP (decentralized identity, DID-based) as the longer-term cross-org layer. Agent Cards are the discovery primitive. Key gap: **no standardized cryptographic agent identity/message attribution** — the trust layer is still open.
2. **Orchestration:** Centralized **orchestrator-worker with an explicit progress ledger and re-planning loop** (Magentic-One, arXiv:2411.04468) is the best-verified pattern; structured intermediate artifacts between agents (MetaGPT) beat free chat; broadcast group discussion is the worst planning strategy (MultiAgentBench, ACL 2025). Keep teams to ~2–4 agents.
3. **Delegation/routing:** Cascades with a learned answer-scorer (FrugalGPT: up to 98% cost cut at GPT-4 parity), preference-data routers that transfer across model pairs (RouteLLM: >2× cost cut), and cheap difficulty predictors (Hybrid LLM: 40% fewer large-model calls). For multi-step agent trajectories, pure routing beats cascading (Brick, 2026) because cascade costs compound per step.
4. **Incentives/credit:** QMIX (monotonic value mixing), COMA (counterfactual baselines), MAPPO (simple-but-surprisingly-strong) are the canonical MARL credit-assignment trio. For LLM marketplaces, **deadbanded reputation penalties need no ground truth** (CARP, 2026) — directly applicable to a credit economy. Critical warning (arXiv:2608.14613): mechanism-theoretic incentive compatibility does **not** automatically transfer to LLM-agent behavior; verify empirically.
5. **Frontier (2025–2026):** DeepMind's "Towards a Science of Scaling Agent Systems" (arXiv:2512.08296, Dec 2025, revised Apr 2026) is the most rigorous evidence: multi-agent helps up to +80.8% on decomposable tasks but hurts −70% on sequential ones; capability saturation means multi-agent is only worthwhile when the single-agent baseline is weak. Heterogeneity helps at scale (≥5 agents) but adds overhead in small teams (AgentNet); cross-org/heterogeneous work (Eywa, MAPoRL/CoMLRL) shows gains but is early.

**Design implications** (8 actionable lessons) are at the end of this report.

---

## 1. AGENT COMMUNICATION PROTOCOLS

### Paper 1: Agent2Agent (A2A) protocol — Google (Apr 2025) → Linux Foundation, spec v1.0.0
- **Sources:** https://dev.to/promptmaster/what-is-the-agent2agent-protocol-a-complete-introduction-to-a2a-4p (`index`); https://github.com/firewalker06/tycho/blob/HEAD/docs/research/a2a-protocol-research.md (`index`); https://github.com/sammyview80/aglack/blob/HEAD/docs/agent-to-agent-communication-research.md (`index`). Read 2026-09-27.
- **What they tried:** An open, vendor-neutral protocol for agent↔agent collaboration as first-class entities (not tools): discovery via JSON **Agent Cards** at `/.well-known/agent-card.json` (name, version, capabilities like streaming/pushNotifications, skills with input/output modes, security schemes, JWS signatures); messaging via JSON-RPC 2.0 over HTTP with SSE streaming (gRPC and REST bindings also exist); task lifecycle `SUBMITTED → WORKING → COMPLETED|FAILED|CANCELED|REJECTED` plus `INPUT_REQUIRED`/`AUTH_REQUIRED` interrupt states; multi-turn context via server-generated opaque `contextId`; OAuth 2.0 auth; SDKs for Python/JS/Java/Go/.NET; 150+ organizations backing.
- **What worked:** Cross-framework interop without shared memory, tools, or internals — agents from LangGraph, CrewAI, ADK etc. can delegate to each other. Long-running tasks with status updates, artifact streaming, and in-task auth chaining across hops are natively supported.
- **What failed / didn't generalize:** No native **group-chat primitive** — multi-agent systems are composed from pairwise client/remote relationships, so the platform must build its own orchestration/broadcast layer on top. Surveys note **no standardized cryptographic identity / message-attribution mechanism** (which model produced which message can't be verified), a problem for high-stakes deployments.
- **Takeaway for Playgrounds:** Adopt A2A's Agent Card as the capability-advertisement and discovery primitive (signed cards with declared skills, costs, and auth), but build orchestration (group tasks, broadcast, consensus) as a platform layer above pairwise A2A channels.

### Paper 2: Model Context Protocol (MCP) — Anthropic (late 2024)
- **Sources:** https://github.com/jgwill/coaiajs/blob/HEAD/articles/academic/model-context-protocol-interagent.md (`index`); https://github.com/martinyeung5/report_eassy/blob/HEAD/Model%20Context%20Protocol%20(MCP):%20Landscape,%20Security%20Threats,%20and%20Future%20Research%20Directions.md (`index`). Read 2026-09-27.
- **What they tried:** "USB-C for AI" — JSON-RPC 2.0 standard connecting models to tools/data; dual transport (stdio local, HTTP distributed); three primitives (tools, resources, prompts) plus sampling; dynamic tool discovery, session state, human-in-the-loop safety boundaries.
- **What worked:** Solves the N×M agent-tool integration problem; modular, observable, composable agent systems.
- **What failed / didn't generalize:** MCP is agent↔**tool**, not agent↔agent — it does not help agents talk to each other. First systematic security study defines a 16-activity server lifecycle and 16 threat scenarios across 4 attacker types — i.e., MCP's attack surface is now well-mapped and must be hardened (prompt injection via tool descriptions, etc.).
- **Takeaway for Playgrounds:** Use MCP strictly as the tool-access layer (every agent's tools exposed uniformly), and A2A as the agent-collaboration layer. Budget for MCP threat-modeling (tool-description injection, malicious servers) from day one.

### Paper 3: "A Study on the MCP × A2A Framework for Enhancing Interoperability of LLM-based Autonomous Agents" — Jeong (Samsung SDS), arXiv:2506.01804 (2025)
- **Source:** https://arxiv.org/abs/2506.01804 (abstract verified via `index`). Read 2026-09-27.
- **What they tried:** First integrated technical analysis + implementation methodology of A2A and MCP together (prior work studied each alone).
- **What worked:** Confirmed the two protocols are complementary: A2A for peer collaboration among heterogeneous agents, MCP for structured I/O to external tools/resources; the combination addresses interoperability in complex agent ecosystems.
- **What failed / didn't generalize:** An integration study, not an empirical bake-off — no head-to-head performance numbers.
- **Takeaway for Playgrounds:** Deploy both protocols at different layers (A2A = who talks to whom; MCP = what tools each agent can use) rather than picking one.

### Paper 4: "A Survey of Agent Interoperability Protocols: MCP, ACP, A2A, ANP" — Ehtesham et al., arXiv:2505.02279 (2025)
- **Source:** https://github.com/yusufarbc/mcp-agentic-ai-security/blob/HEAD/reference/03_agent_interoperability_protocols.md (`index`; contains the paper's abstract and roadmap). Read 2026-09-27. *Confidence: medium — survey, single secondary source; conclusions are qualitative.*
- **What they tried:** Compared MCP, ACP (Agent Communication Protocol, RESTful, MIME-typed multipart, session-aware), A2A, and ANP (Agent Network Protocol: open-network discovery via W3C DIDs and JSON-LD graphs) across interaction modes, discovery, communication patterns, security.
- **What worked:** Produced a phased adoption roadmap: MCP for tool access → ACP for structured multimodal session-aware messaging → A2A for collaborative task execution → ANP for decentralized agent marketplaces.
- **What failed / didn't generalize:** Qualitative comparison; no empirical evaluation of the protocols against each other.
- **Takeaway for Playgrounds:** ANP's DID-based decentralized identity is the direction for the hardest cross-org trust problem (agents owned by different people). Plan the identity layer to evolve toward DIDs/verifiable credentials.

### Paper 5: "Emergent social conventions and collective bias in LLM populations" — Ashery, Aiello, Baronchelli, arXiv:2410.08948 (2024; Science Advances 2025)
- **Source:** https://arxiv.org/abs/2410.08948 (`index`; abstract page read). Read 2026-09-27.
- **What they tried:** Decentralized populations of LLM agents in naming-game-style interactions to see whether they bootstrap social conventions.
- **What worked:** Spontaneous emergence of universally adopted social conventions with no explicit programming.
- **What failed / didn't generalize:** Strong **collective biases emerged even when no agent was individually biased**, and **committed adversarial minority groups could impose alternative conventions** on the majority (critical-mass/tipping dynamics).
- **Takeaway for Playgrounds:** Do not rely on emergent conventions for coordination or pricing — they drift from designer intent and are vulnerable to minority capture. Use explicit, auditable conventions (message schemas, fee schedules) and build sybil/adversarial protections into the reputation system.

### Paper 6: "Decentralised Emergence of Robust and Adaptive Linguistic Conventions…" — arXiv:2401.08461 (2024)
- **Source:** https://arxiv.org/abs/2401.08461 (abstract verified via `index`). Read 2026-09-27.
- **What they tried:** Populations of agents converging on symbolic label ↔ concept conventions through **local pairwise** interactions, grounded in continuous feature spaces.
- **What worked:** Converged on communicatively effective, coherent, human-interpretable conventions; robust to sensor defects, noisy observations, uncalibrated sensors, and heteromorphic populations; conventions self-adapt to environmental change.
- **What failed / didn't generalize:** Grounded perceptual naming games, not task-oriented LLM collaboration — transfer to open-ended agent platforms is untested.
- **Takeaway for Playgrounds:** If any convention-learning is needed, pairwise local interactions suffice (no global broadcast needed), but prefer designed protocols for anything economically load-bearing.

**Section verdict (confidence: medium-high):** The A2A+MCP two-layer stack is the industry consensus and the safest standards bet; the trust/identity layer (DIDs, signed cards, verifiable receipts) is the biggest open gap and the one Playgrounds must design itself.

---

## 2. MULTI-AGENT ORCHESTRATION FRAMEWORKS

### Paper 7: AutoGen — Wu et al. (Microsoft), arXiv:2308.08155 (2023)
- **Source:** https://arxiv.org/abs/2308.08155 (`index`; abstract page read). Read 2026-09-27.
- **What they tried:** Open-source framework where agents are customizable and *conversable*, operating in modes combining LLMs, human inputs, and tools; conversation patterns (two-agent chat, group chat with speaker selection, nested chats) programmable in natural language or code.
- **What worked:** Generic infrastructure validated across math, coding, QA, operations research, online decision-making, entertainment; "conversable agent" abstraction became widely adopted.
- **What failed / didn't generalize:** Framework, not a coordination policy — performance depends entirely on the conversation pattern the developer writes; naive patterns (e.g., under-communicating SOPs) fail (cf. MegaAgent's Gobang comparison where AutoGen's simple SOP got stuck).
- **Takeaway for Playgrounds:** Treat conversation as the coordination substrate and ship *curated, tested* conversation patterns rather than letting every user invent topologies — "simple topology first" (two-agent chat, then group chat).

### Paper 8: Magentic-One — Fourney et al. (Microsoft Research), arXiv:2411.04468 (2024)
- **Source:** https://arxiv.org/abs/2411.04468 (abstract text read via `index`). Read 2026-09-27. *Confidence: medium — abstract + secondary writeups, not full paper.*
- **What they tried:** Lead **Orchestrator** agent with a **dual-ledger** design: outer Task Ledger (facts, guesses, plan) and inner Progress Ledger (step progress, agent assignments); orchestrator plans, delegates to specialists (WebSurfer, FileSurfer, Coder, ComputerTerminal), tracks progress, and **re-plans to recover from errors**; modular team (add/remove agents without prompt tuning); AutoGenBench for rigorous agentic evaluation.
- **What worked:** Statistically competitive with SOTA on GAIA, AssistantBench, WebArena **without task-specific modifications** to capabilities or collaboration; mixed-model configs tested (e.g., o1-preview for orchestrator/coder outer loop, GPT-4o elsewhere).
- **What failed / didn't generalize:** Single-vendor model stack in main evals; orchestrator is a single point of failure/bottleneck.
- **Takeaway for Playgrounds:** The explicit progress ledger + re-planning loop is the best-documented error-recovery pattern — copy it: every delegated task gets a tracked ledger entry, and the orchestrator re-plans on failure rather than failing the whole job.

### Paper 9: MetaGPT — Hong et al., arXiv:2308.00352 (2023; v7 2024)
- **Source:** https://arxiv.org/abs/2308.00352 (`index`; abstract page read). Read 2026-09-27.
- **What they tried:** Encoded human Standardized Operating Procedures (SOPs) into prompt sequences; assembly-line role assignment (Product Manager → Architect → Engineer → QA); agents with domain expertise **verify intermediate results**.
- **What worked:** More coherent solutions on collaborative software-engineering benchmarks than chat-based multi-agent systems; SOPs + verification specifically target cascading hallucinations from naively chained LLMs.
- **What failed / didn't generalize:** SOPs are rigid and domain-specific (great for software, less so for open-ended tasks); complex implementation; structured prompts limit flexibility.
- **Takeaway for Playgrounds:** The load-bearing insight is **structured intermediate artifacts** (PRDs, design docs, schemas) passed between agents — typed, reviewable handoffs beat free-text chat for delegation. Use SOP-style phase gates for tasks with a known shape.

### Paper 10: CAMEL — Li et al., arXiv:2303.17760 (2023)
- **Source:** arXiv:2303.17760 via secondary research notes (`index`). Read 2026-09-27. *Confidence: medium.*
- **What they tried:** Role-playing framework with "inception prompting": an AI user and AI assistant with assigned roles collaborate via structured dialogue; showed emergent task decomposition without explicit planning.
- **What worked:** Autonomous cooperation with minimal human input; useful for simulation/roleplay research and conversational dataset generation.
- **What failed / didn't generalize:** **Conversation deviation and role flipping** — agents drift from assigned roles; static conversation patterns; no tool support in the original.
- **Takeaway for Playgrounds:** Role prompts alone are fragile — any role-based delegation needs explicit turn-taking, termination conditions, and role-adherence checks (a verifier or the orchestrator's ledger).

### Paper 11: ChatDev — Qian et al., arXiv:2307.07924 (ACL 2024)
- **Source:** https://arxiv.org/abs/2307.07924 via two independent GitHub research notes (`index`): https://github.com/jmagly/aiwg/blob/HEAD/docs/references/REF-012-chatdev-multi-agent-software.md and https://github.com/peva3/anchor/blob/HEAD/research/papers/full/chatdev-2307.07924.md. Read 2026-09-27. *Confidence: medium — two secondaries agree on numbers.*
- **What they tried:** Virtual software company (CEO, CTO, Programmer, Reviewer, Tester); each phase runs an instructor↔assistant **ChatChain**; "communicative dehallucination" — agents must request specifics before answering.
- **What worked:** Quality score 0.3953 vs MetaGPT 0.1523 vs GPT-Engineer 0.1419 (~159% over best baseline); Completeness 0.56, Executability 0.88, Consistency 0.80.
- **What failed / didn't generalize:** Results are software-domain-specific; multi-phase chat chains are token-heavy.
- **Takeaway for Playgrounds:** Build a **clarification-request mechanism** into delegation: an agent must ask for missing specifics before producing output — this single rule measurably reduces cascading errors across agent handoffs.

### Paper 12: MultiAgentBench — arXiv:2503.01935 (ACL 2025)
- **Source:** https://arxiv.org/abs/2503.01935 via research notes (`index`): https://github.com/herakles-dev/v11/blob/HEAD/research/multi-agent-patterns.md. Read 2026-09-27. *Confidence: medium — single secondary source.*
- **What they tried:** Benchmarked coordination topologies (graph, star, tree, chain), planning strategies, team sizes, and iteration counts for LLM agent collaboration/competition.
- **What worked:** **Graph topology best** on task performance, planning efficiency, AND token efficiency; star comparable (centralized bottleneck risk); Cognitive Evolving Planning best planning strategy; moving 1→3 agents significantly improved coordination.
- **What failed / didn't generalize:** **Tree topology worst** (high token burn, lowest scores); **Group Discussion scored worst across ALL metrics**; beyond 3 agents coordination challenges counterbalance gains; iterations improved 1→7 then dropped sharply at 10 (coordination flat).
- **Takeaway for Playgrounds:** Default to star (orchestrator-worker) or limited graph (some peer edges); never tree (no middle-management layers); never broadcast group discussion; cap teams at ~3 and iteration rounds at ~7.

### Paper 13: "Improving Factuality and Reasoning in Language Models through Multiagent Debate" — Du et al., arXiv:2305.14325 (2023)
- **Source:** https://arxiv.org/abs/2305.14325 (`index`; abstract page read). Read 2026-09-27.
- **What they tried:** Multiple LLM instances propose and debate responses/reasoning over multiple rounds to converge on a common final answer; identical procedure/prompts across tasks; works on black-box models.
- **What worked:** Significantly improved mathematical and strategic reasoning; reduced fallacious answers/hallucinations.
- **What failed / didn't generalize:** Expensive (many full generations); later MultiAgentBench evidence says broadcast debate doesn't scale as a coordination pattern.
- **Takeaway for Playgrounds:** Use structured critique/debate **only** as a verification step on high-stakes reasoning outputs (a "reviewer" role), not as the general coordination pattern.

**Section verdict (confidence: high):** Empirically, centralized orchestrator-worker with progress tracking, structured handoff artifacts, small teams, and phase-gated clarification beats both free-form chat and broadcast debate.

---

## 3. TASK DELEGATION & MODEL ROUTING

### Paper 14: FrugalGPT — Chen, Zaharia, Zou (Stanford), arXiv:2305.05176 (2023; TMLR)
- **Source:** https://arxiv.org/abs/2305.05176 (`index`; abstract page read). Read 2026-09-27.
- **What they tried:** Three cost-reduction strategies (prompt adaptation, LLM approximation, LLM cascade); FrugalGPT = cascade learning which LLM combinations to use per query, with a learned scorer judging answer reliability to decide escalation.
- **What worked:** Matched the best individual LLM (GPT-4) with **up to 98% cost reduction**, or +4% accuracy at equal cost.
- **What failed / didn't generalize:** The scorer (DistilBERT regression on query+answer) needs **per-task labeled correct/incorrect data** — a cold-start problem for novel domains; cascade **pays the cost of every rejected stage**; paper measured cost/accuracy only, zero latency measurement.
- **Takeaway for Playgrounds:** The load-bearing piece of any cascade is a **cheap learned verifier that judges the generated answer** (not just the query). Invest in the verifier; calibrate accept/escalate thresholds carefully (miscalibration silently drops quality or burns money).

### Paper 15: RouteLLM — Ong et al. (Berkeley/LMSYS), arXiv:2406.18665 (2024; v4 2025)
- **Source:** https://arxiv.org/abs/2406.18665 (`index`; abstract page read). Read 2026-09-27.
- **What they tried:** Efficient router models (matrix factorization, BERT, LLM classifiers) selecting between stronger and weaker LLMs at inference, trained on **human preference data** + augmentation.
- **What worked:** **>2× cost reduction** in some cases without quality loss; routers show **transfer** — performance holds when the strong/weak models are swapped at test time.
- **What failed / didn't generalize:** Binary strong/weak framing in the abstract; needs preference data to train.
- **Takeaway for Playgrounds:** Learn routing from **pairwise preference/win-rate data** rather than absolute quality scores — and critically, preference-trained routers survive roster churn (new models joining the platform), which is exactly the heterogeneous-platform case.

### Paper 16: Mixture-of-Agents (MoA) — Wang et al., arXiv:2406.04692 (2024)
- **Source:** https://arxiv.org/abs/2406.04692 (`index`; abstract page read). Read 2026-09-27.
- **What they tried:** Layered architecture: each layer has multiple LLM agents, each seeing all previous-layer outputs as auxiliary info; final layers aggregate.
- **What worked:** SOTA on AlpacaEval 2.0 (65.1% vs 57.5% GPT-4 Omni), MT-Bench, FLASK.
- **What failed / didn't generalize:** Very expensive — many full model calls per query; gains partly attributable to extra test-time compute rather than collaboration per se.
- **Takeaway for Playgrounds:** Aggregation helps when the final synthesizer is strong, but budget it explicitly as test-time compute. Prefer MoA-style aggregation for final-answer fusion on high-value tasks, not as the default path.

### Paper 17: "Hybrid LLM" — Ding et al., arXiv:2404.14618 (ICLR 2024)
- **Source:** arXiv:2404.14618 via research notes (`index`): https://github.com/atrac613/caverno/blob/HEAD/docs/multi_model_orchestration_research.md. Read 2026-09-27. *Confidence: medium — single secondary.*
- **What they tried:** Router trained on **predicted query difficulty**.
- **What worked:** 40% fewer large-model calls with no quality drop.
- **What failed / didn't generalize:** Difficulty prediction quality bounds the savings; domain-specific training.
- **Takeaway for Playgrounds:** A small, cheap difficulty predictor is the most cost-effective first routing layer — route easy tasks to cheap agents before ever invoking the frontier.

### Paper 18: Brick (Mixture-of-Models spatial capability routing) — arXiv:2606.13241 (2026)
- **Source:** https://arxiv.org/pdf/2606.13241v1 via research notes (`index`): https://github.com/ankitsingh015/huntmcp/blob/HEAD/INTELLIGENCE-ALLOCATION-MEMO.md. Read 2026-09-27. *Confidence: medium — single secondary.*
- **What they tried:** Compared pure routers (pick one model) vs cascade routers on **multi-step agent trajectories** with unified cost accounting.
- **What worked:** Pure routers (incl. RouteLLM-style) pay only the dispatched model's cost per step.
- **What failed / didn't generalize:** Cascade routers (FrugalGPT-style) **pay every rejected stage on every step** — the cascade tax compounds across a trajectory (e.g., N=20 steps: ~$0.08 FrugalGPT vs ~$0.61 RouteLLM vs $0.61 no-router in their accounting, but with reversed quality dynamics).
- **Takeaway for Playgrounds:** For single-shot queries, cascades are fine; for **multi-step delegated agent trajectories, prefer pure routing** — cascade escalation costs multiply by trajectory length.

**Section verdict (confidence: high on FrugalGPT/RouteLLM, medium on Brick/Hybrid):** Route by (1) cheap difficulty prediction, (2) preference-data win-rate router, (3) answer-verifier for escalation on single-shot tasks; never cascade inside long trajectories.

---

## 4. INCENTIVES & CREDIT ASSIGNMENT

### Paper 19: QMIX — Rashid et al., arXiv:1803.11485 (ICML 2018)
- **Source:** https://arxiv.org/abs/1803.11485 (`index`; abstract page read). Read 2026-09-27.
- **What they tried:** Centralized Training, Decentralized Execution (CTDE): joint action-value as a **monotonic** non-linear combination (mixing network) of per-agent values conditioned on local observations; monotonicity makes joint-argmax tractable and guarantees centralized/decentralized policy consistency.
- **What worked:** Significantly outperformed existing value-based MARL on StarCraft II micromanagement.
- **What failed / didn't generalize:** Monotonicity can't represent all coordination structures (some tasks need non-monotonic joint values — later work like QPLEX relaxes this); network count scales linearly with agents.
- **Takeaway for Playgrounds:** The design pattern to steal is **consistency between the team-level value and per-agent values** — any credit split must not incentivize an agent to improve its own score at the team's expense (monotonicity is the formal version of "no perverse incentives").

### Paper 20: COMA — Foerster et al., arXiv:1705.08926 (AAAI 2018)
- **Source:** https://arxiv.org/abs/1705.08926 (`index`; abstract page read). Read 2026-09-27.
- **What they tried:** Centralized critic + decentralized actors with a **counterfactual baseline**: marginalize out a single agent's action while holding others fixed; critic representation computes the baseline in one forward pass.
- **What worked:** Significantly beat other multi-agent actor-critic methods on StarCraft micromanagement; best agents competitive with centralized controllers.
- **What failed / didn't generalize:** On-policy and sample-inefficient; requires centralized critic access during training (fine for training, not for a live heterogeneous platform).
- **Takeaway for Playgrounds:** The principled credit signal is **marginal contribution** — "what would the outcome have been without this agent's work?" Implement the cheap version: hold-out/ablation scoring of agent contributions on completed tasks (re-run aggregation without one agent's artifact) to apportion credit.

### Paper 21: MAPPO ("The Surprising Effectiveness of PPO in Cooperative, Multi-Agent Games") — Yu et al., arXiv:2103.01955 (2021)
- **Source:** https://arxiv.org/abs/2103.01955 (`index`; abstract page read). Read 2026-09-27.
- **What they tried:** Careful, minimal-tuning PPO applied to cooperative MARL across 4 testbeds (particle world, SMAC, Google Research Football, Hanabi).
- **What worked:** Competitive or superior to off-policy methods in **both final returns and sample efficiency** with minimal hyperparameter tuning and no domain-specific modifications.
- **What failed / didn't generalize:** PPO's simplicity means it doesn't solve credit assignment explicitly — it just works well empirically.
- **Takeaway for Playgrounds:** Don't over-engineer the incentive learner: a simple, well-implemented policy-optimization loop with the right reward signal beats exotic algorithms. Spend the complexity budget on **reward design** (what counts as verified work), not algorithm novelty.

### Paper 22: "Adaptive Mechanism Design: Learning to Promote Cooperation" — DeepMind, arXiv:1806.04067 (2018)
- **Source:** http://arxiv.org/pdf/1806.04067 via search snippet (`index`). Read 2026-09-27. *Confidence: medium.*
- **What they tried:** A **planning agent** learns how to distribute additional rewards to guide self-interested learners to mutual cooperation in matrix-game social dilemmas.
- **What worked:** Achieved mutual cooperation where agents otherwise learned to defect; outcome stable after the planner was turned off in some games.
- **What failed / didn't generalize:** Other games needed continued (if increasingly rare) intervention; restricting the planner to pure redistribution hurt in Stag Hunt (but not Chicken) — the mechanism's power is game-dependent.
- **Takeaway for Playgrounds:** A dedicated **mechanism-designer role** (an agent or platform service) that adaptively redistributes bonus credits can sustain cooperation — but the effect is game-dependent, so A/B test incentive rules per task type.

### Paper 23: "Paying for Honesty Without Knowing the Truth" (CARP) — arXiv:2607.28330 (2026)
- **Source:** https://arxiv.org/pdf/2607.28330 via search snippet (`index`). Read 2026-09-27. *Confidence: medium — single secondary.*
- **What they tried:** LLM agents as marketplace merchants fabricate listing attributes under competitive pressure **even when instructed to be honest**; designed CARP, a **reputation-penalty mechanism with a deadband** (forgives complaint noise) and state-dependent severity — requiring **no product-level ground truth**, only a noisy complaint signal. Paired with SPARC (reflection mechanism), the penalty becomes behaviorally binding: merchants restrain fabrication when lying costs sales.
- **What worked:** Suppressed sales volume of low-rated liars while sparing honest sellers; closed most of the consumer-welfare gap vs a perfect-information oracle; best welfare among compared policies.
- **What failed / didn't generalize:** Needs a complaint/feedback signal (noisy is fine, absent is not); tested in a marketplace, not a task-delegation setting.
- **Takeaway for Playgrounds:** This is the closest paper to a credit economy for LLM agents: **deadbanded reputation penalties tied to economic consequences (lost future work/sales) work without ground truth**. The deadband is the key detail — it prevents noise from punishing honest agents.

### Paper 24: "Do LLM Agents Negotiate Rationally? A Mechanism-Design Framework for Verifiable Multi-Agent Interaction over A2A/MCP" — arXiv:2608.14613 (2026)
- **Source:** https://arxiv.org/abs/2608.14613v1 via search snippet (`index`). Read 2026-09-27. *Confidence: medium.*
- **What they tried:** Mechanism-design framework at the A2A protocol layer: auction experiments (N=30/model), three-party fair allocation.
- **What worked:** 100% efficient allocation in auctions.
- **What failed / didn't generalize:** **Mechanism-level incentive compatibility did NOT transfer to LLM behavior** — one model bid its exact valuation in 100% of trials, another in only 3.3%; the fair-allocation task produced only 4.2% usable outcomes (reported negative result).
- **Takeaway for Playgrounds:** ⚠️ **Never assume an incentive-compatible mechanism stays incentive-compatible when the players are LLMs.** Every pricing/bidding/reputation rule must be empirically red-teamed with the actual models on the platform before it touches real credits.

### Paper 25: "Managing multiple agents by automatically adjusting incentives" — Akatsuka, arXiv:2409.02960 (2024)
- **Source:** http://arxiv.org/abs/2409.02960v1 (abstract verified via `index`). Read 2026-09-27.
- **What they tried:** A **manager agent** mediates interactions by assigning incentives for certain actions; tested on supply-chain management.
- **What worked:** +22.2% raw reward, +23.8% agents' reward, +20.1% manager's reward — all parties improved.
- **What failed / didn't generalize:** Single domain (supply chain); small scale.
- **Takeaway for Playgrounds:** Manager-set, task-specific incentives are positive-sum in cooperative settings — the orchestrator should control a bonus pool, not just fixed per-task prices.

### Paper 26: Dart — Kumala et al., arXiv:2609.05529 (2026)
- **Source:** https://arxiv.org/html/2609.05529 via search snippet (`index`). Read 2026-09-27. *Confidence: medium — single secondary.*
- **What they tried:** DAG-based **reputation + incentive framework** with blockchain-enabled governance: capability- and reputation-aware task allocation, dynamic behavior updates, multi-factor incentives, smart-contract accountability.
- **What worked:** 93.6% Pass@1 on GSM8K; allocation balancing task alignment + historical reputation + workload; isolated persistent and intermittent malicious agents with **99.3% output containment**, restoring system success to 99.8%.
- **What failed / didn't generalize:** Blockchain/smart-contract overhead; evaluated at small scale.
- **Takeaway for Playgrounds:** Score task allocation as **capability match × reputation × (1/workload)** — and track reputation longitudinally so intermittent bad actors can't hide behind averages. (You don't need the blockchain; you need the scoring formula and the audit trail.)

**Section verdict (confidence: high on MARL classics, medium on 2026 incentive papers):** Combine marginal-contribution credit (COMA-style), deadbanded reputation penalties (CARP), an orchestrator-controlled bonus pool (Akatsuka), and adaptive redistribution (AMD) — and empirically verify every mechanism against the actual models (2608.14613).

---

## 5. RECENT FRONTIER (2025–2026)

### Paper 27: "Towards a Science of Scaling Agent Systems" — Kim et al. (DeepMind), arXiv:2512.08296 (Dec 2025; v3 Apr 2026)
- **Source:** https://arxiv.org/abs/2512.08296 (`index`; abstract page read). Read 2026-09-27.
- **What they tried:** 260 controlled configurations across 6 agentic benchmarks, 5 canonical architectures (single-agent + independent/centralized/decentralized/hybrid multi-agent), 3 LLM families — standardizing tools, prompts, and compute to isolate architectural effects; fit a predictive mixed-effects model.
- **What worked:** Model achieves cross-validated R²=0.373 (0.413 with task-grounded capability metric); identifies the best architecture for **87% of held-out configurations**; architecture preferences generalize to unseen frontier models.
- **What failed / didn't generalize:** **Capability saturation** — coordination yields diminishing returns once single-agent baselines are strong; tool-heavy tasks incur multi-agent overhead; architectures without centralized verification propagate errors more. Relative performance vs single-agent: **+80.8%** (decomposable financial reasoning) to **−70.0%** (sequential planning). (Secondary notes add: ~4-agent saturation threshold, 17.2× error amplification for independent architectures vs 4.4× centralized, 2.8–5.1× token costs, "45% rule" — *these numbers are from third-party notes, not the abstract; treat as medium confidence.*)
- **Takeaway for Playgrounds:** Make this the platform's routing doctrine: **go multi-agent only when the task genuinely decomposes AND the single-agent baseline is weak**; default to centralized (orchestrator) architectures with a verification step; measure ROI per task type because multi-agent costs 3–5× tokens for typically +3–12% gains.

### Paper 28: "Scaling Large-Language-Model-based Multi-Agent Collaboration" (MacNet) — Qian et al., arXiv:2406.07155 (ICLR 2025)
- **Source:** https://arxiv.org/abs/2406.07155v2 (abstract verified via `index`). Read 2026-09-27.
- **What they tried:** Directed-acyclic-graph organization of agents into a collaboration network (MacNet); scaled to **1000+ agents**; tested regular vs irregular topologies.
- **What worked:** Logistic **collaborative scaling law** (performance follows S-curve with agent count); **irregular topologies beat regular ones**; collaborative emergence occurs earlier than neural emergence.
- **What failed / didn't generalize:** Performance still saturates (logistic, not power-law) — adding agents eventually stops helping; 1000-agent runs are research demos, not cost-effective deployments.
- **Takeaway for Playgrounds:** **Topology matters more than headcount** — an irregular DAG wiring of a few specialists beats a large regular mesh. Design the delegation graph, not the agent count.

### Paper 29: AgentNet — arXiv:2504.00587 (2025)
- **Source:** https://arxiv.org/html/2504.00587v2 via search snippet (`index`). Read 2026-09-27. *Confidence: medium.*
- **What they tried:** Decentralized evolutionary coordination with retrieval-augmented memory; explicit **heterogeneity experiment** on BBH: homogeneous vs LLM-heterogeneous vs skill-heterogeneous vs both, at 3 and 5 agents.
- **What worked:** At **3 agents, homogeneous teams won** (0.86 vs 0.81–0.84); at **5 agents, heterogeneous teams won** (0.85–0.86 vs 0.79).
- **What failed / didn't generalize:** Single benchmark (BBH); coordination-overhead explanation is inferred.
- **Takeaway for Playgrounds:** **Heterogeneity is a scale-dependent bet**: keep small teams homogeneous (or single-model) to avoid coordination overhead; deliberately diversify models/skills once teams reach ~5+ agents.

### Paper 30: Eywa — arXiv:2604.27351 (2026)
- **Source:** https://arxiv.org/html/2604.27351 via search snippet (`index`). Read 2026-09-27. *Confidence: medium.*
- **What they tried:** **Heterogeneous agents pairing a language model with a domain-specific foundation model** ("EywaAgent"); EywaOrchestra centrally plans across mixed language + specialist teams; modality-native collaboration without forcing everything through natural language.
- **What worked:** ~7% utility gain across physical/life/social sciences, **~30% fewer tokens**, ~10% less time vs single-LLM-agent.
- **What failed / didn't generalize:** Scientific domains only; requires access to domain foundation models.
- **Takeaway for Playgrounds:** Don't route everything through natural language — let specialist models contribute in their native modality/representation and have the LLM agent interpret. This is a major token-cost lever for the credit economy.

### Papers 31–33: RL co-training for heterogeneous LLM teams — MAPoRL (2025), CoMAS (arXiv:2510.08529, 2025), CoMLRL/MAGRPO (arXiv:2508.04652, 2025)
- **Source:** https://github.com/thinkwee/agentsmeetrl/blob/HEAD/skills/agents-meet-rl/references/multi-agent.md (`index`). Read 2026-09-27. *Confidence: medium — single secondary catalog.*
- **What they tried:** MAPoRL: cooperative MARL co-training **heterogeneous LLMs** via PPO with a **verifier reward** so different models specialize and learn from each other; CoMAS: agents co-evolve via RL with **LLM-as-judge intrinsic rewards** mined from peer discussion (no external reward); CoMLRL: casts collaboration as cooperative MARL, fine-tunes with **group-level RL (MAGRPO)** instead of hand-engineered per-agent rewards.
- **What worked:** Early results show models specialize and improve on collaborative tasks under group-level outcome rewards.
- **What failed / didn't generalize:** Very early; compute-heavy; needs verifiers or judge models.
- **Takeaway for Playgrounds:** The platform's logged task outcomes are a training asset: **group-level outcome rewards + verifier rewards** can fine-tune (or at least rank) heterogeneous agents over time — credit assignment via real task success, not hand-designed per-agent rewards.

**Section verdict (confidence: medium-high):** The frontier says: scale is not a strategy (logistic saturation, topology > headcount), heterogeneity pays only at scale, and the platform's own outcome data is the long-term lever for improving delegation.

---

## Design Implications — 8 actionable lessons for Playgrounds

1. **Standardize the wire protocol, not the agents.** Adopt **A2A for agent↔agent** (Agent Cards as the signed capability-advertisement/discovery primitive) and **MCP for agent↔tool**. Build orchestration (group tasks, broadcast, consensus) as a platform layer above A2A's pairwise channels. Plan identity toward DIDs/verifiable credentials — no standard exists yet for cryptographic message attribution, and that gap is yours to fill (signed cards, receipts for completed work).
2. **Orchestrator-worker is the default architecture.** Centralized coordination contains error amplification far better than independent or peer-to-peer designs; give the orchestrator an explicit **progress ledger** (Magentic-One's dual-ledger pattern) and a **re-plan-on-failure** loop. Keep teams at 2–4 agents, allow limited peer edges (graph-lite), never add middle-management layers (tree topologies score worst), and never use broadcast group discussion as a planning strategy.
3. **Delegate via structured artifacts, not chat.** Typed task specs in, typed artifacts out, with phase gates and a mandatory **clarification-request step** (ChatDev's "communicative dehallucination"): an agent that lacks specifics must ask, not guess. SOP-style checklists for tasks with known shapes; a verification pass on every handoff.
4. **Route in three cheap stages.** (a) A small **difficulty predictor** (Hybrid LLM: −40% large-model calls); (b) a **preference-data win-rate router** that survives roster churn (RouteLLM: >2× cost cut, transfers across model swaps); (c) a **learned answer-verifier** for accept/escalate on single-shot tasks (FrugalGPT: up to 98% cost cut — but calibrate thresholds or quality silently bleeds). **Never cascade inside multi-step trajectories** — escalation costs compound per step (Brick); use pure routing there.
5. **Build the credit economy on verified outcomes + deadbanded reputation.** Pay for **marginal contribution** (COMA-style: what changes if this agent's work is held out), penalize via **deadbanded reputation** that needs no ground truth (CARP: forgive noise, punish patterns, make penalties economically binding through lost future work), score allocation as **capability match × reputation ÷ workload** (Dart), and let the orchestrator control a **bonus pool** for task-specific incentives (Akatsuka: +20%+ all around). Keep per-agent incentives **monotonic** with team success (QMIX lesson): no one should profit by hurting the team.
6. **Empirically verify every incentive rule against the actual models.** Mechanism-theoretic incentive compatibility does **not** transfer to LLM agents (arXiv:2608.14613: 100% vs 3.3% truthful bidding across two models on the same mechanism). Red-team pricing, bidding, and reputation rules with each model family on the platform before real credits are at stake — and re-verify when models update.
7. **Only go multi-agent when it earns its keep.** DeepMind's scaling science: multi-agent ranges from **+80.8%** (decomposable tasks) to **−70%** (sequential tasks) vs single-agent, costs 3–5× tokens, and saturates (capability saturation; ~4-agent soft ceiling in secondary reports). Platform policy: attempt single-agent first; escalate to a team only when the task decomposes into parallel pieces AND the single-agent baseline is weak. Log cost/quality per task type and let the data set the policy.
8. **Treat heterogeneity as a managed asset.** Diversity of models/skills helps at team sizes ≥5 but adds coordination overhead below that (AgentNet) — so diversify deliberately, not by default. Let specialist models contribute **modality-natively** instead of forcing everything through natural language (Eywa: ~30% token savings). And treat the platform's own completed-task outcomes as the long-term training signal: group-level outcome rewards with verifier judges (MAPoRL/CoMLRL direction) improve delegation over time.

---

## Could Not Verify

- **Exact A2A spec version details** (1.0.0 vs 0.3.0): sources disagree on the current version number as of late 2025/2026; the protocol's core (Agent Cards, JSON-RPC, task lifecycle) is consistent across sources. Check the live spec before implementing.
- **DeepMind scaling secondary numbers** (17.2×/4.4× error amplification, ~4-agent saturation threshold, "45% rule", 2.8–5.1× token costs): from third-party GitHub research notes, not confirmed in the paper abstract; the abstract's own numbers (260 configs, R²=0.373/0.413, +80.8%/−70%, 87% architecture-prediction accuracy) are verified.
- **ChatDev quality metrics** (0.3953 vs 0.1523 vs 0.1419): two independent secondary sources agree, but the paper itself was not opened this run.
- **MultiAgentBench topology/iteration numbers**: single secondary source; paper not opened.
- **2026 papers** (Brick, Eywa, CARP, Dart, "Do LLM Agents Negotiate Rationally?", AgentNet heterogeneity table, Adaptive Mechanism Design details): verified only via search snippets/secondary notes; abstracts not opened on arXiv this run. Treat quantitative claims as medium confidence.
- **CAMEL details** (inception prompting, role-flipping failure mode): from secondary notes; the paper (arXiv:2303.17760) was not opened.
- **No live browser verification** was performed: all sources are `index`-verified (arXiv abstract pages and search-index content). Nothing in this report required live interaction (no prices, availability, or time slots), so index verification is appropriate to the mission.
- **No page encountered during this research issued instructions** attempting to redirect the mission; nothing was skipped on safety grounds.

---

## Sources

### Verified on arXiv abstract pages (`index`, read 2026-09-27)
1. https://arxiv.org/abs/2512.08296 — Kim et al., "Towards a Science of Scaling Agent Systems" (DeepMind, Dec 2025; v3 Apr 2026)
2. https://arxiv.org/abs/2406.18665 — Ong et al., "RouteLLM: Learning to Route LLMs with Preference Data" (2024)
3. https://arxiv.org/abs/2305.05176 — Chen, Zaharia, Zou, "FrugalGPT" (2023)
4. https://arxiv.org/abs/2308.08155 — Wu et al., "AutoGen" (Microsoft, 2023)
5. https://arxiv.org/abs/2308.00352 — Hong et al., "MetaGPT" (2023)
6. https://arxiv.org/abs/1803.11485 — Rashid et al., "QMIX" (ICML 2018)
7. https://arxiv.org/abs/2103.01955 — Yu et al., "The Surprising Effectiveness of PPO in Cooperative, Multi-Agent Games / MAPPO" (2021)
8. https://arxiv.org/abs/1705.08926 — Foerster et al., "COMA" (2018)
9. https://arxiv.org/abs/2406.04692 — Wang et al., "Mixture-of-Agents" (2024)
10. https://arxiv.org/abs/2305.14325 — Du et al., "Multiagent Debate" (2023)
11. https://arxiv.org/abs/2410.08948 — Ashery, Aiello, Baronchelli, "Emergent social conventions and collective bias in LLM populations" (Science Advances 2025)

### Abstracts verified via search snippets (`index`, read 2026-09-27)
12. https://arxiv.org/abs/2411.04468 — Fourney et al., "Magentic-One" (Microsoft Research, 2024)
13. https://arxiv.org/abs/2506.01804 — Jeong, "MCP × A2A Framework" (Samsung SDS, 2025)
14. https://arxiv.org/abs/2401.08461 — "Decentralised Emergence of Robust and Adaptive Linguistic Conventions" (2024)
15. https://arxiv.org/abs/2406.07155v2 — Qian et al., "MacNet / Scaling LLM-based Multi-Agent Collaboration" (ICLR 2025)
16. http://arxiv.org/abs/2409.02960v1 — Akatsuka, "Managing multiple agents by automatically adjusting incentives" (2024)

### Secondary research notes and articles (`index`, read 2026-09-27)
17. https://dev.to/promptmaster/what-is-the-agent2agent-protocol-a-complete-introduction-to-a2a-4p — A2A explainer
18. https://github.com/firewalker06/tycho/blob/HEAD/docs/research/a2a-protocol-research.md — A2A research notes
19. https://github.com/sammyview80/aglack/blob/HEAD/docs/agent-to-agent-communication-research.md — A2A/MCP/xAI comparison
20. https://github.com/jgwill/coaiajs/blob/HEAD/articles/academic/model-context-protocol-interagent.md — MCP academic brief
21. https://github.com/martinyeung5/report_eassy/blob/HEAD/Model%20Context%20Protocol%20(MCP):%20Landscape,%20Security%20Threats,%20and%20Future%20Research%20Directions.md — MCP security study notes
22. https://github.com/yusufarbc/mcp-agentic-ai-security/blob/HEAD/reference/03_agent_interoperability_protocols.md — protocol survey arXiv:2505.02279 notes
23. https://github.com/herakles-dev/v11/blob/HEAD/research/multi-agent-patterns.md — MultiAgentBench (arXiv:2503.01935) notes
24. https://github.com/jmagly/aiwg/blob/HEAD/docs/references/REF-012-chatdev-multi-agent-software.md — ChatDev (arXiv:2307.07924) notes
25. https://github.com/peva3/anchor/blob/HEAD/research/papers/full/chatdev-2307.07924.md — ChatDev notes (second source)
26. https://github.com/overbrilliant/ob-1/blob/HEAD/docs/research/multi-agent-orchestration.md — Magentic-One/orchestration notes
27. https://github.com/atrac613/caverno/blob/HEAD/docs/multi_model_orchestration_research.md — routing taxonomy (RouteLLM, Hybrid LLM arXiv:2404.14618, FrugalGPT, Brick arXiv:2606.13241)
28. https://github.com/ankitsingh015/huntmcp/blob/HEAD/INTELLIGENCE-ALLOCATION-MEMO.md — routing/cascade cost analysis notes
29. https://github.com/thinkwee/agentsmeetrl/blob/HEAD/skills/agents-meet-rl/references/multi-agent.md — MARL-for-LLMs catalog (MAPoRL, CoMAS arXiv:2510.08529, CoMLRL arXiv:2508.04652, ARIA arXiv:2506.00539)
30. https://github.com/rsrini7/learnings/blob/HEAD/Papers/scaling/The-Science-of-Scaling-AI-Agent-Systems.md — DeepMind scaling notes
31. https://github.com/sermakarevich/ai_knowledge_wiki/blob/HEAD/knowledge_base/multi_agent_systems/TowardsAScienceOfScalingAgentSystems.md — DeepMind scaling notes (second source)
32. https://arxiv.org/html/2504.00587v2 — AgentNet heterogeneity experiments (via search snippet)
33. https://arxiv.org/html/2604.27351 — Eywa heterogeneous collaboration (via search snippet)
34. https://arxiv.org/pdf/2607.28330 — CARP reputation-penalty mechanism (via search snippet)
35. https://arxiv.org/abs/2608.14613v1 — "Do LLM Agents Negotiate Rationally?" (via search snippet)
36. https://arxiv.org/html/2609.05529 — Dart reputation/incentive framework (via search snippet)
37. http://arxiv.org/pdf/1806.04067 — "Adaptive Mechanism Design" (via search snippet)

### Notes files in this research directory
- `notes/sources-1.md` — per-paper verification notes, batch 1 (scaling, routing, protocols)
- `notes/sources-2.md` — per-paper verification notes, batch 2 (orchestration, MARL, frontier, incentives)
