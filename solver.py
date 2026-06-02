import json
import sys
import os
from typing import List, Optional, Dict, Tuple, Any
from pydantic import BaseModel, Field
import numpy as np
from scipy.optimize import linprog, minimize_scalar

# ==========================================
# 1. Pydantic Models for Input Validation
# ==========================================

class BetSelection(BaseModel):
    id: str = Field(description="Unique identifier for the selection")
    bookmaker: str = Field(description="Name of the bookmaker")
    market_type: str = Field(description="Type of market: '1X2', 'AH' (Asian Handicap), 'OU' (Over/Under), 'DC' (Double Chance), 'DNB' (Draw No Bet)")
    name: str = Field(description="Selection name: e.g., 'Home', 'Draw', 'Away', '1X', 'X2', '12', 'Over', 'Under'")
    team: Optional[str] = Field(None, description="For team-specific bets (AH, DNB, DC), specify 'home' or 'away'")
    line: Optional[float] = Field(None, description="Handicap or Over/Under line, e.g. -0.25, 0.5, 2.5, 2.75")
    odds: float = Field(description="Decimal odds, e.g., 2.05")

class MatchInfo(BaseModel):
    home_team: str = Field(description="Home team name")
    away_team: str = Field(description="Away team name")
    league: Optional[str] = Field(None, description="League or tournament name")

class OddsData(BaseModel):
    match_info: MatchInfo
    selections: List[BetSelection]

# ==========================================
# 2. Payoff Calculations
# ==========================================

# State representations:
# GD_STATES: Goal Difference (Home Goals - Away Goals)
# We support GD from -4 to +4 (with -4 meaning <= -4, and +4 meaning >= 4)
GD_STATES = [-4, -3, -2, -1, 0, 1, 2, 3, 4]

# TG_STATES: Total Goals
# We support TG from 0 to 6 (with 6 meaning >= 6)
TG_STATES = [0, 1, 2, 3, 4, 5, 6]


def get_gd_payoff(sel: BetSelection, gd: int) -> float:
    """Calculates the payoff of a Goal Difference (GD) selection for a unit stake."""
    market = sel.market_type.upper()
    name = sel.name.strip()
    odds = sel.odds

    if market == "1X2":
        if name in ["Home", "1"] and gd >= 1:
            return odds
        elif name in ["Draw", "X"] and gd == 0:
            return odds
        elif name in ["Away", "2"] and gd <= -1:
            return odds
        return 0.0

    elif market == "DC":  # Double Chance
        if name in ["1X", "Home/Draw"] and gd >= 0:
            return odds
        elif name in ["X2", "Draw/Away"] and gd <= 0:
            return odds
        elif name in ["12", "Home/Away"] and gd != 0:
            return odds
        return 0.0

    elif market == "DNB":  # Draw No Bet
        team = (sel.team or "").lower()
        if not team:
            # Try to guess from name
            if "home" in name.lower() or "1" in name:
                team = "home"
            else:
                team = "away"

        if team == "home":
            if gd >= 1:
                return odds
            elif gd == 0:
                return 1.0  # Refund
            return 0.0
        elif team == "away":
            if gd <= -1:
                return odds
            elif gd == 0:
                return 1.0  # Refund
            return 0.0
        return 0.0

    elif market == "AH":  # Asian Handicap
        team = (sel.team or "").lower()
        if not team:
            if "home" in name.lower():
                team = "home"
            else:
                team = "away"

        line = sel.line if sel.line is not None else 0.0

        # Calculate effective goal difference for the selected team
        # If Home: X = GD + line
        # If Away: X = -GD + line
        x = gd + line if team == "home" else -gd + line

        # Asian Handicap payout rules:
        if x >= 0.5:
            return odds
        elif x == 0.25:
            return 0.5 * odds + 0.5  # Half Win, Half Refund
        elif x == 0.0:
            return 1.0  # Refund
        elif x == -0.25:
            return 0.5  # Half Loss, Half Refund (you get half your stake back)
        else:
            return 0.0  # Loss

    return 0.0


def get_tg_payoff(sel: BetSelection, tg: int) -> float:
    """Calculates the payoff of a Total Goals (TG) selection for a unit stake."""
    market = sel.market_type.upper()
    name = sel.name.strip().lower()
    odds = sel.odds
    line = sel.line if sel.line is not None else 0.0

    if market != "OU":
        return 0.0

    # Over/Under payout logic is symmetric
    if "over" in name:
        x = tg - line
    elif "under" in name:
        x = line - tg
    else:
        return 0.0

    if x >= 0.5:
        return odds
    elif x == 0.25:
        return 0.5 * odds + 0.5
    elif x == 0.0:
        return 1.0
    elif x == -0.25:
        return 0.5
    else:
        return 0.0


