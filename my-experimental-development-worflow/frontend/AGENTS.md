# Repository Guidelines

## Project Structure & Module Organization

- Source root: `src/`
- Pages: `src/pages/` (route-level screens)
- Components: `src/components/` (shared UI + form components)
- Layouts: `src/layouts/` (shells and navigation)
- Routes: `src/routes/` (route definitions and guards)
- Sections: `src/sections/` (feature sections used by pages)
- Auth: `src/auth/` (auth guards, helpers)
- API clients: `src/api/` (service wrappers)
- Utilities: `src/utils/` (helpers, API setup)
- Contexts: `src/contexts/` (React context providers)
- Theme: `src/theme/` (MUI theme setup)
- Types: `src/types/` (shared TypeScript types)
- Assets: `src/assets/` and `public/` (bundled vs static)

## Build, Test, and Development Commands

- package manager: pnpm

## Coding Style & Naming Conventions

- TypeScript + React 18 with ES modules.
- Prefer project aliases from `vite.config.ts` (e.g., `@components/...`, `@utils/...`, `@assets/...`) instead of deep relative paths.

## AI Assisted Frontend Development Workflow with Human in the Loop (frontend-agent)

- The `.agent/` directory contains local agent tooling, prompts, and scripts used to assist development with human review.
- Key files: `.agent/Agent.md` (agent guidance), `docs/PROJECT_PATTERNS.md` (project patterns — read first), `.agent/PLAN_TEMPLATE.md` (planning template), `.agent/API_SCRIPT_USAGE_GUIDE.md` (script usage),
- Agent scripts live in `.agent/bin/`; reusable skills are in `.agent/skills/`.
