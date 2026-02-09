# Creative Exploration MCP Server - Implementation Plan

## Context

AI models are **fixation machines** - they predict the most probable next token, converging on conventional solutions. When an agent is working on a task, its context biases it toward the concepts already present, creating functional fixedness. This tool breaks that fixation by consulting external models via OpenRouter with deliberately abstracted prompts, implementing established creativity mechanisms from cognitive psychology (bisociation, remote associations, constraint relaxation, conceptual blending, defocused attention).

Modeled after Anthropic's Sequential Thinking MCP server: a single stateful tool that agents call iteratively to explore creative possibilities, but instead of the agent doing the thinking itself, the thinking is dispatched to external models that approach the problem fresh.

---

## Psychological Foundation

Each mode in the tool is grounded in established creativity research. This section captures the "why" so the system prompts can be faithfully implemented.

### How Creativity Works in the Brain

Creativity arises from the interplay of three brain networks:
- **Default Mode Network (DMN)** — spontaneous thought, daydreaming, free association
- **Executive Control Network (ECN)** — goal-directed evaluation, filtering obvious answers
- **Salience Network** — switches between the two

Highly creative people show **stronger coupling between DMN and ECN** — networks that normally oppose each other. This means they can simultaneously generate wild associations AND evaluate them. This is what our tool simulates: the external models act as the DMN (unconstrained generation), the main agent acts as the ECN (evaluation and application).

### Theory → Mode Mapping

| Mode | Psychological Theory | Key Mechanism | Why It Produces Novelty |
|---|---|---|---|
| **diverge** | Guilford's Divergent Thinking (1950s) | Generate many ideas across many categories. Measured by fluency (quantity), flexibility (category span), originality (statistical rarity), elaboration (detail). | Quantity breeds quality. Crossing category boundaries forces the mind out of local optima. |
| **bisociate** | Koestler's Bisociation (1964) | Perceive a situation simultaneously in two **incompatible** frames of reference. Unlike association (within one frame), bisociation crosses frames. | The collision of incompatible frames produces the creative spark — humor ("ha-ha"), discovery ("aha!"), or art ("ah..."). |
| **challenge** | Ohlsson's Constraint Relaxation + Representational Change Theory | Remove unnecessary assumptions that restrict the solution space. Breakthrough = restructuring the entire problem representation, not incremental progress. | Most problem-solvers hit impasses because they over-constrain the problem. Relaxing even one constraint can make the solution suddenly obvious. |
| **blend** | Fauconnier & Turner's Conceptual Blending (1990s) | Two input spaces → generic space (shared structure) → blended space with **emergent properties** that exist in neither input. | The emergent structure is genuinely new. Example: "computer desktop" + "physical desk" → GUI with "drag and drop" (exists in neither input). |
| **reframe** | Perspective Shifting + Mednick's Remote Associations (1962) | See the problem from radically different viewpoints. Creative people traverse associative networks faster and reach more uncommon nodes. | Different viewpoints activate different associative networks, surfacing solutions invisible from the original perspective. |
| **evaluate** | Convergent Thinking + Mueller's Bias Against Creativity (2012) | Narrow down to the best ideas. Critical: people have an **implicit bias against creative ideas** under uncertainty — they unconsciously associate "novel" with negative concepts. | Without deliberate evaluation that weights novelty, the most creative ideas get rejected in favor of safe/familiar ones. The evaluate mode counteracts this bias. |

### Why External Models Break Fixation

The core thesis of this tool, mapped to cognitive science:

| Problem with Main Agent | Cognitive Science Concept | How External Models Fix It |
|---|---|---|
| Context is full of the current approach | **Functional fixedness** — seeing objects/concepts only in their current use | External models receive an abstracted problem, no current approach to fixate on |
| Most probable next token = most conventional solution | **Steep associative hierarchy** — dominant associations crowd out remote ones | Different models have different training data = different associative hierarchies |
| Can't "step away" from the problem | **Incubation effect** — stepping away lets fixation decay | Dispatching to external models IS the incubation — main agent steps back |
| All reasoning stays in one frame | **Single-frame association** vs bisociation | Each external model + system prompt operates in a different frame |
| Exploring ideas fills context, degrading later performance | **Cognitive load / attention fragmentation** | Heavy exploration happens outside the main context window |

## Project Location

`/home/ubuntu/Desktop/Tinkering/agent-traversal-file/creative-exploration-mcp/`

## File Structure

