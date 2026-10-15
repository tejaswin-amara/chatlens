# Diff & PR Quality Review Command (`/review`)

Perform an exhaustive quality review of current staged or recent changes against Ponytail Ultra criteria:

1. **Understand Flow**: Read the diff and every caller of touched functions.
2. **Review Checklist**:
   - **Correctness**: Logic accuracy, edge cases, timezone handling (`Asia/Kolkata`).
   - **Safety**: Secret scrubbing, input validation, read-only boundaries.
   - **Scale**: Concurrency safety, lock contention, memory footprint.
   - **Missing Tests**: Does every non-trivial branch have a runnable test?
   - **Speed**: Are hot loops optimized? Is async properly awaited?
   - **Lean**: Is every new line strictly necessary?
3. **Output Format**:
   - `What this change does:` Summary in 2-3 sentences.
   - Findings in 3 groups: **Must fix**, **Should fix**, **Nice to have**.
   - Conclude with `Verdict: Ship` or `Verdict: fix X first`, `Lean: -<N> lines possible`, and `Not checked:`.