# ==========================================
# 3. Solver Implementations
# ==========================================

def solve_surebet(selections: List[BetSelection], states: List[int], is_tg: bool = False) -> Tuple[bool, float, List[float], List[float]]:
    """
    Solves the Linear Program to find the optimal surebet weights.
    Returns:
        (is_success, return_multiplier, weights, payouts_per_state)
    """
    K = len(selections)
    M = len(states)
    
    # Construct payoff matrix P of size M x K
    P = np.zeros((M, K))
    for i, sel in enumerate(selections):
        for j, state in enumerate(states):
            P[j, i] = get_tg_payoff(sel, state) if is_tg else get_gd_payoff(sel, state)

    # Variables: v = [w_1, ..., w_K, R]^T
    # Objective: Minimize -R (which maximizes R)
    c = np.zeros(K + 1)
    c[-1] = -1.0

    # Bounds: w_i >= 0, R >= 0
    bounds = [(0.0, 1.0) for _ in range(K)] + [(0.0, None)]

    # Equality Constraint: sum(w_i) = 1.0
    A_eq = np.ones((1, K + 1))
    A_eq[0, -1] = 0.0  # R is not part of sum(w_i)
    b_eq = [1.0]

    # Inequality Constraint: -sum(w_i * P_ji) + R <= 0
    # Equivalent to: sum(w_i * P_ji) >= R for all states j
    A_ub = np.zeros((M, K + 1))
    for j in range(M):
        A_ub[j, :K] = -P[j, :]
        A_ub[j, -1] = 1.0
    b_ub = np.zeros(M)

    # Solve the LP
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs")

    if res.success:
        weights = list(res.x[:K])
        R = res.x[-1]
        
        # Calculate actual payouts for each state under this weight distribution
        payouts = [sum(weights[i] * P[j, i] for i in range(K)) for j in range(M)]
        
        # If the minimum payout is strictly greater than 1, we have a surebet
        # (allowing for float precision, say R > 1.0001)
        if R > 1.0001:
            return True, R, weights, payouts
            
    return False, 0.0, [], []


def search_arbitrage(selections: List[BetSelection]) -> List[Dict[str, Any]]:
    """
    Searches for arbitrage opportunities by checking all combinations of size 2 and 3.
    Splits selections into Goal Difference (GD) and Total Goals (TG) markets.
    """
    gd_selections = [s for s in selections if s.market_type.upper() in ["1X2", "AH", "DNB", "DC"]]
    tg_selections = [s for s in selections if s.market_type.upper() in ["OU"]]

    results = []

    # Helper search function
    def search_in_subset(subset: List[BetSelection], states: List[int], is_tg: bool):
        n = len(subset)
        # Check pairs (size 2)
        for i in range(n):
            for j in range(i + 1, n):
                sel_combo = [subset[i], subset[j]]
                # Don't pair bets from the same bookmaker unless they are different
                # Actually, usually they must be from different bookmakers to have arb
                success, R, weights, payouts = solve_surebet(sel_combo, states, is_tg)
                if success:
                    results.append({
                        "selections": sel_combo,
                        "profit_pct": (R - 1.0) * 100,
                        "return_multiplier": R,
                        "weights": weights,
                        "payouts": payouts,
                        "states": states,
                        "is_tg": is_tg
                    })

        # Check triplets (size 3)
        for i in range(n):
            for j in range(i + 1, n):
                for k in range(j + 1, n):
                    sel_combo = [subset[i], subset[j], subset[k] ]
                    # Filter: check if they have at least 2 different bookmakers
                    bookmakers = {s.bookmaker for s in sel_combo}
                    if len(bookmakers) < 2:
                        continue
                    success, R, weights, payouts = solve_surebet(sel_combo, states, is_tg)
                    if success:
                        results.append({
                            "selections": sel_combo,
                            "profit_pct": (R - 1.0) * 100,
                            "return_multiplier": R,
                            "weights": weights,
                            "payouts": payouts,
                            "states": states,
                            "is_tg": is_tg
                        })

    search_in_subset(gd_selections, GD_STATES, is_tg=False)
    search_in_subset(tg_selections, TG_STATES, is_tg=True)

    # Sort results by profit percentage descending
    results.sort(key=lambda x: x["profit_pct"], reverse=True)

    # Deduplicate results: if a combination has the same selection IDs, remove duplicates
    unique_results = []
    seen_ids = set()
    for r in results:
        ids_tuple = tuple(sorted([s.id for s in r["selections"]]))
        if ids_tuple not in seen_ids:
            seen_ids.add(ids_tuple)
            unique_results.append(r)

    return unique_results