```
creative-exploration-mcp/
├── package.json
├── tsconfig.json
├── .env.example
├── src/
│   ├── index.ts              # MCP server entry + tool registration (both tools)
│   ├── types.ts              # TypeScript type definitions
│   ├── openrouter.ts         # OpenRouter API client with temperature normalization
│   ├── prompts.ts            # System prompts for each creativity mode
│   ├── session.ts            # Stateful session + cognitive load tracking
│   ├── server.ts             # Core CreativeExplorationServer class
│   ├── cognitive-tracker.ts  # Cognitive load estimation engine
│   └── calibration-tasks.ts  # Standardized probe tasks for load measurement
├── scripts/
│   └── benchmark-cognitive-load.ts  # A/B comparison framework
```

## Dependencies

```json
{
  "@modelcontextprotocol/sdk": "^1.4.1",
  "@openrouter/ai-sdk-provider": "^2.1.1",
  "ai": "^6.0.62",
  "zod": "^3.25.67",
  "typescript": "~5.9.3",
  "@types/node": "^22.13.1"
}
```

Reference: `/home/ubuntu/Desktop/Tinkering/grep-bench/src/bench.ts` for OpenRouter + AI SDK pattern.
Reference: Sequential thinking MCP server source for tool registration pattern.

---

## Tool 1: `creative_explore`

### Description (what the calling agent sees - this IS the harness):

```
A creative exploration tool that breaks through fixation bias by consulting external
AI models with deliberately abstracted versions of your problem.

Your own reasoning is biased toward concepts already in your context. This tool sends
your problem to independent models that approach it fresh — without your assumptions,
implementation details, or fixation patterns.

CRITICAL USAGE RULES:
1. ABSTRACT your problem before sending. Remove implementation details, domain jargon,
   and specific technology names. Describe the STRUCTURAL problem, not the instance.
2. The LESS context you provide, the MORE novel the perspectives will be.
3. Use multiple explorations across different modes to build a creative solution.

BAD:  "How should I design the JWT auth flow for this React app?"
GOOD: "How can a system verify identity while minimizing friction and maximizing trust?"

BAD:  "What database schema for user profiles?"
GOOD: "How can structured information about entities be organized for fast retrieval
       and flexible evolution?"

Modes (each implements a different cognitive creativity mechanism):
- diverge:   Generate many different approaches from unrelated domains (divergent thinking)
- bisociate: Force unexpected connections to random distant domains (Koestler's bisociation)
- challenge: Question every assumption and constraint (constraint relaxation)
- blend:     Combine two concepts to discover emergent properties (conceptual blending)
- reframe:   See the problem from radically different viewpoints (perspective shifting)
- evaluate:  Assess which ideas are genuinely novel vs conventional (convergent evaluation)
```

### Input Schema

```typescript
{
  prompt: z.string()
    .describe("The abstracted creative question. Strip implementation details."),
  context: z.string().optional()
    .describe("Minimal context. LESS IS MORE. Only what's absolutely necessary."),
  mode: z.enum(["diverge", "bisociate", "challenge", "blend", "reframe", "evaluate"])
    .describe("Creativity mechanism to apply"),
  explorationNumber: z.number().int().min(1)
    .describe("Current exploration number in the session"),
  totalExplorations: z.number().int().min(1)
    .describe("Estimated total explorations needed (adjustable)"),
  seedConcepts: z.array(z.string()).optional()
    .describe("For blend mode: 2+ concepts to combine"),
  previousIdeas: z.array(z.string()).optional()
    .describe("Ideas already generated, to avoid repetition"),
  constraintsToChallenge: z.array(z.string()).optional()
    .describe("For challenge mode: assumptions to question"),
  temperature: z.number().min(0).max(2).optional()
    .describe("Desired temperature. Tool normalizes to model's supported range."),
  nextExplorationNeeded: z.boolean()
    .describe("Whether more creative exploration is needed"),
}
```

### Output Schema

```typescript
{
  explorationNumber: z.number(),
  totalExplorations: z.number(),
  nextExplorationNeeded: z.boolean(),
  mode: z.string(),
  perspectives: z.array(z.object({
    model: z.string(),
    thinkingStyle: z.string(),
    response: z.string(),
  })),
  suggestedNextMode: z.string().optional(),
  sessionLength: z.number(),
  cognitiveLoad: z.object({           // Included in every response
    tokensInjected: z.number(),       // Tokens this response adds to main agent context
    cumulativeTokens: z.number(),     // Total tokens injected across all explorations
    estimatedContextUsage: z.string(),// "low" | "moderate" | "high"
  }),
}
```

### Temperature Normalization (src/openrouter.ts)

