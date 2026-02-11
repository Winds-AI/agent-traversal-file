# Repository Guidelines

## Project Structure & Module Organization

- Source root: `src/`
- Functions: `src/functions/` (API endpoints organized by module)
  - Admin: `src/functions/admin/` (admin-facing APIs)
  - Vendor: `src/functions/vendor/` (vendor-facing APIs)
  - Customer: `src/functions/customer/` (customer-facing APIs)
  - Common: `src/functions/common/` (shared endpoints)
- Models: `src/models/` (Sequelize model definitions)
- Migrations: `src/migrations/` (database schema changes)
- Seeders: `src/seeders/` (test data)
- Middlewares: `src/middlewares/` (auth, logging, validation)
- Config: `src/config/` (database, services, environment)
- Shared: `src/shared/`
  - Utils: `src/shared/utils/` (helpers, handlers)
  - Constants: `src/shared/constants/` (enums, static values)
  - Templates: `src/shared/templates/` (email, notification templates)
- Swagger: `src/swagger/` (API documentation)

## Build, Test, and Development Commands

- Package manager: npm
- Start server: `npm start` or `func start`
- Run tests: `npm test`
- Run migrations: `npx sequelize-cli db:migrate`
- Rollback migration: `npx sequelize-cli db:migrate:undo`
- Generate migration: `npx sequelize-cli migration:generate --name <name>`

## Coding Style & Naming Conventions

- JavaScript (Node.js) with CommonJS modules
- Sequelize ORM for database operations
- Express-validator patterns for input validation
- Centralized response handlers (`successResponse`, `errorResponse`)

## API Route Prefixes

- Admin: `/bandar-admin/...`
- Vendor: `/bandar-vendor/...`
- Customer: `/bandar-customer/...`

## AI Assisted Backend Development Workflow with Human in the Loop (backend-agent)

- The `.agent/` directory contains local agent tooling, prompts, and scripts used to assist development with human review.
- Key files: `.agent/Agent.md` (agent guidance), `docs/PROJECT_PATTERNS.md` (project patterns — read first), `.agent/PLAN_TEMPLATE.md` (planning template), `.agent/API_SCRIPT_USAGE_GUIDE.md` (script usage)
- Agent scripts live in `.agent/bin/`; MCP tools handle database exploration.
