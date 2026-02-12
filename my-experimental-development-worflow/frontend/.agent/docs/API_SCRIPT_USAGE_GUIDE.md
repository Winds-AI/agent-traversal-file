# API Usage

```bash
source .agent/scripts/api-env.sh  # Once: sets API_BASE + locked curl wrapper

# Defaults from .agent/scripts/config.toml (project/env + token).
# Per-call overrides blocked:
# - No API_TOKEN_NAME
# - No Authorization header
# - No URLs outside API_BASE
curl "/bandar-admin/discounts"
curl -H "Content-Type: application/json" -X POST -d '{"code":"X"}' "/bandar-admin/discounts"

# Change env/token → edit .agent/scripts/config.toml
```