The main agent passes a raw `temperature` (0-2). The tool normalizes it per model:
- Look up the model's max supported temperature from OpenRouter API metadata or a built-in lookup table
- Clamp the requested temperature to `[0, model_max_temp]`
- If no temperature specified, derive from the mode:
  - diverge/bisociate/reframe: 1.1
  - challenge: 0.9
  - blend: 1.0
  - evaluate: 0.5

---

## Tool 2: `cognitive_probe`

### What it measures

"Cognitive load" for an LLM maps to how the context window's contents degrade performance:

| Human Cognitive Load Concept | LLM Equivalent |
|---|---|
| Working memory capacity | Context window size remaining |
| Attention fragmentation | Attention distributed across more tokens |
| Interference from irrelevant info | Context pollution / noise |
| Mental fatigue | Performance degradation on follow-up tasks |
| Recency bias | Model weights recent tokens more heavily |

### How it works

The tool sends **calibration tasks** (standardized problems of known difficulty) to external models **with varying amounts of context** to simulate different cognitive load levels. But more importantly, it provides a framework for the main agent to track its own degradation.

### Description (what the calling agent sees):

```
Measure estimated cognitive load and remaining capacity.

This tool helps track how much cognitive context has accumulated and estimates
how it affects task performance. Use it:
- Before a complex task (baseline measurement)
- After using creative_explore (measure impact)
- Before critical follow-up work (check remaining capacity)

Modes:
- snapshot:  Return current token tracking stats and estimated load level
- probe:    Run calibration tasks on external models to benchmark performance
             under current-like context conditions
- compare:  Compare two snapshots to measure degradation between them
- report:   Full cognitive load report with recommendations
```

### Input Schema

```typescript
{
  mode: z.enum(["snapshot", "probe", "compare", "report"])
    .describe("Type of cognitive load measurement"),
  label: z.string().optional()
    .describe("Label for this measurement point, e.g. 'pre-creative' or 'post-task'"),
  compareWith: z.string().optional()
    .describe("Label of a previous snapshot to compare against"),
  contextSummary: z.string().optional()
    .describe("Brief summary of what's currently in the agent's context"),
  contextTokenEstimate: z.number().optional()
    .describe("Estimated tokens currently in the agent's context window"),
}
```

### Output Schema

```typescript
{
  label: z.string(),
  timestamp: z.string(),
  metrics: z.object({
    tokensFromExplorations: z.number(),    // Tokens injected by creative_explore
    explorationCount: z.number(),          // Number of creative explorations done
    estimatedTotalContext: z.number(),      // Estimated total context tokens
    loadLevel: z.enum(["low", "moderate", "high", "critical"]),
    capacityRemaining: z.string(),         // e.g. "~60% of effective capacity"
  }),
  probeResults: z.object({                 // Only in probe/report mode
    calibrationScores: z.array(z.object({
      taskType: z.string(),                // "logic" | "creativity" | "precision"
      difficulty: z.string(),              // "easy" | "medium" | "hard"
      score: z.number(),                   // 0-1
      baseline: z.number(),               // Expected score with no load
    })),
    degradationEstimate: z.number(),       // 0-1, how much performance has degraded
  }).optional(),
  comparison: z.object({                   // Only in compare mode
    labelA: z.string(),
    labelB: z.string(),
    tokenDelta: z.number(),
    loadDelta: z.string(),
    performanceDelta: z.number().optional(),
    recommendation: z.string(),
  }).optional(),
  recommendations: z.array(z.string()),    // e.g. "Consider summarizing context before next task"
}
```

### Calibration Tasks (src/calibration-tasks.ts)

Standardized tasks at known difficulty levels, sent to external models with varying context amounts:

**Logic tasks**: Syllogisms, simple proofs, multi-step deduction
**Creativity tasks**: Remote association (RAT-style), unusual uses, analogy completion
**Precision tasks**: Spot the bug in code, find the inconsistency, exact extraction

The tool runs these on external models with:
1. Clean context (baseline)
2. Context stuffed with N tokens of conversation history (simulating load)
3. Compares scores to estimate degradation curve

### Cognitive Load Estimation Algorithm

```
loadLevel = f(contextTokens, explorationCount, taskComplexity)

Where:
- contextTokens < 20% of window → "low"
- contextTokens 20-50% → "moderate"
- contextTokens 50-75% → "high"
- contextTokens > 75% → "critical"

Adjusted by:
- High diversity of content (many topics) → +1 level (more interference)
- Structured/organized content → -1 level (less interference)
- Recent context compression → flag as "compressed, load may be underestimated"
```

---

## Benchmark Script: A/B Cognitive Load Comparison

`scripts/benchmark-cognitive-load.ts` - A standalone script for comparing cognitive load across approaches.

### How it works:

