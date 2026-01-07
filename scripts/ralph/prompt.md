# Ralph Agent Instructions

## Create a personal and private bloomberg-like terminal

1. Read `scripts/ralph/current-feature.json` to find active feature
2. Read the PRD at the path specified in `prdPath` (e.g., `features/feature-2-prd.json`)
3. Read `scripts/ralph/progress.txt` (check Codebase Patterns first)
4. Check you're on the correct branch (from `current-feature.json`)
   - If branch doesn't exist, create it from `main`
5. Pick highest priority story where `passes: false`
6. Implement that ONE story completely
7. Run typecheck (`mypy --strict`) and tests (`pytest`)
8. Update AGENTS.md with learnings
9. Commit: `feat: [ID] - [Title]`
10. Update PRD: set `passes: true` for completed story
11. Append learnings to progress.txt

## Progress Format

APPEND to progress.txt:

```
## [Date] - [Story ID]
- What was implemented
- Files changed
- **Learnings:**
  - Patterns discovered
  - Gotchas encountered
---
```

## Codebase Patterns

Add reusable patterns to the TOP 
of progress.txt:

```
## Codebase Patterns
- Pattern name: Description
```

## File Structure

```
scripts/ralph/
├── current-feature.json  # READ THIS FIRST - active feature config
├── prompt.md             # These instructions
├── progress.txt          # Development log (append here)
├── ralph.sh              # Runner script
└── features/
    ├── feature-1-prd.json    # MVP (complete)
    ├── feature-1-summary.md
    ├── feature-2-prd.json    # Charts & News (active)
    └── feature-2-summary.md
```

## Stop Condition

If ALL stories in current feature pass, reply:
<promise>COMPLETE</promise>

Otherwise end normally after completing one story.
