# Whole-Repo Audit Command (`/audit`)

Execute a whole-repo complexity, dead abstraction, and bloat audit following Ponytail Ultra doctrine:

1. **Map First**: Read README, entry points, configuration, and dependencies.
2. **Scan for Issues**:
   - **Bugs & Edge Cases**: Timezone mismatches, swallowed errors, unhandled boundary conditions.
   - **Security & Data Loss**: Secret leakage, prompt injection vulnerabilities, non-transactional writes.
   - **Scale Risks**: Races, unbounded memory collections, inefficient per-item loops.
   - **Missing Tests**: Risky logic without deterministic assertions.
   - **Lean Cuts**: Dead code, duplicate helpers, speculative abstractions, unused dependencies.
3. **Output Format**:
   - `What this repo does:` 2-3 sentences and assumed load.
   - Findings in 3 groups: **Must fix**, **Should fix**, **Nice to have** (each finding numbered with: What this is, Problem, Fix, If we skip it).
   - End with: `Verdict:`, `Lean: -<N> lines possible`, and `Not checked:`.