# ==========================================
# 4. Expected Value & Kelly Calculator
# ==========================================

def calculate_expected_values(selections: List[BetSelection], probabilities: Dict[int, float], is_tg: bool = False) -> List[Dict[str, Any]]:
    """
    Calculates the expected value (EV) for each selection given a probability distribution over the states.
    For selections with EV > 1, calculates the optimal Kelly fraction.
    """
    states = TG_STATES if is_tg else GD_STATES
    results = []

    for sel in selections:
        # Calculate expected payoff
        ev = 0.0
        for j, state in enumerate(states):
            prob = probabilities.get(state, 0.0)
            payoff = get_tg_payoff(sel, state) if is_tg else get_gd_payoff(sel, state)
            ev += prob * payoff

        # Calculate Kelly fraction if EV > 1
        # Kelly maximizes: E[ln(1 + f * (Payoff - 1))]
        # We search for f in [0, 1] using minimize_scalar
        kelly_fraction = 0.0
        if ev > 1.0001:
            def neg_expected_log_return(f):
                log_sum = 0.0
                for state in states:
                    prob = probabilities.get(state, 0.0)
                    payoff = get_tg_payoff(sel, state) if is_tg else get_gd_payoff(sel, state)
                    net_return = payoff - 1.0
                    val = 1.0 + f * net_return
                    # Avoid log of zero or negative
                    if val <= 1e-9:
                        return 1e9
                    log_sum += prob * np.log(val)
                return -log_sum

            res = minimize_scalar(neg_expected_log_return, bounds=(0, 1), method='bounded')
            if res.success:
                kelly_fraction = res.x
                # If Kelly fraction is tiny, set to 0
                if kelly_fraction < 1e-4:
                    kelly_fraction = 0.0

        results.append({
            "selection": sel,
            "expected_value": ev,
            "kelly_fraction": kelly_fraction
        })

    # Sort by EV descending
    results.sort(key=lambda x: x["expected_value"], reverse=True)
    return results


# ==========================================
# 5. CLI & Presentation
# ==========================================

def print_arbitrage_report(opportunities: List[Dict[str, Any]], match_info: MatchInfo):
    print(f"\n==================================================================")
    print(f"⚽ BETTING ANALYSIS REPORT: {match_info.home_team} vs {match_info.away_team}")
    if match_info.league:
        print(f"🏆 League: {match_info.league}")
    print(f"==================================================================")

    if not opportunities:
        print("\n❌ No arbitrage (Surebet) opportunities found.")
        print("Tip: Arbitrage requires different bookmakers having contrasting odds.")
        return

    print(f"\n✨ Found {len(opportunities)} Arbitrage (Surebet) opportunities!")
    for idx, opt in enumerate(opportunities[:5]):  # Show top 5
        print(f"\n📌 Opportunity #{idx + 1}: Profit +{opt['profit_pct']:.2f}% (Guaranteed)")
        print(f"   Category: {'Total Goals (Over/Under)' if opt['is_tg'] else 'Goal Difference (Handicap/1X2)'}")
        print(f"   --------------------------------------------------------------")
        print(f"   {'Bookmaker':<15} | {'Selection':<25} | {'Odds':<6} | {'Stake Ratio':<12}")
        print(f"   --------------------------------------------------------------")
        for sel, weight in zip(opt["selections"], opt["weights"]):
            # Format selection label
            line_str = f" {sel.line:+g}" if sel.line is not None else ""
            sel_label = f"{sel.market_type} {sel.name}{line_str}"
            print(f"   {sel.bookmaker:<15} | {sel_label:<25} | {sel.odds:<6.2f} | {weight*100:>10.2f}%")
        print(f"   --------------------------------------------------------------")
        
        # Display simulated payoff for $1000 total stake
        total_stake = 1000.0
        profit = total_stake * (opt['return_multiplier'] - 1.0)
        print(f"   💵 Example Stake Allocation for $1,000 Budget:")
        for sel, weight in zip(opt["selections"], opt["weights"]):
            line_str = f" {sel.line:+g}" if sel.line is not None else ""
            sel_label = f"{sel.market_type} {sel.name}{line_str}"
            print(f"      - {sel.bookmaker} ({sel_label}): Bet ${total_stake * weight:.2f}")
        print(f"      👉 Guaranteed Payout: ${total_stake * opt['return_multiplier']:.2f} (Net Profit: ${profit:.2f})")
    print(f"==================================================================")


