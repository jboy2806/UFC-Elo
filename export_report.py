"""
export_report.py
══════════════════════════════════════════════════════════════════════
Generates a professional Markdown report of the top 50 fighters
by both current and peak Elo, with full fight-by-fight history
for each fighter.

USAGE (in main.py):
    from export_report import export_markdown_report
    export_markdown_report(elo_ratings, df)

OUTPUT:
    ufc_elo_report.md  — full report, ~thousands of lines
══════════════════════════════════════════════════════════════════════
"""

import pandas as pd
from datetime import date as date_type


# ─────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────

def _get_name(fighter_id, df):
    row = df[df["r_id"] == fighter_id]["r_name"]
    if row.empty:
        row = df[df["b_id"] == fighter_id]["b_name"]
    return row.iloc[0] if not row.empty else None


def _elo_bar(elo, min_elo=1400, max_elo=1900, width=20):
    """Unicode block bar for markdown code blocks."""
    ratio  = max(0.0, min(1.0, (elo - min_elo) / (max_elo - min_elo)))
    filled = int(ratio * width)
    return "█" * filled + "░" * (width - filled)


def _tier(elo):
    if elo >= 1800: return "🐐 GOAT"
    if elo >= 1720: return "⭐ Elite"
    if elo >= 1660: return "🔥 Top 10"
    if elo >= 1580: return "💪 Contender"
    if elo >= 1500: return "✅ Average"
    return                 "📉 Below Avg"


def _medal(rank):
    if rank == 1: return "🥇"
    if rank == 2: return "🥈"
    if rank == 3: return "🥉"
    return f"#{rank}"


def _get_fight_history(fighter_id, data, df):
    """
    Build a list of fight dicts for one fighter, sorted chronologically.
    Each dict has: date, opponent, result, method, elo_before, elo_after, elo_change
    """
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
    rows    = []

    for i, (_, fight) in enumerate(all_fights.iterrows()):
        if i >= len(history):
            break
        entry      = history[i]
        elo_before = entry.get("elo_before", 1500.0 if i == 0 else history[i-1]["elo"])
        elo_after  = entry["elo"]
        elo_change = elo_after - elo_before

        winner_id = fight["winner_id"]
        if pd.isna(winner_id):
            result = "D/NC"
        elif str(winner_id) == str(fighter_id):
            result = "W"
        else:
            result = "L"

        rows.append({
            "num":        i + 1,
            "date":       str(fight["date"])[:10],
            "opponent":   str(fight["opponent"]),
            "result":     result,
            "method":     str(fight["method"]),
            "elo_before": elo_before,
            "elo_after":  elo_after,
            "elo_change": elo_change,
        })

    return rows


def _format_change(val):
    sign = "+" if val >= 0 else ""
    return f"{sign}{val:.1f}"


def _result_icon(result):
    if result == "W":    return "✅ W"
    if result == "L":    return "❌ L"
    return                      "➖ D"


# ─────────────────────────────────────────────────────────────────────
# FIGHTER SECTION BUILDER
# ─────────────────────────────────────────────────────────────────────