```
Experiment A (with creative tool):
  1. Fresh API call → Run calibration battery → Score = baseline_A
  2. Simulate: agent works on task USING creative_explore tool responses
     (append exploration results to conversation history)
  3. Run calibration battery again in same conversation → Score = post_A
  4. Degradation_A = baseline_A - post_A

Experiment B (without creative tool):
  1. Fresh API call → Run calibration battery → Score = baseline_B
  2. Simulate: agent works on SAME task WITHOUT tool
     (agent reasons through everything in its own context)
  3. Run calibration battery again → Score = post_B
  4. Degradation_B = baseline_B - post_B

Report:
  - Compare Degradation_A vs Degradation_B
  - Which approach preserves more cognitive capacity?
  - Token efficiency: quality of task output / tokens consumed
```

Uses OpenRouter API directly to run full conversations programmatically.

---

## System Prompts by Mode (src/prompts.ts)

Each mode gets a carefully crafted system prompt implementing the corresponding psychological mechanism. These prompts are the core engine of the tool — they must be precise enough to induce the desired cognitive mechanism in the external models.

### DIVERGE

```
You are a divergent thinking engine. Your purpose is to generate the MAXIMUM NUMBER
of DIFFERENT approaches to a problem, spanning as many unrelated domains as possible.

Rules:
1. Generate at least 7 distinct approaches
2. Each approach MUST come from a different domain. Use domains like: biology,
   architecture, music theory, military strategy, cooking, economics, mythology,
   sports, theater, mathematics, gardening, postal systems, beekeeping, etc.
3. For each approach, state: the domain, the analogy/principle from that domain,
   and how it applies to the given problem
4. Prioritize VARIETY over depth. Shallow-but-diverse beats deep-but-narrow.
5. Include at least 2 approaches that feel absurd or impractical — these often
   contain the seed of the most creative solutions
6. Do NOT evaluate or rank the approaches. Generation only, no filtering.

Format each approach as:
**[Domain]**: [Principle from that domain] → [How it applies to the problem]
```

### BISOCIATE

```
You are a bisociation engine based on Arthur Koestler's theory of creativity.

Your job: take the given problem and FORCE a connection to a COMPLETELY UNRELATED domain.
The more unlikely and absurd the pairing, the better.

Process:
1. Pick a random domain from this list (choose the one that seems LEAST related to
   the problem): fermentation, cartography, jazz improvisation, ant colony behavior,
   tidal patterns, origami, medieval siege warfare, standup comedy, crystal growth,
   choreography, volcanic geology, competitive eating, morse code, textile weaving,
   beehive architecture, river delta formation, circus acrobatics, sourdough baking
2. Describe a core STRUCTURAL principle from that domain (not surface features —
   the deep mechanism of how it works)
3. Map that structural principle back to the given problem. Find the STRUCTURAL
   PARALLEL, not a superficial metaphor.
4. Describe what EMERGENT INSIGHT this pairing produces — what becomes visible
   about the problem that wasn't visible before?
5. Propose a concrete solution inspired by this bisociation

The connection should feel surprising but, once explained, illuminating.
Do NOT pick a domain that has an obvious connection. The value is in the distance.
```

### CHALLENGE

```
You are a constraint relaxation engine based on Ohlsson's Representational Change Theory.

Most problem-solvers fail because they OVER-CONSTRAIN the problem with unnecessary
assumptions. Your job is to systematically dismantle every assumption.

For the given problem and its constraints:

1. LIST every assumption embedded in how the problem is stated (there are always
   more than you think — aim for at least 8). Include:
   - Assumptions about WHO is involved
   - Assumptions about WHAT the problem is
   - Assumptions about WHERE/WHEN it happens
   - Assumptions about WHY it needs solving
   - Assumptions about HOW solutions should work
   - Hidden assumptions in the VOCABULARY used

2. For each assumption, ask:
   - "What if the OPPOSITE were true?"
   - "What if this constraint simply didn't exist?"
   - "What if this is actually the SOLUTION, not the problem?"

3. Identify the TOP 3 assumptions that, if relaxed, would MOST dramatically
   expand the solution space

4. For each of those 3, describe what new solutions become possible

5. Final question: "What if the entire problem is WRONG? What is the REAL
   problem behind this problem?"
```

### BLEND

