"""
display.py
══════════════════════════════════════════════════════════════════════
All terminal print functions for displaying Elo results.

Contains four functions:
  1. print_elo_rankings()       — current elo leaderboard
  2. print_peak_elo_rankings()  — all-time peak elo leaderboard
  3. print_fighter_history()    — every fight for one specific fighter
                                  with elo before/after and gain/loss
  4. Helper functions           — get_name(), elo_bar(), elo_tier()
══════════════════════════════════════════════════════════════════════
"""


# ─────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────

def get_name(fighter_id, df):
    """
    Look up a fighter's display name from the DataFrame using their ID.

    We check the red corner column first, then the blue corner column,
    because a fighter could appear in either across their career.

    PARAMETERS:
        fighter_id : the 16-character hex ID string
        df         : the full fights DataFrame

    RETURNS:
        name string, or None if the fighter ID isn't found
    """
    name_row = df[df["r_id"] == fighter_id]["r_name"]
    if name_row.empty:
        name_row = df[df["b_id"] == fighter_id]["b_name"]
    if name_row.empty:
        return None
    return name_row.iloc[0]


def elo_bar(elo, min_elo=1400, max_elo=2200, bar_width=20):
    """
    Convert an elo number into a visual progress bar using block characters.

    The bar fills proportionally between min_elo and max_elo.
    A fighter at max_elo gets a full bar. At min_elo the bar is empty.

    Example output:  [████████████░░░░░░░░]

    PARAMETERS:
        elo       : the elo value to visualize
        min_elo   : elo that represents an empty bar (default 1400)
        max_elo   : elo that represents a full bar (default 2200)
        bar_width : total number of characters in the bar (default 20)

    RETURNS:
        string like "[████████░░░░░░░░░░░░]"
    """
    # Clamp ratio between 0 and 1 so the bar never overflows or goes negative
    ratio  = max(0, min(1, (elo - min_elo) / (max_elo - min_elo)))
    filled = int(ratio * bar_width)
    empty  = bar_width - filled
    return f"[{'█' * filled}{'░' * empty}]"


def elo_tier(elo):
    """
    Assign a human-readable tier label based on elo rating.

    Tiers are subjective but calibrated so that all-time greats
    (Jones, Khabib, GSP) sit in GOAT/Elite, active champions sit
    in Top 10/Contender, and average UFC fighters sit around Average.

    RETURNS:
        10-character padded string label
    """
    if elo >= 1800: return "GOAT      "
    if elo >= 1650: return "Elite     "
    if elo >= 1620: return "Good    "
    if elo >= 1570: return "Above Average"
    if elo >= 1500: return "Average   "
    return                 "Below avg "


def result_symbol(elo_change):
    """
    Return a simple symbol showing whether the fighter won or lost elo.

    RETURNS:
        "W" if elo went up, "L" if elo went down, "D" if unchanged
    """
    if elo_change > 0.05:
        return "W"
    elif elo_change < -0.05:
        return "L"
    else:
        return "D"


# ─────────────────────────────────────────────────────────────────────
# 1. CURRENT ELO RANKINGS
# ─────────────────────────────────────────────────────────────────────

def print_elo_rankings(elo_ratings, df, top_n=20):
    """
    Print a leaderboard of all fighters sorted by their CURRENT elo.

    Current elo = where they stand today, after all their UFC fights.
    A fighter who peaked at 1900 but lost 3 in a row might now sit
    at 1700 — that's what this table shows.

    Includes:
      - Rank with medals for top 3
      - Fighter name
      - Current elo value
      - Tier label (GOAT → Below avg)
      - Visual bar showing elo strength
      - Total UFC fights processed

    PARAMETERS:
        elo_ratings : the fully calculated elo dictionary
        df          : the fights DataFrame (used to look up names)
        top_n       : how many fighters to display (default 20)
    """

    # Build a list of (name, elo, fights) for every fighter
    rankings = []
    for fighter_id, data in elo_ratings.items():
        name = get_name(fighter_id, df)
        if name is None:
            continue
        rankings.append((name, data["elo"], data["fights"]))

    # Sort by current elo, highest first
    rankings.sort(key=lambda x: x[1], reverse=True)
    rankings = rankings[:top_n]

    # ── Print table ───────────────────────────────────────────────────
    width = 80
    print("\n" + "═" * width)
    print(f"{'UFC ELO RANKINGS — CURRENT':^{width}}")
    print("═" * width)
    print(f"  {'#':<5} {'FIGHTER':<22} {'ELO':<8} {'TIER':<12} {'BAR':<24} {'FIGHTS'}")
    print("─" * width)

    for i, (name, elo, fights) in enumerate(rankings, start=1):
        bar  = elo_bar(elo)
        tier = elo_tier(elo)

        # Gold/silver/bronze medals for top 3, number for the rest
        if i == 1:   medal = "🥇"
        elif i == 2: medal = "🥈"
        elif i == 3: medal = "🥉"
        else:        medal = f"{i:<2}."

        print(f"  {medal:<5} {name:<22} {elo:<8.1f} {tier:<12} {bar}  {fights}")

    print("─" * width)
    print(f"  Showing top {len(rankings)} of {len(elo_ratings)} fighters")
    print("═" * width + "\n")


