# Ponytail Ultra Minimalism Rules

## Core Philosophy
- The best code is the code never written. Solve the whole problem with the least new code.
- YAGNI (You Aren't Gonna Need It): Skip features, options, and abstractions nobody asked for.

## Hierarchy of Implementation
1. **Does it need to exist?** Skip speculative options.
2. **Already in codebase?** Reuse existing helpers, models, and patterns.
3. **Standard library or native platform?** Use stdlib before adding new code.
4. **Installed dependency?** Use what is installed. Never add a dependency for a few lines.
5. **One readable line?** Make it one line.
6. **Otherwise:** Minimum working code.

## Rigor & Hygiene
- **Shortest Working Diff**: Surgical edits over rewrites. Touch only what is strictly necessary. Never reformat unrelated lines.
- **Runnable Checks**: Every non-trivial change must leave a runnable check behind (unit test or validation script).
- **Tracked Shortcuts**: If making a deliberate shortcut with a known ceiling, annotate: `# shortcut: <the limit>, <when to upgrade>`.
