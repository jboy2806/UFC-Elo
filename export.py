"""
export.py
══════════════════════════════════════════════════════════════════════
Functions to export Elo results to CSV files.

Contains two functions:
  1. export_current_elo()  — one row per fighter, current elo + stats
  2. export_full_history() — one row per fight per fighter, full career

USAGE (in main.py):
    from export import export_current_elo, export_full_history

    export_current_elo(elo_ratings, df)
    export_full_history(elo_ratings, df)
══════════════════════════════════════════════════════════════════════
"""

import pandas as pd


def get_name(fighter_id, df):
    """Look up fighter name from the DataFrame by ID (checks both corners)."""
    row = df[df["r_id"] == fighter_id]["r_name"]
    if row.empty:
        row = df[df["b_id"] == fighter_id]["b_name"]
    return row.iloc[0] if not row.empty else None


def export_current_elo(elo_ratings, df, filepath="elo_current.csv"):
    """
    Export one row per fighter with their current standing.

    COLUMNS:
        fighter_id   : unique ID string from the dataset
        name         : fighter's display name
        elo          : current elo (after all fights + final decay)
        peak_elo     : highest elo they ever reached
        peak_date    : date of that peak
        fights       : total UFC fights in the dataset
        last_fight   : date of their most recent fight
        elo_vs_peak  : current elo minus peak elo (negative = declined)

    Sorted by current elo descending (best fighter first).

    PARAMETERS:
        elo_ratings : fully computed elo dictionary
        df          : the fights DataFrame (used to look up names)
        filepath    : output file path (default: elo_current.csv)
    """
    rows = []

    for fighter_id, data in elo_ratings.items():
        name = get_name(fighter_id, df)
        if name is None or not data["history"]:
            continue

        peak_entry = max(data["history"], key=lambda x: x["elo"])

        rows.append({
            "name":        name,
            "elo":         round(data["elo"], 2),
            "peak_elo":    round(peak_entry["elo"], 2),
            "peak_date":   str(peak_entry["date"])[:10],
            "fights":      data["fights"],
            "last_fight":  str(data["last_fight_date"])[:10] if data["last_fight_date"] else None,
            "elo_vs_peak": round(data["elo"] - peak_entry["elo"], 2),
        })

    result = (
        pd.DataFrame(rows)
        .sort_values("elo", ascending=False)
        .reset_index(drop=True)
    )

    # Add rank column (1 = best current elo)
    result.insert(0, "rank", range(1, len(result) + 1))

    result.to_csv(filepath, index=False)
    print(f"  → Exported {len(result)} fighters to '{filepath}'")
    return result


def export_full_history(elo_ratings, df, filepath="elo_history.csv"):
    """
    Export one row per fight per fighter — the complete career log.

    COLUMNS:
        fighter_id   : unique ID string
        name         : fighter's display name
        fight_num    : sequential fight number in their UFC career (1, 2, 3...)
        date         : date of the fight
        opponent     : opponent's name
        result       : WIN / LOSS / D/NC
        method       : method of victory/loss
        elo_before   : elo entering the fight (post-decay, pre-fight)
        elo_after    : elo after the fight result
        elo_change   : elo_after - elo_before (fight result only, no decay)

    Sorted by fighter name, then chronologically within each fighter.
    Useful for plotting career arcs or doing further analysis in Excel/pandas.

    PARAMETERS:
        elo_ratings : fully computed elo dictionary
        df          : the fights DataFrame (used to look up opponents/results)
        filepath    : output file path (default: elo_history.csv)
    """
    rows = []

    for fighter_id, data in elo_ratings.items():
        name = get_name(fighter_id, df)
        if name is None or not data["history"]:
            continue

        # Get all fights for this fighter from both corners
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

        history = data["history"]

        for i, (_, fight) in enumerate(all_fights.iterrows()):
            if i >= len(history):
                break

            entry = history[i]
            elo_before = entry.get("elo_before", 1500.0 if i == 0 else history[i-1]["elo"])
            elo_after  = entry["elo"]
            elo_change = elo_after - elo_before

            winner_id = fight["winner_id"]
            if pd.isna(winner_id):
                result = "D/NC"
            elif str(winner_id) == str(fighter_id):
                result = "WIN"
            else:
                result = "LOSS"

            rows.append({
                "name":        name,
                "fight_num":   i + 1,
                "date":        str(fight["date"])[:10],
                "opponent":    fight["opponent"],
                "result":      result,
                "method":      fight["method"],
                "elo_before":  round(elo_before, 2),
                "elo_after":   round(elo_after, 2),
                "elo_change":  round(elo_change, 2),
            })

    result = (
        pd.DataFrame(rows)
        .sort_values(["name", "date"])
        .reset_index(drop=True)
    )

    result.to_csv(filepath, index=False)
    print(f"  → Exported {len(result)} fight records to '{filepath}'")
    return result

def export_peak_elo(elo_ratings, df, filepath="elo_peak.csv"):
    """
    Export one row per fighter sorted by their all-time PEAK elo.

    COLUMNS:
        rank         : all-time rank by peak elo (1 = highest ever)
        fighter_id   : unique ID string
        name         : fighter's display name
        peak_elo     : highest elo they ever reached during their career
        peak_date    : date that peak was achieved
        current_elo  : elo right now (after final decay)
        elo_vs_peak  : current_elo - peak_elo (negative = declined from peak)
        fights       : total UFC fights in the dataset
        last_fight   : date of most recent fight

    Sorted by peak_elo descending — rank 1 is the greatest of all time
    by this metric, regardless of what they're rated today.

    PARAMETERS:
        elo_ratings : fully computed elo dictionary (with final decay applied)
        df          : the fights DataFrame
        filepath    : output path (default: elo_peak.csv)
    """
    rows = []

    for fighter_id, data in elo_ratings.items():
        name = get_name(fighter_id, df)
        if name is None or not data["history"]:
            continue

        peak_entry = max(data["history"], key=lambda x: x["elo"])

        rows.append({
            "name":        name,
            "peak_elo":    round(peak_entry["elo"], 2),
            "peak_date":   str(peak_entry["date"])[:10],
            "current_elo": round(data["elo"], 2),
            "elo_vs_peak": round(data["elo"] - peak_entry["elo"], 2),
            "fights":      data["fights"],
            "last_fight":  str(data["last_fight_date"])[:10] if data["last_fight_date"] else None,
        })

    result = (
        pd.DataFrame(rows)
        .sort_values("peak_elo", ascending=False)
        .reset_index(drop=True)
    )

    result.insert(0, "rank", range(1, len(result) + 1))

    result.to_csv(filepath, index=False)
    print(f"  → Exported {len(result)} fighters to '{filepath}'")
    return result