# ─────────────────────────────────────────────────────────────────────
# 2. PEAK ELO RANKINGS
# ─────────────────────────────────────────────────────────────────────

def print_peak_elo_rankings(elo_ratings, df, top_n=20):
    """
    Print a leaderboard sorted by each fighter's ALL-TIME PEAK elo.

    Peak elo = the single highest rating a fighter ever reached.
    This is different from current elo — Khabib retired unbeaten so
    his current and peak are the same. A fighter who dominated for
    years and then faded will rank higher here than in current rankings.

    Also shows the gap between their peak and current elo, which
    reveals how far a fighter has declined (or hasn't).

    Includes:
      - Rank with medals for top 3
      - Fighter name
      - Peak elo value
      - Date the peak was reached
      - Current elo
      - Change from peak (negative = declined, positive = still rising)
      - Total UFC fights

    PARAMETERS:
        elo_ratings : the fully calculated elo dictionary
        df          : the fights DataFrame (used to look up names)
        top_n       : how many fighters to display (default 20)
    """

    rankings = []
    for fighter_id, data in elo_ratings.items():
        # Skip fighters with no fight history
        if not data["history"]:
            continue

        name = get_name(fighter_id, df)
        if name is None:
            continue

        # Find the single best entry in the history list
        peak      = max(data["history"], key=lambda x: x["elo"])
        peak_elo  = peak["elo"]
        peak_date = str(peak["date"])[:10]   # trim to YYYY-MM-DD
        curr_elo  = data["elo"]
        diff      = curr_elo - peak_elo       # negative means declined

        rankings.append((name, peak_elo, peak_date, curr_elo, diff, data["fights"]))

    rankings.sort(key=lambda x: x[1], reverse=True)
    rankings = rankings[:top_n]

    # ── Print table ───────────────────────────────────────────────────
    width = 90
    print("\n" + "═" * width)
    print(f"{'UFC ELO RANKINGS — ALL TIME PEAK':^{width}}")
    print("═" * width)
    print(f"  {'#':<5} {'FIGHTER':<22} {'PEAK ELO':<10} {'PEAK DATE':<13} {'CURRENT':<10} {'CHANGE':<10} {'FIGHTS'}")
    print("─" * width)

    for i, (name, peak_elo, peak_date, curr_elo, diff, fights) in enumerate(rankings, start=1):
        # Format the change with explicit + or - sign
        diff_str = f"+{diff:.1f}" if diff >= 0 else f"{diff:.1f}"

        if i == 1:   medal = "🥇"
        elif i == 2: medal = "🥈"
        elif i == 3: medal = "🥉"
        else:        medal = f"{i:<2}."

        print(f"  {medal:<5} {name:<22} {peak_elo:<10.1f} {peak_date:<13} {curr_elo:<10.1f} {diff_str:<10} {fights}")

    print("─" * width)
    print(f"  Showing top {len(rankings)} of {len(elo_ratings)} fighters")
    print("═" * width + "\n")


# ─────────────────────────────────────────────────────────────────────
# 3. SINGLE FIGHTER FIGHT HISTORY
# ─────────────────────────────────────────────────────────────────────