def print_value_bet_report(selections: List[BetSelection], probabilities: Dict[int, float], is_tg: bool, match_info: MatchInfo):
    results = calculate_expected_values(selections, probabilities, is_tg)
    print(f"\n==================================================================")
    print(f"📈 VALUE BET ANALYSIS: {match_info.home_team} vs {match_info.away_team}")
    print(f"   Model: {'Total Goals (TG)' if is_tg else 'Goal Difference (GD)'}")
    print(f"==================================================================")
    
    print(f"\n   {'Bookmaker':<15} | {'Selection':<20} | {'Odds':<6} | {'EV':<8} | {'Kelly Fraction':<15}")
    print(f"   ----------------------------------------------------------------------------")
    
    value_bets_found = False
    for res in results:
        sel = res["selection"]
        ev = res["expected_value"]
        kelly = res["kelly_fraction"]
        
        line_str = f" {sel.line:+g}" if sel.line is not None else ""
        sel_label = f"{sel.market_type} {sel.name}{line_str}"
        
        ev_str = f"\033[92m{ev:.3f}\033[0m" if ev > 1.0 else f"{ev:.3f}"
        kelly_str = f"\033[92m{kelly*100:.2f}%\033[0m" if kelly > 0 else "0.00%"
        
        if ev > 1.0:
            value_bets_found = True
            
        print(f"   {sel.bookmaker:<15} | {sel_label:<20} | {sel.odds:<6.2f} | {ev_str:<17} | {kelly_str:<24}")
        
    print(f"   ----------------------------------------------------------------------------")
    if not value_bets_found:
        print("   ❌ No selections with EV > 1.0 found based on your probability estimates.")
    else:
        print("   💡 Selections with EV > 1.0 are highlighted. Kelly fraction represents the ")
        print("      optimal portion of your bankroll to wager on that single bet.")
    print(f"==================================================================")


def load_odds_data(filepath: str) -> OddsData:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Odds file not found: {filepath}")
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return OddsData.model_validate(data)


def main():
    filepath = "odds.json"
    if len(sys.argv) > 1:
        filepath = sys.argv[1]

    try:
        data = load_odds_data(filepath)
    except FileNotFoundError:
        print(f"\n❌ Error: File '{filepath}' not found.")
        print("Please ensure you have generated an 'odds.json' file using the AI Vision Agent.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error validating odds data: {e}")
        sys.exit(1)

    # 1. Run Arbitrage Search
    opportunities = search_arbitrage(data.selections)
    print_arbitrage_report(opportunities, data.match_info)

    # 2. Check if user wants to run a value bet check
    # Check if a custom probabilities file exists, e.g. "probs.json"
    if os.path.exists("probs.json"):
        try:
            with open("probs.json", "r") as f:
                prob_data = json.load(f)
            
            # Can specify 'gd_probs' or 'tg_probs'
            if "gd_probs" in prob_data:
                # Convert keys back to int
                gd_probs = {int(k): float(v) for k, v in prob_data["gd_probs"].items()}
                # Validate sum
                if abs(sum(gd_probs.values()) - 1.0) > 0.05:
                    print("\n⚠️ Warning: gd_probs in probs.json does not sum to 1.0. Normalizing...")
                    total = sum(gd_probs.values())
                    gd_probs = {k: v / total for k, v in gd_probs.items()}
                
                gd_sels = [s for s in data.selections if s.market_type.upper() in ["1X2", "AH", "DNB", "DC"]]
                if gd_sels:
                    print_value_bet_report(gd_sels, gd_probs, is_tg=False, match_info=data.match_info)

            if "tg_probs" in prob_data:
                tg_probs = {int(k): float(v) for k, v in prob_data["tg_probs"].items()}
                if abs(sum(tg_probs.values()) - 1.0) > 0.05:
                    print("\n⚠️ Warning: tg_probs in probs.json does not sum to 1.0. Normalizing...")
                    total = sum(tg_probs.values())
                    tg_probs = {k: v / total for k, v in tg_probs.items()}

                tg_sels = [s for s in data.selections if s.market_type.upper() in ["OU"]]
                if tg_sels:
                    print_value_bet_report(tg_sels, tg_probs, is_tg=True, match_info=data.match_info)

        except Exception as e:
            print(f"\n⚠️ Could not process probs.json for Value Bet calculations: {e}")

if __name__ == "__main__":
    main()
