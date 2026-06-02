# Skill: Soccer Odds Screenshot Parsing and Solver execution

This file is an AI Agent "Skill" template. When you upload a soccer match betting odds screenshot in Cursor, Codex, Antigravity, or any other AI-enabled IDE chat, you can paste or reference this skill file, and the AI will automatically parse the screenshot, write `odds.json`, and run the betting math solver.

---

## Instructions for AI Assistant

When the user uploads a screenshot of soccer betting odds, please execute the following steps:

### Step 1: Parse the Screenshot
Extract the match details, bookmakers, and odds selections from the screenshot. Pay special attention to:
- **Teams**: Identify which is the Home Team and which is the Away Team.
- **Market Types**:
  - `1X2`: Home win (1), Draw (X), Away win (2).
  - `AH` (Asian Handicap): Identify the line (e.g., `-0.5`, `+0.25`, `0`, `-1.25`) and which team it belongs to.
  - `OU` (Over/Under): Identify the line (e.g., `2.5`, `2.75`, `3.0`) and whether it's Over or Under.
  - `DC` (Double Chance): `1X`, `X2`, `12`.
  - `DNB` (Draw No Bet): Home DNB, Away DNB (equivalent to Asian Handicap 0).
- **Odds**: Ensure the decimal odds are exact (e.g. `2.05`, `1.85`).
- **Bookmaker**: Extract the bookmaker name if visible (e.g. `Bet365`, `Pinnacle`, `188Bet`, `Crown`). If not visible, default to a generic name like `Bookmaker_1`.

### Step 2: Generate `odds.json`
Write the parsed data into a file named `odds.json` in the root directory of the workspace. Use the exact JSON schema defined below:

```json
{
  "match_info": {
    "home_team": "Home Team Name",
    "away_team": "Away Team Name",
    "league": "League/Tournament (Optional or null)"
  },
  "selections": [
    {
      "id": "unique_string_id_1",
      "bookmaker": "Bookmaker Name",
      "market_type": "1X2",
      "name": "Home",
      "odds": 2.10
    },
    {
      "id": "unique_string_id_2",
      "bookmaker": "Bookmaker Name",
      "market_type": "AH",
      "name": "Home",
      "team": "home",
      "line": -0.25,
      "odds": 1.95
    },
    {
      "id": "unique_string_id_3",
      "bookmaker": "Bookmaker Name",
      "market_type": "OU",
      "name": "Over",
      "line": 2.5,
      "odds": 1.88
    }
  ]
}
```

#### JSON Field Schema Rules:
- `id`: A unique string for each selection (e.g., `[bookmaker]_[market]_[name]_[line]`).
- `market_type`: Must be one of `["1X2", "AH", "OU", "DC", "DNB"]`.
- `name`:
  - For `1X2`: Must be one of `["Home", "Draw", "Away"]`.
  - For `AH`: Must be one of `["Home", "Away"]`.
  - For `OU`: Must be one of `["Over", "Under"]`.
  - For `DC`: Must be one of `["1X", "X2", "12"]`.
  - For `DNB`: Must be one of `["Home", "Away"]`.
- `team`: Specify `"home"` or `"away"` for `AH`, `DNB`, and `DC` selections.
- `line`: Specify the numeric line value for `AH` and `OU` (e.g. `-0.5`, `+0.75`, `2.25`). Leave null for `1X2`, `DC`, and `DNB` (except AH 0 which has `line: 0.0`).
- `odds`: The decimal odds float.

### Step 3: Run the Solver
Propose and run the local solver command to calculate optimal stakes and expected value:

```bash
./.venv/bin/python solver.py odds.json
```

### Step 4: Display the Results
Present the output of the solver script in your response, highlighting any arbitrage surebets or positive EV opportunities.

---

## Guide for the User

To use this skill:
1. Simply drag and drop your football odds screenshot into your AI assistant chat window.
2. Type a message like:
   > "Please analyze this screenshot using the skill in `soccer_betting_skill.md`."
3. The AI assistant will write the parsed data to `odds.json`, execute the local calculation engine, and give you the exact stakes to bet for a guaranteed profit or positive expected value.
