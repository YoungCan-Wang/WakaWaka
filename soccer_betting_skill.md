# Soccer Betting Skill Compatibility Entry

The canonical WakaWaka skill now lives at:

```text
skills/soccer-betting/SKILL.md
```

When a user references this legacy file, load and follow the canonical skill instructions there. In short, the workflow is:

1. Parse the soccer odds screenshot or user-supplied odds.
2. Ask for clarification instead of guessing when odds, teams, bookmaker names, market types, lines, or handicap signs are unclear.
3. Write `odds.json` in the repository root using the WakaWaka schema.
4. Run `./.venv/bin/python solver.py odds.json`.
5. Report the solver output, separating arbitrage results from EV/Kelly results that only exist when `probs.json` is present.

This compatibility file is kept so older README snippets and manual AI-chat prompts that mention `soccer_betting_skill.md` still work.
