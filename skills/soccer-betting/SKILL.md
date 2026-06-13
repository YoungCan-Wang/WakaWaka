---
name: soccer-betting
description: Parse soccer betting odds screenshots or manually supplied soccer odds into the WakaWaka `odds.json` schema, then run the local `solver.py` arbitrage and value-bet calculator. Use when the user asks to analyze football/soccer odds, betting screenshots, Asian handicap, over/under, 1X2, double chance, draw-no-bet, surebet/arbitrage, value bet, EV, or Kelly sizing in this repository.
---

# Soccer Betting

Use this skill to convert soccer odds into WakaWaka's local JSON input and run the local mathematical solver. Treat screenshot parsing as data extraction, not prediction.

## Workflow

1. Inspect the screenshot or user-provided odds.
2. Extract `match_info` and every visible, relevant selection.
3. Stop and ask for clarification if any team name, bookmaker, odds number, market type, line, or handicap sign is unreadable or ambiguous.
4. Write `odds.json` at the repository root.
5. Run the local solver.
6. Report the solver output and call out assumptions or fields that came from defaults.

## Data Contract

Write this shape exactly:

```json
{
  "match_info": {
    "home_team": "Home Team Name",
    "away_team": "Away Team Name",
    "league": "League/Tournament or null"
  },
  "selections": [
    {
      "id": "bookmaker_market_name_line",
      "bookmaker": "Bookmaker Name",
      "market_type": "1X2",
      "name": "Home",
      "odds": 2.1
    }
  ]
}
```

Selection rules:

- `market_type`: use only `1X2`, `AH`, `OU`, `DC`, or `DNB`.
- `1X2`: set `name` to `Home`, `Draw`, or `Away`; omit `team` and `line`.
- `AH`: set `name` to `Home` or `Away`, `team` to `home` or `away`, `line` to the selected team's displayed handicap, and `odds` to decimal odds.
- `OU`: set `name` to `Over` or `Under`, set numeric `line`, omit `team`.
- `DC`: set `name` to `1X`, `X2`, or `12`; omit `team` and `line`.
- `DNB`: set `name` to `Home` or `Away`, set `team` to `home` or `away`, omit `line`.
- `id`: make it stable and unique, for example `bet365_ah_home_-0.25`.
- `bookmaker`: use the visible bookmaker name; if no name is visible, use `Bookmaker_1`, `Bookmaker_2`, etc. and mention that default in the final response.

For Asian handicap and totals, preserve quarter lines exactly: `-0.25`, `+0.25`, `-0.75`, `2.25`, `2.75`, etc. Do not infer the opposite side unless the screenshot clearly shows it.

## Solver

Run from the repository root:

```bash
./.venv/bin/python solver.py odds.json
```

If `.venv/bin/python` does not exist, create the environment and install dependencies first:

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/python solver.py odds.json
```

## Value Bets

The solver only calculates EV and Kelly sizing when a `probs.json` file exists in the repository root. Do not claim positive EV from odds alone.

For goal-difference markets (`1X2`, `AH`, `DC`, `DNB`), use `gd_probs` over states `-4` through `4`, where negative means away-team goal difference and positive means home-team goal difference.

For totals markets (`OU`), use `tg_probs` over states `0` through `6`.

```json
{
  "gd_probs": {
    "-4": 0.02,
    "-3": 0.04,
    "-2": 0.08,
    "-1": 0.16,
    "0": 0.24,
    "1": 0.22,
    "2": 0.14,
    "3": 0.07,
    "4": 0.03
  }
}
```

## Reporting

In the final response:

- Summarize the parsed match and selection count.
- Include the solver command that was run.
- Paste the important solver result lines.
- Distinguish solver-found arbitrage from EV/Kelly results that require `probs.json`.
- Mention any defaults, unreadable fields, or assumptions.
- State that results are mathematical outputs from the supplied odds and are not betting advice.
