"""
data_loader.py
══════════════════════════════════════════════════════════════════════
Responsible for two things:
  1. Loading the UFC dataset from CSV and sorting it chronologically
  2. Creating the elo_ratings dictionary that will track every fighter

This module is always the first thing that runs in main.py.
══════════════════════════════════════════════════════════════════════
"""

import pandas as pd


def load_fights(filepath="UFC_merged.csv"):
    """
    Load the UFC dataset and sort every fight from oldest to newest.

    WHY WE SORT:
        Elo is a historical rating system — each fight's result affects
        both fighters' ratings going forward. If we processed fights
        out of order, a fighter could lose elo from a fight that
        hasn't happened yet, making all ratings meaningless.
        Sorting guarantees we always process history in the right order.

    WHY low_memory=False:
        Some columns (height, reach, etc.) have mixed types — some rows
        are numbers, others are strings like "None" or "---". Without
        this flag pandas guesses the type from chunks and sometimes gets
        it wrong, throwing a warning. low_memory=False reads the whole
        file before deciding types, which is slower but correct.

    PARAMETERS:
        filepath : path to the merged UFC CSV file

    RETURNS:
        df : pandas DataFrame sorted oldest fight → newest fight
    """
    df = pd.read_csv(filepath, low_memory=False)

    # Convert the date column from a plain string like "2020/01/18"
    # to a real datetime object so pandas can sort it correctly.
    # Without this, "2020/01/18" sorts as text which gives wrong order.
    df["date"] = pd.to_datetime(df["date"])

    # Sort ascending = True means 1994 comes first, 2026 comes last.
    # reset_index(drop=True) renumbers rows 0,1,2... after sorting
    # so .iloc[0] reliably gives the first fight and .iloc[-1] the last.
    df = df.sort_values(by="date", ascending=True).reset_index(drop=True)

    print(f"  → {len(df)} fights loaded")
    print(f"  → First: {df['date'].iloc[0].date()} — {df['r_name'].iloc[0]} vs {df['b_name'].iloc[0]}")
    print(f"  → Last:  {df['date'].iloc[-1].date()} — {df['r_name'].iloc[-1]} vs {df['b_name'].iloc[-1]}")

    return df


def initialize_elo(df, starting_elo=1500):
    """
    Build the elo_ratings dictionary — the core data structure of this project.

    STRUCTURE:
        elo_ratings = {
            'fighter_id_string': {
                'elo':     1500,   <- current elo rating (float)
                'fights':  0,      <- number of UFC fights processed so far
                'history': []      <- list of {'date': ..., 'elo': ...} snapshots
            },
            ...one entry per unique fighter...
        }

    WHY A DICTIONARY:
        We need to look up a fighter by their ID thousands of times —
        once per fighter per fight. A dictionary does this in O(1) time
        (instant lookup regardless of size). A list would require scanning
        through every entry each time, which would be very slow.

    WHY START AT 1500:
        1500 is the universal standard default in Elo systems. It places
        every fighter at the exact midpoint of the scale. Fighters above
        1500 are better than average, below 1500 are worse. This gives
        the ratings a meaningful reference point from the start.

    WHY COLLECT IDs FROM BOTH CORNERS:
        Every fight has an r_id (red corner) and b_id (blue corner).
        A fighter can appear in either corner across their career, so we
        need to scan both columns and merge them to get every unique ID.
        set() removes any duplicates automatically.

    PARAMETERS:
        df           : the sorted DataFrame returned by load_fights()
        starting_elo : initial elo for every fighter (default 1500)

    RETURNS:
        elo_ratings : dict mapping fighter_id -> {elo, fights, history}
    """

    # Collect every unique fighter ID from both corners
    all_ids = set(df["r_id"].tolist() + df["b_id"].tolist())

    # Initialize every fighter at the same starting point
    elo_ratings = {}
    for fighter_id in all_ids:
        elo_ratings[fighter_id] = {
            "elo":     starting_elo,
            "fights":  0,
            "history":       [],   # grows by 1 entry per fight
            "last_fight_date": None  # tracks when they last fought for decay
        }

    print(f"  → {len(elo_ratings)} fighters initialized at {starting_elo} elo")
    return elo_ratings
