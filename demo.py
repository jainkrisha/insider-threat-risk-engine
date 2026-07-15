"""
demo.py — Interactive demo of the FinSpark risk scoring engine.

Loads the saved model bundle, picks known malicious and normal users
from the test window, and shows the full score + explanation output.

Usage:
    python demo.py                         # shows top 5 malicious + 2 normal
    python demo.py --user CCA0046          # score a specific user's worst day
    python demo.py --user CCA0046 --all    # score ALL of a user's days

Run from the project root.
"""

import sys
import argparse
import textwrap
import pandas as pd

# Force UTF-8 output so box-drawing chars work on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.predict import RiskPredictor

# ── Colour helpers (works on most terminals; degrades gracefully if not) ─────
RESET  = "\033[0m"
BOLD   = "\033[1m"
RED    = "\033[91m"
YELLOW = "\033[93m"
GREEN  = "\033[92m"
CYAN   = "\033[96m"
DIM    = "\033[2m"

TIER_COLOUR = {
    "Critical": RED,
    "High":     YELLOW,
    "Medium":   CYAN,
    "Low":      GREEN,
}

def tier_badge(tier):
    c = TIER_COLOUR.get(tier, "")
    return f"{c}{BOLD}[{tier}]{RESET}"


def print_result(result, is_malicious=None):
    """Pretty-print a single score_row() result."""
    tier  = result["risk_tier"]
    score = result["risk_score"]
    user  = result["user"]

    label = ""
    if is_malicious is True:
        label = f"  {RED}● KNOWN MALICIOUS{RESET}"
    elif is_malicious is False:
        label = f"  {GREEN}● NORMAL USER{RESET}"

    print(f"\n{'─'*60}")
    print(f"  {BOLD}User:{RESET}        {user}{label}")
    print(f"  {BOLD}Risk Score:{RESET}  {BOLD}{score:.1f} / 100{RESET}")
    print(f"  {BOLD}Risk Tier:{RESET}   {tier_badge(tier)}")
    print(f"  {BOLD}Model:{RESET}       v{result['model_version']}")

    signals = result.get("top_signals", [])
    if signals:
        print(f"\n  {BOLD}Why flagged — top contributing signals:{RESET}")
        for s in signals:
            z = s["zscore"]
            bar_len = min(int(abs(z) * 2), 20)
            bar = "█" * bar_len
            z_colour = RED if abs(z) > 3 else YELLOW if abs(z) > 1.5 else CYAN
            print(f"    {z_colour}[{z:+.1f}σ]{RESET}  {s['label']}")
            print(f"           {DIM}{bar}{RESET}")
    else:
        print(f"\n  {DIM}  (no elevated signals — user appears normal on this day){RESET}")
    print()


def load_predictor():
    try:
        return RiskPredictor("models/model_v1.pkl")
    except FileNotFoundError:
        print("ERROR: models/model_v1.pkl not found. Run 'python src/train.py' first.")
        sys.exit(1)


def load_features():
    try:
        df = pd.read_csv("features.csv")
        df["day"] = pd.to_datetime(df["day"])
        return df
    except FileNotFoundError:
        print("ERROR: features.csv not found. Run 'python src/feature_engineering.py' first.")
        sys.exit(1)


def worst_day_for_user(features_df, user):
    """Return the row dict for the user's day with the highest off-hours + removable activity."""
    user_rows = features_df[features_df["user"] == user].copy()
    if user_rows.empty:
        return None
    # Rank by combined anomaly signals as a proxy for "worst day"
    user_rows["_signal"] = (
        user_rows["off_hours_events"] +
        user_rows["removable_file_events"] * 3 +
        user_rows["external_email_count"] +
        user_rows["suspicious_url_events"] * 2
    )
    best = user_rows.sort_values("_signal", ascending=False).iloc[0]
    row = best.drop("_signal").to_dict()
    row["day"] = str(best["day"].date())
    return row


def demo_default(predictor, features_df):
    """Show 5 known malicious users + 2 normal users from the test window."""

    # Load answer key to know which users are malicious
    try:
        answers = pd.read_csv("data/answers/insiders.csv")
        r42 = answers[answers["dataset"] == 4.2]
        malicious_set = set(r42["user"])
    except FileNotFoundError:
        malicious_set = set()

    # Spotlight users that tell a clear story for each scenario
    spotlight_malicious = ["CCA0046", "MAS0025", "JLM0364", "AJR0932", "MPM0220"]
    spotlight_normal    = ["BAL0044", "EIS0041"]

    print(f"\n{'='*60}")
    print(f"  {BOLD}FinSpark Risk Engine — Live Demo{RESET}")
    print(f"  Ensemble model: Isolation Forest (60%) + Random Forest (40%)")
    print(f"{'='*60}")

    print(f"\n{BOLD}== KNOWN MALICIOUS USERS (from CERT r4.2 answer key) =={RESET}")
    for uid in spotlight_malicious:
        row = worst_day_for_user(features_df, uid)
        if row is None:
            print(f"  {uid}: not found in features.csv")
            continue
        result = predictor.score_row(row)
        print_result(result, is_malicious=True)

    print(f"\n{BOLD}== NORMAL USERS (should score LOW / MEDIUM) =={RESET}")
    for uid in spotlight_normal:
        row = worst_day_for_user(features_df, uid)
        if row is None:
            print(f"  {uid}: not found in features.csv")
            continue
        result = predictor.score_row(row)
        print_result(result, is_malicious=False)


def demo_user(predictor, features_df, user, all_days=False):
    """Score a specific user — either their worst day or all days."""
    malicious_set = set()
    try:
        answers = pd.read_csv("data/answers/insiders.csv")
        r42 = answers[answers["dataset"] == 4.2]
        malicious_set = set(r42["user"])
    except FileNotFoundError:
        pass

    is_malicious = user in malicious_set
    user_rows = features_df[features_df["user"] == user]

    if user_rows.empty:
        print(f"User '{user}' not found in features.csv.")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  {BOLD}FinSpark — Scoring user: {user}{RESET}")
    if is_malicious:
        print(f"  {RED}{BOLD}This user is in the CERT r4.2 malicious answer key.{RESET}")
    print(f"{'='*60}")

    if all_days:
        rows = user_rows.sort_values("day")
        print(f"  Scoring all {len(rows)} days...\n")
        for _, r in rows.iterrows():
            row = r.to_dict()
            row["day"] = str(r["day"].date())
            result = predictor.score_row(row)
            print_result(result, is_malicious=is_malicious)
    else:
        row = worst_day_for_user(features_df, user)
        print(f"  Showing worst day (highest anomaly signals).\n")
        result = predictor.score_row(row)
        print_result(result, is_malicious=is_malicious)


def main():
    parser = argparse.ArgumentParser(
        description="FinSpark risk engine demo.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
        Examples:
          python demo.py                        # default demo — 5 malicious + 2 normal
          python demo.py --user AJR0932         # score a specific user's worst day
          python demo.py --user AJR0932 --all   # score all of AJR0932's days
        """),
    )
    parser.add_argument("--user", help="Score a specific user ID")
    parser.add_argument("--all",  action="store_true",
                        help="Score ALL days for the given user (requires --user)")
    args = parser.parse_args()

    predictor    = load_predictor()
    features_df  = load_features()

    if args.user:
        demo_user(predictor, features_df, args.user.upper(), all_days=args.all)
    else:
        demo_default(predictor, features_df)


if __name__ == "__main__":
    main()
