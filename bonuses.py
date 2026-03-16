"""
bonuses.py
══════════════════════════════════════════════════════════════════════
All bonus multiplier functions used in the Elo calculation.

HOW BONUSES WORK:
    Every fight has a base K factor of 40. Each bonus function returns
    a multiplier that gets applied to K. All multipliers are combined
    together at the end in GetKAdj().

    Example:
        K=40, KO finish (x1.15), underdog win (x1.07)
        → K_adj = 40 * 1.15 * 1.07 = 49.2

    A higher K_adj means the fight moves both fighters' ratings more.
    A lower K_adj (below 1.0 multiplier) dampens the swing.

BONUS SUMMARY:
    1. Finish        KO/TKO/Sub/Doctor Stoppage    x1.15
                     Split Decision                x0.95
    2. Domination    Unanimous decisions only       x1.10
    3. Underdog      Winner had >70 elo deficit
                       Title fight                 x1.20
                       Normal fight                x1.07
    4. Catchweight   Different weight class        x1.05
══════════════════════════════════════════════════════════════════════
"""


# ─────────────────────────────────────────────────────────────────────
# BONUS 1 — FINISH
#
# A finish (KO, submission, doctor stoppage) is more decisive than a
# decision, so it should move ratings more. A split decision means the
# judges were divided — the win was less convincing — so we dampen it.
# ─────────────────────────────────────────────────────────────────────


def FinishBonus(mode):
    """
    Returns a multiplier based on HOW the fight ended.

    x1.15 → KO/TKO, Submission, Doctor stoppage
             These are dominant finishes — the winner proved
             superiority beyond any doubt.

    x0.95 → Split Decision
             Judges were split — the win was real but contested.
             Slightly fewer elo points change hands.

    x1.00 → Unanimous / Majority Decision
             A clear win on the scorecards. Normal elo swing.

    PARAMETERS:
        mode : the method of victory string from the CSV

    RETURNS:
        float multiplier to apply to K
    """
    if mode in ("KO/TKO", "Submission", "TKO - Doctor's Stoppage"):
        return 1.15
    elif mode == "Decision - Split":
        return 0.95
    else:
        return 1.0


# ─────────────────────────────────────────────────────────────────────
# BONUS 2 — DOMINATION
#
# A fighter can win a unanimous decision narrowly (3 close rounds) or
# completely dominate (outstriking, outwrestling, knocking down).
# This bonus rewards truly dominant performances on the scorecards.
#
# Only applies to unanimous decisions — split/majority already signal
# the fight was close so domination doesn't make sense there.
#
# 5 ROUND FIGHTS — DOMINATED if ANY of:
#   A: kd_diff > 2                              (knockdown dominance)
#   B: 10-8 round AND sig_diff > 30%            (round dominance + volume)
#   C: sig_diff > 45%                           (pure striking dominance)
#   D: ctrl_diff > 50% AND td_ratio >= 2x       (grappling dominance)
#
# 3 ROUND FIGHTS — DOMINATED if ANY of:
#   F: kd_diff > 1                              (knockdown dominance)
#   G: 10-8 round                               (round dominance)
#   H: sig_diff > 35%                           (striking dominance)
#   I: ctrl_diff > 50% AND td_ratio >= 2x       (grappling dominance)
#
# NOTE: 10-8 round detection requires round-by-round data which is not
# available in UFC_merged.csv. round_10_8 is always False for now.
# ─────────────────────────────────────────────────────────────────────


def DominationBonus(fight, winner_id, r_id, mode, total_rounds):
    """
    Returns x1.1 if the winner dominated statistically, x1.0 otherwise.

    First assigns winner/loser stats from the fight row, then computes
    the key differentials (knockdowns, sig strikes, control, takedowns)
    and checks whether any domination condition is met.

    PARAMETERS:
        fight        : the full fight row from the DataFrame
        winner_id    : the ID of the fighter who won
        r_id         : the red corner fighter's ID (used to determine
                       which column prefix to use — r_ or b_)
        mode         : method of victory string
        total_rounds : 3 or 5, determines which criteria to apply

    RETURNS:
        1.1 if fight was dominated, 1.0 otherwise
    """
    # Domination only meaningful for clear unanimous wins
    if mode != "Decision - Unanimous":
        return 1.0

    try:
        # Assign winner/loser stats based on which corner won.
        # r_ prefix = red corner, b_ prefix = blue corner.
        if winner_id == r_id:
            w_kd = float(fight["r_kd"])
            l_kd = float(fight["b_kd"])
            w_sig = float(fight["r_sig_str_landed"])
            l_sig = float(fight["b_sig_str_landed"])
            w_ctrl = float(fight["r_ctrl"])
            l_ctrl = float(fight["b_ctrl"])
            w_td = float(fight["r_td_landed"])
            l_td = float(fight["b_td_landed"])
        else:
            w_kd = float(fight["b_kd"])
            l_kd = float(fight["r_kd"])
            w_sig = float(fight["b_sig_str_landed"])
            l_sig = float(fight["r_sig_str_landed"])
            w_ctrl = float(fight["b_ctrl"])
            l_ctrl = float(fight["r_ctrl"])
            w_td = float(fight["b_td_landed"])
            l_td = float(fight["r_td_landed"])

        # Raw knockdown advantage
        kd_diff = w_kd - l_kd

        # Significant strike percentage difference
        # e.g. winner lands 70, loser lands 30 → total=100, diff=40%
        total_sig = w_sig + l_sig
        sig_diff_pct = (w_sig - l_sig) / total_sig * 100 if total_sig > 0 else 0

        # Control time percentage difference (stored in seconds)
        total_ctrl = w_ctrl + l_ctrl
        ctrl_diff_pct = (w_ctrl - l_ctrl) / total_ctrl * 100 if total_ctrl > 0 else 0

        # Takedown ratio — how many more times did winner take down vs loser
        # float('inf') if loser had 0 takedowns (any winner TDs = infinite ratio)
        td_ratio = w_td / l_td if l_td > 0 else float("inf")

        # 10-8 round detection not available — would require round-by-round data
        round_10_8 = False

        if total_rounds == 5:
            A = kd_diff > 2  # clear knockdown advantage
            B = round_10_8 and sig_diff_pct > 30  # dominant round + volume
            C = sig_diff_pct > 45  # massive striking gap
            D = ctrl_diff_pct > 50 and td_ratio >= 2  # grappling dominance
            dominated = A or B or C or D

        else:  # 3 round fights — thresholds are slightly lower
            F = kd_diff > 1
            G = round_10_8
            H = sig_diff_pct > 35
            I = ctrl_diff_pct > 50 and td_ratio >= 2
            dominated = F or G or H or I

        return 1.1 if dominated else 1.0

    except:
        # If any stat is missing or can't be converted to float,
        # skip the bonus rather than crash the loop
        return 1.0