def _fighter_section(rank, fighter_id, data, df, sort_key="current"):
    """
    Render a full markdown section for one fighter.
    sort_key: "current" or "peak" — controls which elo is shown as headline.
    """
    name      = _get_name(fighter_id, df)
    curr_elo  = data["elo"]
    history   = data["history"]
    fights    = data["fight_history"]   # pre-built list of dicts
    peak_entry = max(history, key=lambda x: x["elo"])
    peak_elo   = peak_entry["elo"]
    peak_date  = str(peak_entry["date"])[:10]
    last_fight = str(data["last_fight_date"])[:10] if data["last_fight_date"] else "—"

    headline_elo = curr_elo if sort_key == "current" else peak_elo

    lines = []

    # ── Fighter header ────────────────────────────────────────────────
    lines.append(f"\n---\n")
    lines.append(f"## {_medal(rank)} {name}\n")
    lines.append(f"```")
    lines.append(f"{'Elo':12}  {headline_elo:.1f}   {_elo_bar(headline_elo)}")
    lines.append(f"{'Tier':12}  {_tier(headline_elo)}")
    if sort_key == "current":
        lines.append(f"{'Peak Elo':12}  {peak_elo:.1f}  ({peak_date})")
        lines.append(f"{'vs Peak':12}  {_format_change(curr_elo - peak_elo)}")
    else:
        lines.append(f"{'Current Elo':12}  {curr_elo:.1f}")
        lines.append(f"{'vs Peak':12}  {_format_change(curr_elo - peak_elo)}")
    lines.append(f"{'UFC Fights':12}  {data['fights']}")
    lines.append(f"{'Last Fight':12}  {last_fight}")
    lines.append(f"```\n")

    # ── Fight history table ───────────────────────────────────────────
    if not fights:
        lines.append("*No fight history available.*\n")
        return "\n".join(lines)

    lines.append("| # | Date | Opponent | Result | Method | Before | After | Change |")
    lines.append("|---|------|----------|--------|--------|-------:|------:|-------:|")

    wins = losses = 0
    best_win = worst_loss = 0.0

    for f in fights:
        change_str = _format_change(f["elo_change"])
        if f["elo_change"] > 0.05:
            change_cell = f"▲ **{change_str}**"
        elif f["elo_change"] < -0.05:
            change_cell = f"▼ {change_str}"
        else:
            change_cell = f"  {change_str}"

        result_cell = _result_icon(f["result"])

        lines.append(
            f"| {f['num']} "
            f"| {f['date']} "
            f"| {f['opponent']} "
            f"| {result_cell} "
            f"| {f['method']} "
            f"| {f['elo_before']:.1f} "
            f"| {f['elo_after']:.1f} "
            f"| {change_cell} |"
        )

        if f["result"] == "W":
            wins += 1
            best_win = max(best_win, f["elo_change"])
        elif f["result"] == "L":
            losses += 1
            worst_loss = min(worst_loss, f["elo_change"])

    # ── Career mini-stats ─────────────────────────────────────────────
    win_changes  = [f["elo_change"] for f in fights if f["result"] == "W"]
    loss_changes = [f["elo_change"] for f in fights if f["result"] == "L"]
    avg_win  = sum(win_changes)  / len(win_changes)  if win_changes  else 0
    avg_loss = sum(loss_changes) / len(loss_changes) if loss_changes else 0

    lines.append(f"\n> **{wins}W – {losses}L** &nbsp;|&nbsp; "
                 f"Avg gain: **+{avg_win:.1f}** &nbsp;|&nbsp; "
                 f"Avg loss: **{avg_loss:.1f}** &nbsp;|&nbsp; "
                 f"Best win: **+{best_win:.1f}** &nbsp;|&nbsp; "
                 f"Worst loss: **{worst_loss:.1f}**\n")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────
# SUMMARY TABLE BUILDER
# ─────────────────────────────────────────────────────────────────────

def _summary_table(rankings, sort_key):
    """Compact top-50 overview table at the top of each section."""
    lines = []
    if sort_key == "current":
        lines.append("| Rank | Fighter | Elo | Tier | Peak | vs Peak | Fights |")
        lines.append("|------|---------|----:|------|-----:|--------:|-------:|")
        for rank, (fid, data, name) in enumerate(rankings, 1):
            peak = max(data["history"], key=lambda x: x["elo"])["elo"]
            diff = data["elo"] - peak
            lines.append(
                f"| {_medal(rank)} | {name} | **{data['elo']:.1f}** "
                f"| {_tier(data['elo'])} | {peak:.1f} "
                f"| {_format_change(diff)} | {data['fights']} |"
            )
    else:
        lines.append("| Rank | Fighter | Peak Elo | Peak Date | Current | vs Peak | Fights |")
        lines.append("|------|---------|--------:|-----------|--------:|--------:|-------:|")
        for rank, (fid, data, name) in enumerate(rankings, 1):
            peak_entry = max(data["history"], key=lambda x: x["elo"])
            peak_elo   = peak_entry["elo"]
            peak_date  = str(peak_entry["date"])[:10]
            diff       = data["elo"] - peak_elo
            lines.append(
                f"| {_medal(rank)} | {name} | **{peak_elo:.1f}** "
                f"| {peak_date} | {data['elo']:.1f} "
                f"| {_format_change(diff)} | {data['fights']} |"
            )
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────
# MAIN EXPORT FUNCTION
# ─────────────────────────────────────────────────────────────────────

