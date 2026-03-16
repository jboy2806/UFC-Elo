"""
elo.py
══════════════════════════════════════════════════════════════════════
Core Elo calculation logic.

Contains:
  1. ExpA()                — expected score formula (probability of winning)
  2. _calc_decay()         — internal: computes decayed elo for a given gap
  3. apply_decay()         — applies inactivity decay before a fight
  4. apply_final_decay()   — applies decay to ALL fighters after the loop,
                             using today's date as the reference point
  5. EloChange()           — calculates new ratings for both fighters
  6. run_elo_loop()        — iterates through every fight in the dataset

WHY TWO DECAY FUNCTIONS:
    apply_decay() fires inside the loop, just before a fighter's next
    fight. This handles cases like GSP retiring and coming back — his
    rating decays between his last fight and his comeback.

    apply_final_decay() fires AFTER the loop using today's date. This
    is what catches retired fighters like Khabib who have no more fights
    in the dataset — without this pass, the loop never touches them again
    and their rating stays frozen at retirement.

EXPONENTIAL DECAY FORMULA:
    new_elo = DECAY_FLOOR + (old_elo - DECAY_FLOOR) * DECAY_RATE ^ extra_years

    extra_years = years of inactivity beyond DECAY_GRACE_MONTHS
    DECAY_RATE  = fraction of elo-above-floor kept per year (0.80 = -20%/yr)

    Example — fighter at 1800, floor 1500, rate 0.80:
        1 yr beyond grace → surplus 300 * 0.80^1.0 = 240 → elo 1740
        2 yrs             → surplus 300 * 0.80^2.0 = 192 → elo 1692
        3 yrs             → surplus 300 * 0.80^3.0 = 154 → elo 1654
        5 yrs             → surplus 300 * 0.80^5.0 =  98 → elo 1598
══════════════════════════════════════════════════════════════════════
"""

import pandas as pd
from datetime import date as date_type
from bonuses import GetKAdj


# ─────────────────────────────────────────────────────────────────────
# DECAY SETTINGS — edit these three constants to tune the penalty
#
# DECAY_GRACE_MONTHS : inactivity allowed before any penalty kicks in
# DECAY_RATE         : fraction of elo surplus kept per extra year
#                      0.80 → gentle,  0.70 → moderate,  0.60 → harsh
# DECAY_FLOOR        : elo can never decay below this value
# ─────────────────────────────────────────────────────────────────────

DECAY_GRACE_MONTHS = 12
DECAY_RATE         = 0.80
DECAY_FLOOR        = 1500


# ─────────────────────────────────────────────────────────────────────
# CORE ELO FORMULA
# ─────────────────────────────────────────────────────────────────────

def ExpA(eloA, eloB):
    """
    Calculate the expected win probability for fighter A.

    FORMULA:  E_A = 1 / (1 + 10 ^ ((eloB - eloA) / 300))

    Returns a float between 0 and 1:
        0.5  = even match
        0.75 = A heavily favored
        0.25 = A is the underdog

    WHY (eloB - eloA) not (eloA - eloB):
        When A is stronger, (eloB - eloA) is negative, making the
        exponent negative, making 10^x < 1, making the denominator
        < 2, giving E_A > 0.5. Correct. Reversed sign gives wrong answer.

    WHY 300 scaling constant:
        Lower than chess standard (400) to make ratings more sensitive.
        MMA fighters have short careers — every rating difference needs
        to carry more weight.
    """
    return 1 / (1 + 10 ** ((eloB - eloA) / 300))


# ─────────────────────────────────────────────────────────────────────
# DECAY HELPERS
# ─────────────────────────────────────────────────────────────────────

def _calc_decayed_elo(current_elo, months_inactive):
    """
    Internal helper: compute what a fighter's elo becomes after
    a given number of months of inactivity.

    Only the elo ABOVE the floor decays — the floor itself is an anchor.
    The decay is exponential: each additional year costs more than the last.

    FORMULA:
        extra_years      = (months_inactive - DECAY_GRACE_MONTHS) / 12
        decayed_surplus  = (current_elo - DECAY_FLOOR) * DECAY_RATE ^ extra_years
        new_elo          = DECAY_FLOOR + decayed_surplus

    If the fighter is within the grace period, returns current_elo unchanged.
    If current_elo is already at or below the floor, returns current_elo unchanged.

    PARAMETERS:
        current_elo     : the fighter's elo before applying decay
        months_inactive : total months since their last fight

    RETURNS:
        float — the new decayed elo value
    """
    # Within grace period — no penalty
    if months_inactive <= DECAY_GRACE_MONTHS:
        return current_elo

    # Already at or below the floor — nothing to decay
    surplus = current_elo - DECAY_FLOOR
    if surplus <= 0:
        return current_elo

    # Extra years beyond the grace window
    # e.g. 30 months inactive, 12 month grace → 18 extra months → 1.5 years
    extra_years = (months_inactive - DECAY_GRACE_MONTHS) / 12

    # Exponential decay applied to the surplus only
    # The floor is unaffected — it acts as a hard anchor
    decayed_surplus = surplus * (DECAY_RATE ** extra_years)

    return DECAY_FLOOR + decayed_surplus


