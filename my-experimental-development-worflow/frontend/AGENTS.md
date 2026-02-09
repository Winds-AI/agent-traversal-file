## AI Assisted Frontend Development Workflow with Human in the Loop (frontend-agent)

The `.agent/` directory contains tooling and workflows for agent-assisted development. See `.agent/Agent.md` for workflow guidance, step definitions, and execution rules.

### Directory Layout

```
.agent/
├── Agent.md                 # Workflow guidance and step routing rules
├── docs/                    # Documentation and templates
├── scripts/                 # API scripts (api-env.sh)
├── skills/agent-browser/    # Browser automation for web testing
└── steps/                   # 6-step workflow files (1-api-discovery through 6-bug-resolution)
```

### Project Resources

- `docs/PROJECT_PATTERNS.md` — project conventions and patterns (read first)
- `.agent/Agent.md` — see here for how to invoke agent workflows
