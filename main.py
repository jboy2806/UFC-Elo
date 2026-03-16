"""
main.py
══════════════════════════════════════════════════════════════════════
Entry point for the UFC Elo rating system.

Runs the full pipeline in order:
  1. Load and sort the dataset
  2. Initialize every fighter at 1500 elo
  3. Process all fights chronologically and calculate ratings
  4. Apply final inactivity decay to retired/inactive fighters
  5. Export results to CSV
  6. Print leaderboards and fighter lookups

OUTPUT FILES:
  elo_current.csv  — one row per fighter, current elo + peak stats
  elo_history.csv  — one row per fight per fighter, full career log

FILE STRUCTURE:
  main.py         <- you are here
  data_loader.py  <- loads CSV, sorts fights, builds the dictionary
  elo.py          <- Elo formula, decay functions, and main loop
  bonuses.py      <- all bonus multiplier functions
  display.py      <- all print/display functions
  export.py       <- CSV export functions
══════════════════════════════════════════════════════════════════════
"""

from data_loader import load_fights, initialize_elo
from elo         import run_elo_loop, apply_final_decay
from display     import print_elo_rankings, print_peak_elo_rankings, print_fighter_history
from export      import export_current_elo, export_full_history, export_peak_elo
from export_report import export_markdown_report


# ── Step 1: Load ──────────────────────────────────────────────────────
print("\n━━━ LOADING DATA ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
df          = load_fights("UFC_merged.csv")
elo_ratings = initialize_elo(df)

# ── Step 2: Calculate ─────────────────────────────────────────────────
print("\n━━━ CALCULATING ELO ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
elo_ratings = run_elo_loop(df, elo_ratings)

# ── Step 3: Final decay (retired fighters) ────────────────────────────
print("\n━━━ APPLYING FINAL DECAY ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
apply_final_decay(elo_ratings)

# ── Step 4: Export to CSV ─────────────────────────────────────────────
print("\n━━━ EXPORTING TO CSV ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
export_current_elo(elo_ratings, df, filepath="elo_current.csv")
export_full_history(elo_ratings, df, filepath="elo_history.csv")
export_peak_elo(elo_ratings, df,     filepath="elo_peak.csv")
export_markdown_report(elo_ratings, df)

# ── Step 5: Print leaderboards ────────────────────────────────────────
print("\n━━━ RESULTS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print_elo_rankings(elo_ratings, df, top_n=50)
print_peak_elo_rankings(elo_ratings, df, top_n=50)

# ── Step 6: Individual fighter lookups ───────────────────────────────
# Partial names work: "khabib", "jones", "gsp"
print_fighter_history("Jon Jones",           elo_ratings, df)
print_fighter_history("Khabib Nurmagomedov", elo_ratings, df)
print_fighter_history("Georges St-Pierre",   elo_ratings, df)
