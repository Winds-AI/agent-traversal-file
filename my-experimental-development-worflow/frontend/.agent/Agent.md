# Agent Workflow

Run **only** the steps the user lists in their prompt. Nothing more.

## Steps

| # | Keywords | File |
|---|----------|------|
| 1 | `api discovery`, `1` | `steps/1-api-discovery.md` |
| 2 | `api testing`, `2` | `steps/2-api-testing.md` |
| 3 | `context`, `plan`, `3` | `steps/3-context-and-plan.md` |
| 4 | `implementation`, `implement`, `4` | `steps/4-implementation.md` |
| 5 | `testing`, `test`, `5` | `steps/5-testing.md` |
| 6 | `bug`, `issue`, `fix`, `resolve`, `6` | `steps/6-bug-resolution.md` |

## Rules

1. Match keywords/numbers in the prompt → run those steps only.
2. Multiple steps → execute in numerical order.
3. Read the step file before executing it.
4. Respect each step's boundaries — do not bleed into other steps.
5. Feature/module name follows the step references (e.g., `"1","2" - certificate management`).

## Combinations

- **3 + 4**: Skip plan approval. Use default answers to decisions.
- **3 + 5** (or 5 included): Add `## Test Cases` to the plan.
- **4 alone**: Requires existing `.agent/plans/PLAN_<feature>.md`. If missing, ask user.
- **5 alone**: Derive test cases from the feature's user flows.

## Resources

| Resource | Path |
|----------|------|
| API env + curl wrapper | `.agent/scripts/api-env.sh` |
| API token usage | `.agent/docs/API_SCRIPT_USAGE_GUIDE.md` |
| Plan template | `.agent/docs/PLAN_TEMPLATE.md` |
| Browser automation | `.agent/skills/agent-browser/` |
| Project patterns | `docs/PROJECT_PATTERNS.md` |
| Project structure | `AGENTS.md` |