def apply_decay(fighter_id, fight_date, elo_ratings):
    """
    Apply inactivity decay to a fighter JUST BEFORE their next fight.

    This handles comebacks within the dataset (e.g. GSP retiring 2013,
    returning 2017). The decay is calculated from their last fight date
    to the date of the upcoming fight.

    WHY BEFORE THE FIGHT:
        The decay represents uncertainty about a returning fighter's
        current level. It should be baked into their rating before we
        see how they perform — not after.

    PARAMETERS:
        fighter_id : the fighter's ID string
        fight_date : date of the fight they're about to enter (Timestamp)
        elo_ratings: the full elo dictionary (modified in place)
    """
    last_date = elo_ratings[fighter_id]["last_fight_date"]

    # Debut — no previous fight to measure inactivity from
    if last_date is None:
        return

    months_inactive = (fight_date - last_date).days / 30.44
    old_elo = elo_ratings[fighter_id]["elo"]
    elo_ratings[fighter_id]["elo"] = _calc_decayed_elo(old_elo, months_inactive)


def apply_final_decay(elo_ratings, reference_date=None):
    """
    Apply inactivity decay to ALL fighters after the loop finishes,
    using today's date (or a custom reference date) as the endpoint.

    WHY THIS IS NECESSARY:
        apply_decay() only fires when a fighter is ABOUT TO FIGHT.
        Retired fighters (Khabib, GSP post-2017, etc.) have no more
        fights in the dataset, so the loop never touches them again.
        Without this pass, every retired fighter's rating stays frozen
        at the moment they last fought — potentially years ago.

        This function is the fix: after all 8570 fights are processed,
        we do one final sweep asking "how long ago did every fighter
        last compete?" and decay their rating accordingly.

    HOW IT WORKS:
        For each fighter, we measure the gap between their last fight
        date and `reference_date` (today by default). Then we apply
        the same exponential formula used inside the loop.

    EXAMPLE:
        Khabib last fought Oct 2021. Today is March 2026.
        That's ~53 months → 41 extra months beyond 12-month grace → 3.4 extra years.
        Starting elo ~1800, surplus = 300, decay = 300 * 0.80^3.4 ≈ 140
        Final elo ≈ 1500 + 140 = 1640

    PARAMETERS:
        elo_ratings    : the fully computed elo dictionary from run_elo_loop()
        reference_date : the "today" date to measure inactivity against.
                         Defaults to the actual current date.
                         Pass a custom pd.Timestamp to pin to a specific date.

    RETURNS:
        Nothing — modifies elo_ratings in place
    """
    if reference_date is None:
        reference_date = pd.Timestamp(date_type.today())

    decayed_count = 0

    for fighter_id, data in elo_ratings.items():
        last_date = data["last_fight_date"]

        # Never fought in our dataset — skip
        if last_date is None:
            continue

        months_inactive = (reference_date - last_date).days / 30.44

        # Only process fighters who are past the grace window
        if months_inactive <= DECAY_GRACE_MONTHS:
            continue

        old_elo = data["elo"]
        new_elo = _calc_decayed_elo(old_elo, months_inactive)

        if new_elo < old_elo - 0.01:   # only update if actually changed
            data["elo"] = new_elo
            decayed_count += 1

    print(f"  → Final decay applied to {decayed_count} inactive fighters (ref: {str(reference_date)[:10]})")


# ─────────────────────────────────────────────────────────────────────
# ELO CHANGE CALCULATION
# ─────────────────────────────────────────────────────────────────────

