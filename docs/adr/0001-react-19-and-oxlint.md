# 0001 — React 19 and oxlint for the frontend

- **Status:** accepted
- **Date:** 2026-07-06
- **Context:** `docs/00-PROJECT-BRIEF.md` §6 locked "React 18" when it was the
  current major. Scaffolding in mid-2026, React 19 has been stable since
  December 2024 and is what the Vite template, shadcn/ui, TanStack Query, and
  react-hook-form target. Pinning React 18 would mean holding back library
  versions for the life of the project. Separately, the docs specify
  `npm run lint` without naming a linter; the 2026 Vite template ships oxlint.
- **Decision:** Use React 19 (docs references updated from "React 18" to
  "React 19"). Keep oxlint as the frontend linter.
- **Consequences:** Frontend code may use React 19 APIs (actions, `use`,
  ref-as-prop). Any library added must support React 19. oxlint covers
  correctness rules with zero config and is much faster than ESLint; if a rule
  or plugin gap appears later, ESLint can be layered on in CI without changing
  this decision's surface.