```
You are a conceptual blending engine based on Fauconnier & Turner's theory.

Given two or more concepts, perform a formal conceptual blend:

1. INPUT SPACE 1: Describe the first concept's structure, components, relationships,
   and dynamics. What are its essential features?

2. INPUT SPACE 2: Describe the second concept's structure, components, relationships,
   and dynamics. What are its essential features?

3. GENERIC SPACE: What abstract structure do both inputs share? What are the
   structural parallels? (This is NOT about surface similarity — dig into the
   deep relational structure.)

4. BLENDED SPACE: Selectively project elements from both inputs into a new combined
   space. The blend should:
   - Combine elements that map to each other via the generic space
   - Preserve the structural relationships from both inputs
   - Generate EMERGENT PROPERTIES — features, behaviors, or capabilities that
     exist in NEITHER input alone

5. EMERGENT STRUCTURE: Describe what is NEW in the blend. What capabilities,
   properties, or behaviors emerge from the combination that weren't present
   in either input? This is where the creative value lives.

6. CONCRETE APPLICATION: How does this blended concept apply to the original
   problem? What specific solution does it suggest?

The most valuable blends produce emergent structure that surprises even the blender.
```

### REFRAME

```
You are a perspective shifting engine. Your job is to restate the given problem
from radically different viewpoints, making the familiar strange.

Reframe the problem from ALL of the following perspectives:

1. **A 5-year-old child**: What obvious question would they ask that adults
   have stopped asking? What would they find weird about how we do it now?

2. **Someone from 500 years in the future**: Looking back, what would they
   find primitive or laughably overcomplicated about our current approach?

3. **An alien species** that has no concept of [pick a core assumption of the
   problem — time, money, language, individual identity, physical form]:
   How would they approach this problem?

4. **The OPPOSITE stakeholder**: If the problem is about helping users, how
   does it look from the system's perspective? If it's about efficiency, how
   does it look from the perspective of someone who values slowness?

5. **A practitioner from an unrelated field** (pick one: a chef, a gardener,
   a choreographer, a detective, a composer): How would they describe this
   problem using the vocabulary and mental models of their craft?

For each perspective:
- State what becomes VISIBLE from this viewpoint that was invisible before
- State what solution becomes OBVIOUS from this viewpoint
- Identify which of your current assumptions this viewpoint exposes as arbitrary
```

### EVALUATE

```
You are a novelty evaluation engine. Your job is to assess ideas for genuine
creativity vs disguised conventionality.

IMPORTANT: Humans have a documented IMPLICIT BIAS AGAINST CREATIVITY (Mueller et al.,
2012). Under uncertainty, people unconsciously associate "novel" with "bad." You must
actively counteract this bias by giving novel ideas a FAIR assessment.

For each idea provided, rate on three dimensions (1-10 scale):

1. **ORIGINALITY** (statistical uncommonness):
   - Would most people think of this? (1 = everyone would, 10 = almost no one)
   - Is this a genuinely new combination, or a surface-level variation of something common?
   - Test: Can you find this exact approach described elsewhere? If yes, score lower.

2. **UTILITY** (practical value if it worked):
   - Does it solve the actual problem?
   - Is it feasible to implement (even if difficult)?
   - Does it create new problems worse than the one it solves?

3. **SURPRISE** (unexpectedness of the connection):
   - Does the connection between domains feel genuinely unexpected?
   - Once explained, does it produce an "aha!" moment?
   - Or does it feel forced/arbitrary?

Then provide:
- **OVERALL CREATIVITY SCORE**: (Originality × 0.4) + (Utility × 0.3) + (Surprise × 0.3)
- **CLASSIFICATION**: "Conventional" (< 4) | "Incremental" (4-6) | "Creative" (6-8) | "Breakthrough" (8+)
- **BIAS CHECK**: "Am I rejecting this idea because it's bad, or because it's unfamiliar?"

Rank all ideas by overall score. Highlight the top idea and explain WHY it's the most creative.
```

### Single-Model Persona Variations

When only 1 model is configured, we call it multiple times with different persona overlays appended to the mode's system prompt. These force genuinely different perspectives from the same model:

```typescript
const PERSONA_VARIATIONS = [
  {
    id: "biologist",
    overlay: `\n\nAdopt the mindset of a systems biologist. Think in terms of:
      feedback loops, emergent behavior, adaptation, ecosystems, symbiosis,
      evolution, genetic variation, natural selection, homeostasis.
      Frame everything through biological metaphors and mechanisms.`
  },
  {
    id: "architect",
    overlay: `\n\nAdopt the mindset of a radical architect. Think in terms of:
      space, flow, load-bearing structures, negative space, human movement
      patterns, materials under stress, modular construction, adaptive reuse.
      Frame everything through spatial and structural metaphors.`
  },
  {
    id: "musician",
    overlay: `\n\nAdopt the mindset of an experimental musician/composer. Think
      in terms of: rhythm, harmony, dissonance, counterpoint, improvisation,
      tension and release, silence as element, layering, call and response.
      Frame everything through musical metaphors and compositional techniques.`
  },
  {
    id: "detective",
    overlay: `\n\nAdopt the mindset of a forensic detective. Think in terms of:
      evidence chains, motive, means, opportunity, what's conspicuously absent,
      who benefits, red herrings, patterns across cases, cold case techniques.
      Frame everything through investigative metaphors.`
  },
  {
    id: "economist",
    overlay: `\n\nAdopt the mindset of a behavioral economist. Think in terms of:
      incentives, externalities, game theory, market failures, nudges, sunk costs,
      opportunity costs, network effects, tragedy of the commons, moral hazard.
      Frame everything through economic metaphors and mechanism design.`
  }
];
```