def print_fighter_history(name_query, elo_ratings, df):
    """
    Print the complete fight-by-fight elo history for one fighter.

    For each fight shows:
      - Date
      - Opponent name
      - Win / Loss / D/NC result
      - Method of victory or loss
      - Elo BEFORE the fight (post-decay, pre-fight — the actual value
        the Elo formula used as its starting point)
      - Elo AFTER the fight (the result of the formula)
      - Change = AFTER - BEFORE (purely the fight result, decay excluded)

    WHY elo_before IS NOW CORRECT:
        In previous versions, BEFORE was taken from the previous fight's
        AFTER value. This made it look like wins caused elo to drop when
        there was a long gap between fights — the decay that happened in
        between was invisible. Now each history entry stores elo_before
        (the post-decay, pre-fight value), so CHANGE reflects only what
        the fight result itself did to the rating.

    PARAMETERS:
        name_query  : partial or full name string (case insensitive)
        elo_ratings : the fully calculated elo dictionary
        df          : the fights DataFrame
    """
    import pandas as pd

    # ── Find the fighter ──────────────────────────────────────────────
    match_r = df[df["r_name"].str.contains(name_query, case=False, na=False)]
    match_b = df[df["b_name"].str.contains(name_query, case=False, na=False)]

    if match_r.empty and match_b.empty:
        print(f"\n  Fighter '{name_query}' not found in dataset.\n")
        return

    if not match_r.empty:
        fighter_id   = match_r["r_id"].iloc[0]
        fighter_name = match_r["r_name"].iloc[0]
    else:
        fighter_id   = match_b["b_id"].iloc[0]
        fighter_name = match_b["b_name"].iloc[0]

    data = elo_ratings[fighter_id]

    # ── Gather all fights for this fighter ────────────────────────────
    fights_r = df[df["r_id"] == fighter_id].copy()
    fights_b = df[df["b_id"] == fighter_id].copy()

    fights_r["opponent"] = fights_r["b_name"]
    fights_b["opponent"] = fights_b["r_name"]

    all_fights = pd.DataFrame({
        "date":      list(fights_r["date"])      + list(fights_b["date"]),
        "opponent":  list(fights_r["opponent"])  + list(fights_b["opponent"]),
        "method":    list(fights_r["method"])    + list(fights_b["method"]),
        "winner_id": list(fights_r["winner_id"]) + list(fights_b["winner_id"]),
    }).sort_values("date").reset_index(drop=True)

    history  = data["history"]
    curr_elo = data["elo"]
    peak     = max(history, key=lambda x: x["elo"])

    # ── Summary header ────────────────────────────────────────────────
    width = 90
    print("\n" + "═" * width)
    print(f"  {fighter_name.upper()}")
    print("═" * width)
    print(f"  Current Elo : {curr_elo:.1f}  {elo_bar(curr_elo)}  {elo_tier(curr_elo)}")
    print(f"  Peak Elo    : {peak['elo']:.1f}  ({str(peak['date'])[:10]})")
    print(f"  UFC Fights  : {data['fights']}")
    print("─" * width)
    print(f"  {'#':<4} {'DATE':<13} {'OPPONENT':<25} {'RES':<5} {'METHOD':<26} {'BEFORE':<8} {'AFTER':<8} {'CHANGE'}")
    print("─" * width)

    # ── Per-fight rows ────────────────────────────────────────────────
    fight_changes = []   # collect for summary stats at the bottom

    for i, (_, fight) in enumerate(all_fights.iterrows()):
        if i >= len(history):
            break

        entry = history[i]

        # elo_before: post-decay, pre-fight value stored in the history entry.
        # Falls back to 1500 for debut fights (older history entries may
        # not have elo_before if the dataset was run before this fix).
        elo_before = entry.get("elo_before", 1500.0 if i == 0 else history[i-1]["elo"])
        elo_after  = entry["elo"]
        elo_change = elo_after - elo_before

        # ── Determine result ──────────────────────────────────────────
        # Compare winner_id directly to fighter_id — simple and correct.
        # The old version did an indirect DataFrame lookup which broke
        # on type mismatches and returned wrong results.
        winner_id = fight["winner_id"]
        if pd.isna(winner_id):
            result = "D/NC"
        elif str(winner_id) == str(fighter_id):
            result = "WIN"
        else:
            result = "LOSS"

        # ── Format change ─────────────────────────────────────────────
        change_str = f"{'+' if elo_change >= 0 else ''}{elo_change:.1f}"
        if elo_change > 0.05:
            change_display = f"▲ {change_str}"
        elif elo_change < -0.05:
            change_display = f"▼ {change_str}"
        else:
            change_display = f"  {change_str}"

        date_str     = str(fight["date"])[:10]
        opponent     = str(fight["opponent"])[:24]
        method_short = str(fight["method"])[:25]

        print(f"  {i+1:<4} {date_str:<13} {opponent:<25} {result:<5} {method_short:<26} {elo_before:<8.1f} {elo_after:<8.1f} {change_display}")

        # Track fight changes by result for summary stats
        if result in ("WIN", "LOSS"):
            fight_changes.append((result, elo_change))

    # ── Career summary ────────────────────────────────────────────────
    wins   = [c for r, c in fight_changes if r == "WIN"]
    losses = [c for r, c in fight_changes if r == "LOSS"]

    print("─" * width)
    if wins:
        print(f"  Avg elo per win    : +{sum(wins)/len(wins):.1f}   Best  : +{max(wins):.1f}")
    if losses:
        print(f"  Avg elo per loss   :  {sum(losses)/len(losses):.1f}   Worst :  {min(losses):.1f}")
    print("═" * width + "\n")
