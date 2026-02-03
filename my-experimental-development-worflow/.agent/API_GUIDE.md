# API Usage

```bash
source .agent/api-env.sh  # Run once: sets API_BASE + curl wrapper

# Per-call token selection (required unless you pass Authorization header)
API_TOKEN_NAME=teachbetter-dev-admin curl "$API_BASE/bandar-admin/discounts"
API_TOKEN_NAME=teachbetter-dev-user curl -H "Content-Type: application/json" -X POST -d '{"code":"X"}' "$API_BASE/path"

# Optional: explicit Authorization header
curl -H "Authorization: Bearer <token>" "$API_BASE/path"
```