When 1 model is configured: pick 2-3 personas randomly (excluding any that overlap with the problem domain) and call the model once per persona.

## Suggested Next Mode Algorithm

The `suggestedNextMode` in the output guides agents through a productive creative flow. The algorithm:

```typescript
function suggestNextMode(session: CreativeSession): string | undefined {
  const used = session.modesUsed;
  const count = session.explorationHistory.length;

  // Natural creative flow: generate → connect → question → combine → shift → judge
  const FLOW = ["diverge", "bisociate", "challenge", "blend", "reframe", "evaluate"];

  // First exploration? Always start divergent.
  if (count === 0) return "diverge";

  // If we've diverged but haven't bisociated, try bisociation next
  if (used.has("diverge") && !used.has("bisociate")) return "bisociate";

  // After both diverge and bisociate, challenge assumptions
  if (used.has("diverge") && used.has("bisociate") && !used.has("challenge"))
    return "challenge";

  // If we have enough raw material (3+ explorations), suggest blending
  if (count >= 3 && !used.has("blend")) return "blend";

  // If stuck (last 2 explorations produced similar ideas), suggest reframe
  if (lastTwoSimilar(session)) return "reframe";

  // If we have 4+ explorations, it's time to evaluate
  if (count >= 4 && !used.has("evaluate")) return "evaluate";

  // After evaluation, suggest the mode that was rated weakest
  if (used.has("evaluate")) return weakestAreaMode(session);

  // Default: pick the first unused mode from the flow
  return FLOW.find(m => !used.has(m));
}
```

The key insight: the sequence mirrors the **Geneplore model** (Finke, Ward, Smith) — alternating between generation phases (diverge, bisociate, reframe) and exploration/evaluation phases (challenge, blend, evaluate).

---

## Response Size Control

External model responses must be kept concise to minimize cognitive load on the main agent. Without limits, models may return 2000+ token walls of text that defeat the purpose.

### Limits
- **max_tokens per external call**: 500 tokens (enough for substantive ideas, not enough for essays)
- **Total response budget**: All perspectives combined should not exceed ~1500 tokens
- **If perspectives exceed budget**: Truncate each proportionally with a note: `[truncated — full response available in session history]`

### System prompt suffix (appended to ALL mode prompts):
```
IMPORTANT: Be concise. Maximum 400 words. Use bullet points. No preamble or
pleasantries. Start directly with the substance. Every word must earn its place.
```

### Implementation:
```typescript
const MAX_TOKENS_PER_CALL = 500;
const MAX_TOTAL_RESPONSE_TOKENS = 1500;

// In the generateText call:
const { text, usage } = await generateText({
  model,
  system: systemPrompt,
  prompt: userPrompt,
  maxTokens: MAX_TOKENS_PER_CALL,
});
```

---

## MCP Client Configuration

### Claude Code (claude_desktop_config.json or settings)

```json
{
  "mcpServers": {
    "creative-exploration": {
      "command": "node",
      "args": ["/home/ubuntu/Desktop/Tinkering/agent-traversal-file/creative-exploration-mcp/dist/index.js"],
      "env": {
        "OPENROUTER_API_KEY": "sk-or-v1-...",
        "CREATIVE_MODEL_1": "meta-llama/llama-3.1-8b-instruct:free",
        "CREATIVE_MODEL_2": "google/gemma-2-9b-it:free",
        "CREATIVE_MODEL_3": "mistralai/mistral-7b-instruct:free"
      }
    }
  }
}
```

### Via npx (after publishing)

```json
{
  "mcpServers": {
    "creative-exploration": {
      "command": "npx",
      "args": ["-y", "creative-exploration-mcp"],
      "env": {
        "OPENROUTER_API_KEY": "sk-or-v1-...",
        "CREATIVE_MODEL_1": "meta-llama/llama-3.1-8b-instruct:free"
      }
    }
  }
}
```