def EloChange(eloA, eloB, nfightsA, nfightsB, mode, w_id, A_id, fight):
    """
    Calculate the new elo ratings for both fighters after one fight.

    THE CORE FORMULA:
        new_elo = old_elo + K_adj * (actual_score - expected_score)

        The (actual - expected) term is the "surprise factor":
            Win expected to win   → small positive → small gain
            Win expected to lose  → large positive → big gain
            Loss expected to lose → small negative → small drop
            Loss expected to win  → large negative → big drop

    SPECIAL CASES handled before the main formula:
        DQ          → loser loses flat 20, winner unchanged
        Draw        → both score 0.5, elo nudges toward equilibrium
        NC/Overturn → fight never happened, ratings unchanged

    PARAMETERS:
        eloA    : red corner elo (AFTER decay has been applied)
        eloB    : blue corner elo (AFTER decay has been applied)
        nfightsA: number of fights red corner has had
        nfightsB: number of fights blue corner has had
        mode    : method of victory string from the CSV
        w_id    : winner's fighter ID (NaN for draw/NC)
        A_id    : red corner's fighter ID
        fight   : full fight row (needed for bonus multipliers)

    RETURNS:
        (new_eloA, new_eloB)
    """

    # ── Disqualification ──────────────────────────────────────────────
    # The DQ'd fighter loses a flat penalty; the winner earns nothing
    # because the win came from their opponent's violation, not skill.
    if mode == "DQ":
        if w_id == A_id:
            return eloA, eloB - 20
        else:
            return eloA - 20, eloB

    # ── No official winner ────────────────────────────────────────────
    if pd.isna(w_id):
        if 'Draw' in str(mode):
            scoreA, scoreB = 0.5, 0.5  # split the difference
        else:
            return eloA, eloB          # NC or overturned — nothing changes

    # ── Normal fight ──────────────────────────────────────────────────
    elif w_id == A_id:
        scoreA, scoreB = 1.0, 0.0
    else:
        scoreA, scoreB = 0.0, 1.0

    # Adjusted K incorporates finish/domination/underdog/catchweight bonuses
    total_rounds = fight['total_rounds'] if not pd.isna(fight['total_rounds']) else 3
    K_adj = GetKAdj(fight, eloA, eloB, w_id, A_id, mode, total_rounds)

    expA = ExpA(eloA, eloB)
    expB = 1 - expA   # always sums to 1.0

    new_eloA = eloA + K_adj * (scoreA - expA)
    new_eloB = eloB + K_adj * (scoreB - expB)

    return new_eloA, new_eloB


# ─────────────────────────────────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────────────────────────────────

def run_elo_loop(df, elo_ratings):
    """
    Process every fight chronologically and build all elo ratings.

    ORDER OF OPERATIONS PER FIGHT:
        1. Apply inactivity decay to both fighters (based on their last fight)
        2. Read their current elo (now includes any decay)
        3. Calculate new ratings via EloChange()
        4. Write new ratings back to the dictionary
        5. Update each fighter's last_fight_date to this fight's date
        6. Increment fight counters
        7. Append a history snapshot for career tracking

    After the loop, call apply_final_decay() to catch retired fighters
    who have no more fights in the dataset (Khabib, GSP, etc.).

    PARAMETERS:
        df          : sorted DataFrame of all fights (oldest first)
        elo_ratings : initialized dictionary from initialize_elo()

    RETURNS:
        elo_ratings : fully populated with all fight results
    """
    total = len(df)

    for idx, fight in df.iterrows():
        r_id      = fight["r_id"]
        b_id      = fight["b_id"]
        winner_id = fight["winner_id"]
        method    = fight["method"]
        date      = fight["date"]

        # Step 1 — decay before reading elo so the decay feeds into
        # the fight calculation (returning fighters are treated cautiously)
        apply_decay(r_id, date, elo_ratings)
        apply_decay(b_id, date, elo_ratings)

        # Step 2 — read current state (post-decay)
        r_elo    = elo_ratings[r_id]["elo"]
        b_elo    = elo_ratings[b_id]["elo"]
        r_fights = elo_ratings[r_id]["fights"]
        b_fights = elo_ratings[b_id]["fights"]

        # Step 3 — calculate new ratings
        new_r_elo, new_b_elo = EloChange(
            r_elo, b_elo, r_fights, b_fights, method, winner_id, r_id, fight
        )

        # Step 4 — write back
        elo_ratings[r_id]["elo"] = new_r_elo
        elo_ratings[b_id]["elo"] = new_b_elo

        # Step 5 — record when they last fought (used by next decay check)
        elo_ratings[r_id]["last_fight_date"] = date
        elo_ratings[b_id]["last_fight_date"] = date

        # Step 6 — increment counters
        elo_ratings[r_id]["fights"] += 1
        elo_ratings[b_id]["fights"] += 1

        # Step 7 — save career history snapshot
        # elo_before = post-decay, pre-fight elo (what the fight was calculated from)
        # elo        = post-fight elo (the result)
        # Storing both lets the display show fight gain/loss separately from decay.
        elo_ratings[r_id]["history"].append({"date": date, "elo_before": r_elo, "elo": new_r_elo})
        elo_ratings[b_id]["history"].append({"date": date, "elo_before": b_elo, "elo": new_b_elo})

        if idx % 1000 == 0:
            print(f"  → Processed {idx:>5} / {total} fights...")

    print(f"  → Done! All {total} fights processed.")
    return elo_ratings
