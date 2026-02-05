# AI-Assisted Development Workflows

Human-in-the-loop workflows for frontend and backend development.

## Usage

```bash
# Frontend project
cp -r frontend/.agent /path/to/project/
cp frontend/docs/PROJECT_PATTERNS.md /path/to/project/docs/

# Backend project
cp -r backend/.agent /path/to/project/
cp backend/docs/PROJECT_PATTERNS.md /path/to/project/docs/
```

Then customize:
1. `.agent/api-env.sh` — API base URL
2. `.agent/tokens.toml` — Auth tokens
3. `docs/PROJECT_PATTERNS.md` — Project patterns

## Structure

```
frontend/
├── .agent/
│   ├── Agent.md, PLAN_TEMPLATE.md, API_SCRIPT_USAGE_GUIDE.md
│   ├── api-env.sh, tokens.toml
│   ├── bin/curl
│   └── skills/agent-browser/
└── docs/PROJECT_PATTERNS.md

backend/
├── .agent/
│   ├── Agent.md, PLAN_TEMPLATE.md, API_SCRIPT_USAGE_GUIDE.md
│   ├── api-env.sh, tokens.toml
│   └── bin/curl
└── docs/PROJECT_PATTERNS.md
```

## Key Differences

| | Frontend | Backend |
|-|----------|---------|
| Discovery | `openapi_searchEndpoints` | MCP database tools + models |
| Testing | agent-browser | curl + Jest |
| Plan focus | API integration | Schema + migrations |
