# ADR Scaffolding Command (`/adr`)

Scaffold a new Architectural Decision Record (ADR) in `adr/` adhering to MADR (Markdown Architectural Decision Records).

## Template
Filename pattern: `adr/{NNNN}-{short-kebab-slug}.md`

```markdown
# ADR {NNNN}: {Title}

* Status: [proposed | accepted | rejected | deprecated | superseded by ADR-XXXX]
* Deciders: {Engineering Team / Jules}
* Date: {YYYY-MM-DD}

## Context and Problem Statement
{Describe the context, technical dilemma, requirements, and constraints.}

## Decision Drivers
* {Driver 1}
* {Driver 2}

## Considered Options
* {Option 1}: {Description}
* {Option 2}: {Description}

## Decision Outcome
Chosen option: "{Option 1}", because {rationale}.

### Positive Consequences
* {Benefit 1}
* {Benefit 2}

### Negative Consequences
* {Tradeoff 1}

## Confirmation & Verification
{How the decision is validated via tests, linter rules, or CI checks.}
```