# ─────────────────────────────────────────────────────────────────────
# BONUS 3 — UNDERDOG
#
# When a lower-rated fighter beats a higher-rated one, the upset should
# be rewarded more than a normal win. The bigger the elo gap, the more
# impressive the upset. Title fights get an extra bump because upsets
# at championship level are historically more significant.
# ─────────────────────────────────────────────────────────────────────


def UnderdogBonus(r_elo, b_elo, winner_id, r_id, is_title_fight):
    """
    Returns a bonus multiplier when the lower-rated fighter wins.

    elo_diff = opponent's elo - winner's elo
    Positive value = winner was the underdog (had lower elo going in).

    >70 elo difference:
        Title fight  → x1.20  (major upset at championship level)
        Normal fight → x1.07  (meaningful upset)

    PARAMETERS:
        r_elo        : red corner's elo before the fight
        b_elo        : blue corner's elo before the fight
        winner_id    : ID of the winner
        r_id         : red corner's ID
        is_title_fight : 0 or 1 from the CSV

    RETURNS:
        float multiplier, 1.07 or 1.2 for upsets, 1.0 otherwise
    """
    # Calculate elo difference from the winner's perspective.
    # If winner is r, diff = b_elo - r_elo (positive = r was underdog).
    # If winner is b, diff = r_elo - b_elo (positive = b was underdog).
    if winner_id == r_id:
        elo_diff = b_elo - r_elo
    else:
        elo_diff = r_elo - b_elo

    if elo_diff > 70:
        return 1.2 if is_title_fight else 1.07
    return 1.0


# ─────────────────────────────────────────────────────────────────────
# BONUS 4 — CATCHWEIGHT / DIFFERENT WEIGHT CLASS
#
# Fighting outside your normal weight class (catchweight or open weight)
# adds an extra challenge. A small bonus rewards fighters who take
# these fights and win.
# ─────────────────────────────────────────────────────────────────────


def CatchweightBonus(fight):
    """
    Returns x1.05 if the fight was contested at a non-standard weight.

    Checks the division column for 'Catch' or 'Open' — these cover
    catchweight bouts and open weight (early UFC) contests.

    PARAMETERS:
        fight : the full fight row from the DataFrame

    RETURNS:
        1.05 for catchweight/open weight, 1.0 for normal division
    """
    if "Catch" in str(fight["division"]) or "Open" in str(fight["division"]):
        return 1.05
    return 1.0


# ─────────────────────────────────────────────────────────────────────
# COMBINED K ADJUSTMENT
#
# Takes every bonus and multiplies them all together into one final
# K value. This single number controls how much elo changes hands
# in the fight. All bonuses stack multiplicatively, not additively —
# so a KO (x1.15) + underdog (x1.07) = x1.23, not x1.22.
# ─────────────────────────────────────────────────────────────────────


def GetKAdj(fight, r_elo, b_elo, winner_id, r_id, mode, total_rounds):
    """
    Combine all bonuses into a single adjusted K factor.

    Base K = 40 (standard starting point for Elo systems).
    Each bonus is a multiplier on top of that base.

    PARAMETERS:
        fight        : full fight row from DataFrame
        r_elo        : red corner elo before fight
        b_elo        : blue corner elo before fight
        winner_id    : ID of the winner
        r_id         : red corner ID
        mode         : method of victory
        total_rounds : 3 or 5

    RETURNS:
        float — the adjusted K value to use in the Elo formula
    """
    K = 40  # base K factor — standard for most Elo implementations

    F_finish = FinishBonus(mode)
    F_domination = DominationBonus(fight, winner_id, r_id, mode, total_rounds)
    F_underdog = UnderdogBonus(r_elo, b_elo, winner_id, r_id, fight["title_fight"])
    F_catchweight = CatchweightBonus(fight)

    # Multiply all bonuses together — they stack on top of each other
    return K * F_finish * F_domination * F_underdog * F_catchweight
