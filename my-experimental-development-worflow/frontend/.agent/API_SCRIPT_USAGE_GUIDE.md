# API Usage

```bash
source .agent/api-env.sh  # Run once: sets API_BASE + curl wrapper

# Per-call token selection (required unless you pass Authorization header)
# Token names live in .agent/tokens.toml (repo-local)
# Available in repo: bandar-dev-superuser
API_TOKEN_NAME=bandar-dev-superuser curl "$API_BASE/bandar-admin/discounts"
API_TOKEN_NAME=bandar-dev-superuser curl -H "Content-Type: application/json" -X POST -d '{"code":"X"}' "$API_BASE/path"

# Optional: explicit Authorization header
curl -H "Authorization: Bearer <token>" "$API_BASE/path"
```
