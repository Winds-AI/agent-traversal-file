# API Validation Guide

How to actually validate APIs before planning integration.

---

## Overview

1. **Discover** endpoint in OpenAPI spec (MCP: `openapi_searchEndpoints`)
2. **Test** endpoint with live calls (`.agent/api.sh`)
3. **Document** findings (response schema, latency, errors)
4. **Report** status (working, broken, partial, uncertain)

---

## Step 1: Discover the Endpoint

**MCP Tool:** `openapi_searchEndpoints`

```
Input: { "path": "endpoint-name-or-keyword" }

Example: { "path": "user" }
Returns:
  - All endpoints matching "user"
  - GET /users, POST /users, GET /users/:id, PUT /users/:id, etc.
```

**What you get:**
- Endpoint path and HTTP method
- Request parameters (path, query, body)
- Request body schema with field types
- Response schema (success & error responses)
- Integration hints

---

## Step 2: Test the Endpoint

**Script:** `.agent/api.sh` (in project root)

**Basic Syntax:**
```bash
.agent/api.sh [METHOD] [PATH] [OPTIONS]
```

### GET Requests

```bash
# Simple GET
.agent/api.sh GET /users

# GET with query parameters
.agent/api.sh GET /users -q page=1 -q limit=10
.agent/api.sh GET /users/:id -q include=profile

# GET a specific resource
.agent/api.sh GET /users/123
```

### POST Requests (Create)

```bash
# POST with JSON body
.agent/api.sh POST /users -j '{"name": "Test", "email": "test@example.com"}'

# POST from file
.agent/api.sh POST /users -j @payload.json
```

**Always use agent-test markers:** See DATA_SAFETY.md

### PUT Requests (Full Update)

```bash
# PUT to replace entire resource
.agent/api.sh PUT /users/123 -j '{"name": "Updated", "email": "new@example.com"}'
```

**Verify before updating:** See DATA_SAFETY.md

### PATCH Requests (Partial Update)

```bash
# PATCH to update specific fields
.agent/api.sh PATCH /users/123 -j '{"name": "Updated"}'
```

### DELETE Requests

```bash
# DELETE a resource
.agent/api.sh DELETE /users/123
```

**Verify before deleting:** See DATA_SAFETY.md

### Advanced Options

```bash
# Custom header
.agent/api.sh GET /users -H 'X-Custom-Header: value'

# File upload (multipart)
.agent/api.sh POST /upload -F file=@/path/to/file.pdf

# Multipart form field
.agent/api.sh POST /data -F name=value -F field2=value2

# Disable JSON formatting (useful for large responses)
.agent/api.sh GET /users --no-pretty
```

---

## Step 3: Validate Response

For each endpoint tested, check:

### Response Status

```
✓ 2xx (200, 201, 204) = Success
⚠ 3xx (301, 302) = Redirect
✗ 4xx (400, 401, 403, 404) = Client error
✗ 5xx (500, 502, 503) = Server error
```

### Response Schema

Compare actual response against OpenAPI spec:

```
Spec says:
{
  "id": string,
  "name": string,
  "email": string
}

Actual response:
{
  "id": "123",
  "name": "John",
  "email": "john@example.com",
  "avatar": "https://...",  ← Extra field
  "phone": null             ← Nullable field
}

Finding: Has extra fields beyond spec, some fields are nullable
```

### Latency

```
Fast:    <500ms
Acceptable: 500ms - 2s
Slow:    2s - 5s
Very Slow: >5s

Note if slow and consider caching/pagination
```

### Error Responses

Test error scenarios:

```bash
# Test invalid input
.agent/api.sh POST /users -j '{"name": ""}' # Missing required field

# Test missing resource
.agent/api.sh GET /users/nonexistent-id

# Test unauthorized (if applicable)
.agent/api.sh GET /users (without token)
```

Document error response format:
```json
{
  "error": "User not found",
  "status": 404,
  "code": "NOT_FOUND"
}
```

---

## Step 4: Document Findings

Create a validation report like this:

```markdown
## API Validation Report

### GET /users/:id

**Status:** ✓ Working

**Request:**
- Path parameter: id (string, required)
- No query parameters

**Response (2xx):**
```json
{
  "id": "string",
  "name": "string",
  "email": "string",
  "phone": "string|null",
  "avatar": "string|null"
}
```

**Error Responses:**
- 404: User not found (JSON: `{"error": "Not found", "code": "NOT_FOUND"}`)
- 401: Unauthorized (if not authenticated)

**Latency:** ~800ms
**Notes:** Avatar field can be null, phone is optional

---

### POST /users

**Status:** ✓ Working

**Request:**
```json
{
  "name": "string",
  "email": "string",
  "phone": "string|null"
}
```

**Response (2xx - 201 Created):**
```json
{
  "id": "string",
  "name": "string",
  "email": "string",
  "createdAt": "ISO-8601 timestamp"
}
```

**Validation Errors (4xx):**
- 400: Invalid email format
- 400: Email already exists

**Notes:** Response doesn't include phone field, only returns created resource

---

### PUT /users/:id

**Status:** ✓ Working

**Response Time:** ~1.2s

**Notes:** Same response schema as GET

---

## Common Issues to Check

**Issue: API returns extra fields not in spec**
```
Spec: { id, name, email }
Actual: { id, name, email, metadata, internal_id }

Note: "API returns additional fields beyond spec. Safe to ignore in frontend."
```

**Issue: API returns null unexpectedly**
```
Spec: { avatar: string }
Actual: { avatar: null }

Note: "Avatar field is sometimes null even when user should have avatar. Confirm if backend bug or expected behavior."
```

**Issue: Response structure different from spec**
```
Spec: { user: { id, name } }
Actual: { id, name }

Note: "API response is flattened, not nested under 'user' key"
```

**Issue: Pagination missing from spec**
```
Spec says: GET /users returns array
Actual: GET /users returns { data: [], pagination: { page, limit, total } }

Note: "API uses pagination. Spec is incomplete."
```

---

## Validation Checklist

For each endpoint being integrated:

- [ ] Endpoint discovered in OpenAPI spec?
- [ ] Endpoint tested with live call?
- [ ] Response status is 2xx?
- [ ] Response format matches spec?
- [ ] Any discrepancies documented?
- [ ] Latency acceptable? (<5s)
- [ ] Error responses tested?
- [ ] Authentication requirements clear?
- [ ] Any edge cases to handle?
- [ ] Ready to plan integration? (Yes/No)

---

## When to Stop & Ask Developer

**Stop validation and ask developer if:**

- API doesn't work at all (returns error)
- Response format completely different from spec
- API requires undocumented authentication
- Latency is unusually high (>10s)
- Error responses are undocumented
- You can't determine if behavior is expected
- API changed since spec was written

**Ask:** "Does this API behavior match what you expect?"
