# Project Patterns Reference

> Read before planning. Each pattern: **Rule** (what to do), **Use** (what to import), **Reference** (working example to copy from).

**Global reference module:** `src/sections/banner-management/` + `src/api/banner-management/` — demonstrates all patterns below.

---

## 1. File Uploads

**Rule:** Every URL/image field uses `UploadSingleFile` or `UploadMultiFileWithOrder`. Components handle the `POST /storage/upload` call internally.

**Use:** `@components/extra/upload` — `UploadSingleFile`, `UploadMultiFileWithOrder`

**Reference:** `src/sections/banner-management/banner-edit-form.tsx` — `UploadSingleFile` with `setValue()` callbacks.

---

## 2. API Modules

**Rule:** Each module: `src/api/[module]/` with `api.ts` (functions + hooks), `types.ts` (interfaces), `index.ts` (barrel). Endpoints in `API_ROUTES` from `src/api/routes.ts`.

**Use:**
- `useFetch` from `src/utils/api/query` for queries
- `useMutate` from `src/utils/api/mutation` for mutations (auto-toast, auto-invalidation)
- `AuthClient` from `src/utils/api/http` for all HTTP calls (auto-injects Bearer token, handles 401)

**Query keys:** `["module", "list", JSON.stringify(params)]` / `["module", "detail", id]`. Invalidate with `invalidateKey: ["module"]`.

**Reference:** `src/api/banner-management/api.ts`

---

## 3. Forms

**Rule:** react-hook-form + Yup, wrapped in `FormProvider`. Use `RHF*` components from `@components/extra/hook-form`.

**Use:** Shared validators in `src/utils/validation.ts`.

**Reference:** `src/sections/banner-management/banner-edit-form.tsx`

---

## 4. State Management

**Rule:** TanStack React Query only.

---

## 5. Toasts

**Rule:** Sonner via `showSuccessToast()` / `showErrorToast()` from `src/utils/api/toast`. Mutation hooks toast automatically.

---

## 6. Tables / Lists

**Rule:** `useTable()` for pagination, `useFilterTabs()` for tab filters, `CommonPagination` for pagination UI. One row component per table.

**Use:**
- `useTable` from `src/utils/hooks/use-table-hook`
- `useFilterTabs` from `src/utils/hooks/use-filter-tabs-hook`
- `Pagination` from `@components/common/pagination`
- `FilterTabs` from `@components/common/filters`

**Gotcha:** `useTable` is 0-indexed; API is 1-indexed. Pass `page + 1` to API params.

**Reference:** `src/sections/banner-management/banner-list-view.tsx`, row: `src/sections/banner-management/components/banner-table-row.tsx`

---

## 7. Dialogs

**Rule:** Use `ConfirmDialog`, `DeleteDialog`, `SaveDialog`, `CancelDialog` from `@components/common/dialogs`.

---

## 8. Routing

**Rule:** List = `/module/list`, Create = `/module/edit/new`, Edit = `/module/edit/{id}`. All paths in `src/routes/paths.ts`. Detect create vs edit with `id === 'new'`.

**Structure:** Pages in `src/pages/[module]/` (thin wrappers with PermissionGuard), logic in `src/sections/[module]/`.

---

## 9. Permissions

**Rule:** `hasPermission(user, moduleKey, level)` from `src/utils/auth/permissions`. `useAuth()` provides user. Wrap pages with `PermissionGuard`. SuperAdmin bypasses all checks.

**Levels:** `none (0)` < `view (1)` < `add (2)` < `edit (3)` < `delete (4)`

---

## 10. Error / Loading States

**Rule:** `PageLoadingSkeleton` for form pages, `CommonTableSkeleton` for tables, `ErrorState` with retry for failures.

**Use:** `@components/common/loading`, `@components/common/table`, `@components/common/error`

---

## Also

- **Use Vite aliases** (`@components/`, `@api/`, `@utils/`, `@sections/`, etc. from `vite.config.ts`) — not relative imports.
