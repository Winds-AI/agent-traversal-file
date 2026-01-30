# Testing Guidelines

## No Automated Test Suite (Yet)

Validate changes by manually running all seven commands on files in `examples/`:

1. `rebuild`
2. `rebuild-all`
3. `watch`
4. `unwatch`
5. `validate`
6. `index`
7. `read`

## Testing Approach

Test task requirements by building, running, and validating with the Go CLI.

## Go Tests

Go tests are noted as TODO. If you add tests, ensure `go test` remains clean.