def export_markdown_report(elo_ratings, df, filepath="ufc_elo_report.md", top_n=50):
    """
    Generate a full Markdown report of the top N fighters by current
    and peak Elo, with complete fight-by-fight history for each.

    STRUCTURE:
        # Title & metadata
        ## Table of Contents
        # Part I — Current Elo Top 50
          - Summary table
          - Each fighter: stats card + full fight history table
        # Part II — All-Time Peak Elo Top 50
          - Summary table
          - Each fighter: stats card + full fight history table

    PARAMETERS:
        elo_ratings : fully computed elo dict (with final decay applied)
        df          : fights DataFrame
        filepath    : output markdown file path
        top_n       : number of fighters per section (default 50)
    """

    today = str(date_type.today())

    # ── Pre-build fight histories (shared between both sections) ──────
    print("  → Building fight histories...")
    for fighter_id, data in elo_ratings.items():
        data["fight_history"] = _get_fight_history(fighter_id, data, df)

    # ── Build ranked lists ────────────────────────────────────────────
    all_fighters = []
    for fighter_id, data in elo_ratings.items():
        name = _get_name(fighter_id, df)
        if name and data["history"]:
            all_fighters.append((fighter_id, data, name))

    current_top = sorted(all_fighters, key=lambda x: x[1]["elo"],  reverse=True)[:top_n]
    peak_top    = sorted(
        all_fighters,
        key=lambda x: max(x[1]["history"], key=lambda h: h["elo"])["elo"],
        reverse=True
    )[:top_n]

    total_fighters = len(all_fighters)
    total_fights   = sum(d["fights"] for _, d, _ in all_fighters) // 2  # each fight counted twice

    lines = []

    # ══════════════════════════════════════════════════════════════════
    # COVER
    # ══════════════════════════════════════════════════════════════════
    lines.append("# 🥊 UFC Elo Rating Report\n")
    lines.append(f"> Generated on **{today}** &nbsp;|&nbsp; "
                 f"**{total_fighters}** fighters &nbsp;|&nbsp; "
                 f"**{total_fights:,}** fights analysed\n")
    lines.append("---\n")

    # ── Table of contents ─────────────────────────────────────────────
    lines.append("## 📋 Table of Contents\n")
    lines.append("- [Part I — Current Elo Top 50](#part-i--current-elo-top-50)")
    lines.append("  - [Summary Table](#summary-table-current)")
    lines.append("  - Fighter profiles (ranked #1 → #50)")
    lines.append("- [Part II — All-Time Peak Elo Top 50](#part-ii--all-time-peak-elo-top-50)")
    lines.append("  - [Summary Table](#summary-table-peak)")
    lines.append("  - Fighter profiles (ranked #1 → #50)\n")
    lines.append("---\n")

    # ── How to read ───────────────────────────────────────────────────
    lines.append("## ℹ️ How to Read This Report\n")
    lines.append("| Symbol | Meaning |")
    lines.append("|--------|---------|")
    lines.append("| ▲ **+N** | Elo gained from this fight |")
    lines.append("| ▼ −N | Elo lost from this fight |")
    lines.append("| ✅ W | Win |")
    lines.append("| ❌ L | Loss |")
    lines.append("| ➖ D | Draw or No Contest |")
    lines.append("| Before / After | Elo entering and leaving the fight |")
    lines.append("| vs Peak | How far current Elo is from their career high |\n")
    lines.append("> **Note:** *Before* reflects post-inactivity-decay elo. "
                 "Gaps between fights where a fighter lost elo to inactivity "
                 "will appear as a lower *Before* than the previous *After*.\n")
    lines.append("---\n")

    # ══════════════════════════════════════════════════════════════════
    # PART I — CURRENT ELO
    # ══════════════════════════════════════════════════════════════════
    lines.append("# Part I — Current Elo Top 50\n")
    lines.append("> Rankings based on each fighter's **current** Elo rating — "
                 "where they stand today after all fights and inactivity decay.\n")
    lines.append(f"<a name='summary-table-current'></a>\n")
    lines.append("## Summary Table — Current\n")
    lines.append(_summary_table(current_top, "current"))
    lines.append("\n---\n")
    lines.append("## Fighter Profiles — Current\n")

    print(f"  → Writing current top {top_n} profiles...")
    for rank, (fighter_id, data, name) in enumerate(current_top, 1):
        lines.append(_fighter_section(rank, fighter_id, data, df, sort_key="current"))

    # ══════════════════════════════════════════════════════════════════
    # PART II — PEAK ELO
    # ══════════════════════════════════════════════════════════════════
    lines.append("\n---\n")
    lines.append("# Part II — All-Time Peak Elo Top 50\n")
    lines.append("> Rankings based on each fighter's **highest ever** Elo — "
                 "the single best rating they achieved at any point in their career.\n")
    lines.append(f"<a name='summary-table-peak'></a>\n")
    lines.append("## Summary Table — Peak\n")
    lines.append(_summary_table(peak_top, "peak"))
    lines.append("\n---\n")
    lines.append("## Fighter Profiles — Peak\n")

    print(f"  → Writing peak top {top_n} profiles...")
    for rank, (fighter_id, data, name) in enumerate(peak_top, 1):
        lines.append(_fighter_section(rank, fighter_id, data, df, sort_key="peak"))

    # ── Footer ────────────────────────────────────────────────────────
    lines.append("\n---\n")
    lines.append("*Report generated by the UFC Elo Rating System. "
                 "Ratings are based on fight results, method of victory, "
                 "statistical domination, upset bonuses, and inactivity decay.*\n")

    # ── Write file ────────────────────────────────────────────────────
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    size_kb = len("\n".join(lines).encode("utf-8")) / 1024
    print(f"  → Report written to '{filepath}'  ({size_kb:.0f} KB)")