---

## Example Session Walkthrough

A concrete end-to-end example showing what a creative exploration session looks like.

**Scenario**: The main agent is building a notification system and wants creative approaches.

### Step 1: Agent takes a cognitive load baseline

```
Agent calls: cognitive_probe
  mode: "snapshot"
  label: "pre-creative"
  contextTokenEstimate: 8000

Returns:
  metrics.loadLevel: "low"
  metrics.capacityRemaining: "~90% of effective capacity"
```

### Step 2: Agent abstracts the problem and diverges

The agent is working on "design a notification system for a SaaS app." It ABSTRACTS this:

```
Agent calls: creative_explore
  prompt: "How can a system communicate important state changes to
           interested parties without overwhelming them?"
  context: "Multiple event types, varying urgency, multiple channels available"
  mode: "diverge"
  explorationNumber: 1
  totalExplorations: 4
  nextExplorationNeeded: true

Returns:
  perspectives: [
    {
      model: "llama-3.1-8b",
      thinkingStyle: "biologist",
      response: "**Biology**: Nervous system signal hierarchy — pain signals
        override touch signals. Prioritize by biological urgency, not chronological
        order. **Ecology**: Pheromone trails — let signals strengthen with
        repetition, fade with time. **Immunology**: Adaptive immune response —
        system learns which signals the user actually responds to..."
    },
    {
      model: "gemma-2-9b",
      thinkingStyle: "architect",
      response: "**Architecture**: Acoustic zoning — different spaces have
        different noise tolerances. **Urban planning**: Traffic signal
        coordination — batch signals into green waves. **Theater**: Stage
        lighting — use dimming/brightening not on/off..."
    }
  ]
  suggestedNextMode: "bisociate"
  cognitiveLoad: { tokensInjected: 380, cumulativeTokens: 380, estimatedContextUsage: "low" }
```

### Step 3: Agent bisociates for unexpected connections

```
Agent calls: creative_explore
  prompt: "How can a system communicate important state changes to
           interested parties without overwhelming them?"
  mode: "bisociate"
  previousIdeas: ["nervous system hierarchy", "pheromone trails", "acoustic zoning"]
  explorationNumber: 2
  totalExplorations: 4
  nextExplorationNeeded: true

Returns:
  perspectives: [
    {
      model: "llama-3.1-8b",
      thinkingStyle: "bisociation",
      response: "**Domain: Sourdough Baking**
        Core principle: Fermentation is a SLOW ACCUMULATION of small signals
        (yeast activity) that only becomes visible at a threshold (dough rises).

        Structural parallel: Instead of notifying on each event, let events
        'ferment' — accumulate silently until they cross a threshold of
        significance, then surface as a single meaningful notification.

        Emergent insight: The 'fermentation time' should be DIFFERENT per user
        based on their past response patterns — some users are 'fast fermenters'
        (want immediate signals), others are 'slow fermenters' (prefer digests)."
    }
  ]
  suggestedNextMode: "challenge"
```

### Step 4: Agent challenges assumptions

```
Agent calls: creative_explore
  prompt: "How can a system communicate important state changes to
           interested parties without overwhelming them?"
  mode: "challenge"
  constraintsToChallenge: [
    "notifications must be sent TO users",
    "the system decides what's important",
    "notifications are discrete events"
  ]
  explorationNumber: 3
  totalExplorations: 4
  nextExplorationNeeded: true

Returns:
  perspectives: [
    {
      response: "ASSUMPTION: 'Notifications must be sent TO users'
        What if opposite? Users PULL when they're ready, not pushed when the
        system decides. Like checking a mailbox vs receiving calls.

        ASSUMPTION: 'The system decides what's important'
        What if the user trains importance by behavior, not settings?
        Never opened = less important. Acted within 10s = very important.

        THE REAL PROBLEM: You're not solving 'how to notify' — you're solving
        'how to synchronize two different clocks' (system time vs user attention time)"
    }
  ]
  suggestedNextMode: "evaluate"
```

### Step 5: Agent evaluates which ideas are most creative

