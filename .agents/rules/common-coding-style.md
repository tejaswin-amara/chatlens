# Ponytail Ultra Coding Standards (Ponytail v5.1 Alignment)

> Standard: Ponytail Ultra Minimalism & Awesome Dev Pipeline Engineering Defaults  
> Scope: Python (`src/`, `scripts/`, `benchmarks/`), TypeScript (`chatlens-v2/frontend/`), SQL, and config.

---

## 1. The Ladder of Abstraction
Before writing any new code, stop at the first rung that holds:
1. **Does it need to exist? (YAGNI)**: Skip features, options, and speculative abstractions nobody asked for.
2. **Already in this codebase?**: Reuse existing helpers, utilities, and components.
3. **Standard library or native platform feature?**: Use it before adding code.
4. **An installed dependency?**: Use it before adding anything new.
5. **Can it be one readable line?**: Make it one line.
6. **Otherwise**: Write the minimum code that works.

## 2. Surgical Modifications & Hygiene
- **Shortest Working Diff**: Surgical modifications over rewrites. Touch only what is strictly necessary. Never reformat unrelated lines.
- **Root-Cause Fixes**: Grep all callers of a touched function and fix the root cause once in shared code.
- **Runnable Checks**: Lazy code without its check is unfinished: new non-trivial logic must leave ONE runnable check behind.
- **Preservation**: Preserve existing comments, docstrings, formatting, and established code conventions.
- **Technical Debt Tracking**: Mark deliberate shortcuts with `shortcut: <known ceiling>, <when to upgrade>`. Zero untracked debt (`no-trigger`).
