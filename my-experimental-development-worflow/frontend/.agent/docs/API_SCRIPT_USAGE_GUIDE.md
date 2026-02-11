# API Usage

```bash
source .agent/scripts/api-env.sh  # Run once: sets API_BASE + locked curl wrapper

# Defaults are read from .agent/scripts/config.toml (project/env + token).
# Per-call overrides are intentionally blocked:
# - You cannot pass API_TOKEN_NAME
# - You cannot pass Authorization header
# - You cannot call a URL outside API_BASE
curl "/bandar-admin/discounts"
curl -H "Content-Type: application/json" -X POST -d '{"code":"X"}' "/bandar-admin/discounts"

# If you need to change environment or token, edit .agent/scripts/config.toml defaults.
```