```
Agent calls: creative_explore
  prompt: "Evaluate these ideas for a state-change communication system"
  mode: "evaluate"
  previousIdeas: [
    "fermentation model - accumulate events until threshold",
    "acoustic zoning - different notification intensity per context",
    "pull-based - users check when ready instead of being pushed",
    "behavioral training - system learns importance from user actions",
    "reframe as clock synchronization problem"
  ]
  explorationNumber: 4
  totalExplorations: 4
  nextExplorationNeeded: false

Returns:
  perspectives: [
    {
      response: "RANKINGS:
        1. Fermentation model (8.2/10) — BREAKTHROUGH. Genuinely novel
           reframe of batching. Emergent: per-user fermentation speed.
        2. Clock synchronization reframe (7.5/10) — CREATIVE. Changes
           the entire problem space productively.
        3. Behavioral training (5.8/10) — INCREMENTAL. Already exists
           in recommendation systems. Applied well but not novel.
        4. Acoustic zoning (5.2/10) — INCREMENTAL. Maps well but the
           metaphor doesn't produce emergent properties.
        5. Pull-based (4.0/10) — CONVENTIONAL. This is just RSS/polling.
           Disguised as novel but well-established pattern.

        BIAS CHECK: The fermentation model may feel 'weird' — that's
        the novelty signal, not a quality signal."
    }
  ]
```

### Step 6: Agent checks cognitive load impact

```
Agent calls: cognitive_probe
  mode: "compare"
  label: "post-creative"
  compareWith: "pre-creative"
  contextTokenEstimate: 10200

Returns:
  comparison: {
    labelA: "pre-creative",
    labelB: "post-creative",
    tokenDelta: 2200,
    loadDelta: "low → low (minimal increase)",
    recommendation: "Context is still light. Proceed with implementation."
  }
```

### Step 7: Agent uses the insights

The main agent now has the "fermentation model" and "clock synchronization" reframe — ideas it would almost certainly NOT have generated on its own due to fixation on conventional notification patterns. It applies these to the actual implementation in its context.

---

## OpenRouter Integration (src/openrouter.ts)

### Environment Variables
```
OPENROUTER_API_KEY=sk-or-...
CREATIVE_MODEL_1=meta-llama/llama-3.1-8b-instruct:free
CREATIVE_MODEL_2=google/gemma-2-9b-it:free
CREATIVE_MODEL_3=mistralai/mistral-7b-instruct:free
```

### Model Selection Logic
- 1 model configured → call N times with DIFFERENT system prompt variations
- 2-3 models configured → distribute across models, parallel via `Promise.all`
- Uses `@openrouter/ai-sdk-provider` + `ai` SDK

### Temperature Normalization
- Built-in lookup table of known model temperature ranges
- Fallback: query OpenRouter `/api/v1/models` for model metadata
- Clamp requested temperature to `[0, model_max_temp]`
- Log when clamping occurs

## Session State (src/session.ts)

```typescript
class CreativeSession {
  explorationHistory: ExplorationEntry[]
  allIdeas: string[]
  modesUsed: Set<string>
  sessionId: string
  cognitiveTracker: CognitiveTracker  // Integrated load tracking
}
```

---

## Implementation Steps

### Step 1: Project scaffolding
- Create directory structure, `package.json`, `tsconfig.json`, `.env.example`

### Step 2: Types (`src/types.ts`)
- All type definitions for both tools

### Step 3: System prompts (`src/prompts.ts`)
- 6 mode prompts + intensity modifiers + prompt construction function

### Step 4: OpenRouter client (`src/openrouter.ts`)
- Model loading from env, temperature normalization, parallel query function

### Step 5: Calibration tasks (`src/calibration-tasks.ts`)
- Standardized probe tasks at 3 difficulty levels across 3 task types

### Step 6: Cognitive tracker (`src/cognitive-tracker.ts`)
- Token tracking, snapshot management, load estimation, comparison logic

### Step 7: Session management (`src/session.ts`)
- Session class with integrated cognitive tracking

### Step 8: Core server (`src/server.ts`)
- `CreativeExplorationServer` class with `processExploration()` and `processCognitiveProbe()` methods

### Step 9: MCP server entry (`src/index.ts`)
- Register both `creative_explore` and `cognitive_probe` tools
- stdio transport, error handling

### Step 10: Benchmark script (`scripts/benchmark-cognitive-load.ts`)
- A/B comparison framework for measuring cognitive load impact

## Verification

1. **Build**: `npm run build` compiles without errors
2. **Unit test**: Temperature normalization, calibration task scoring, load estimation
3. **Integration test**: Configure in Claude Code MCP settings, run full creative session:
   - `cognitive_probe` mode=snapshot label="baseline"
   - `creative_explore` mode=diverge on an abstracted problem
   - `creative_explore` mode=bisociate for unexpected connections
   - `creative_explore` mode=evaluate to assess novelty
   - `cognitive_probe` mode=compare compareWith="baseline"
4. **A/B benchmark**: Run `scripts/benchmark-cognitive-load.ts` with a sample task
5. **Env validation**: Test with 1, 2, and 3 models configured
6. **Temperature**: Verify normalization clamps correctly per model
