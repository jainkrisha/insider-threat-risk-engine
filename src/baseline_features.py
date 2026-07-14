"""
Personal (per-user) baseline z-score features -- leakage-safe version.

The old add_baseline_features.py computed each user's mean/std over their
FULL history (all 17 months), then wrote one features_baseline.csv. That's
fine for a single offline batch run, but it silently leaks future data into
"past" rows once you evaluate with a time split: a user's Jan score would be
normalized using their May behavior too.

This module separates fitting stats from applying them:

    stats = fit_baseline_stats(train_df)      # fit on TRAIN rows only
    train_df = apply_baseline_stats(train_df, stats)
    test_df  = apply_baseline_stats(test_df, stats)   # same stats, no peeking

train.py uses both functions and saves `stats` with the model, so predict.py
can apply the exact same baseline to new live rows later.

Usage (still works as a standalone batch step, same as before):
    python src/baseline_features.py
"""

import pandas as pd
from config import BASELINE_COLS, FEATURES_RAW_PATH, FEATURES_BASELINE_PATH


def fit_baseline_stats(df):
    """
    Compute per-user mean/std for each BASELINE_COLS, using ONLY the rows
    in `df` (this should be your training window, not the full dataset).

    Returns a dict: {col: DataFrame(index=user, columns=[mean, std])}
    """
    stats = {}
    existing_cols = [c for c in BASELINE_COLS if c in df.columns]

    for col in existing_cols:
        grouped = df.groupby("user")[col].agg(["mean", "std"])
        grouped["std"] = grouped["std"].replace(0, 1).fillna(1)
        stats[col] = grouped

    return stats


def apply_baseline_stats(df, stats):
    """
    Apply previously-fit per-user stats to `df` (train, test, or brand new
    live rows -- doesn't matter, same function every time).

    Users not present in `stats` (e.g. a new hire with no training history)
    fall back to the GLOBAL mean/std across all users in `stats`, so predict.py
    never crashes on an unseen user -- it just treats them as "average" until
    they build up their own history.
    """
    df = df.copy()

    for col, grouped in stats.items():
        if col not in df.columns:
            continue

        global_mean = grouped["mean"].mean()
        global_std = grouped["std"].mean() if grouped["std"].mean() != 0 else 1

        user_mean = df["user"].map(grouped["mean"]).fillna(global_mean)
        user_std = df["user"].map(grouped["std"]).fillna(global_std)

        df[f"{col}_personal_zscore"] = (df[col] - user_mean) / user_std

    return df


def main():
    """Standalone full-history run, matching the old script's behavior --
    useful for exploration, but train.py does its own leakage-safe version
    for the actual model."""
    features = pd.read_csv(FEATURES_RAW_PATH)
    stats = fit_baseline_stats(features)
    features = apply_baseline_stats(features, stats)
    features.to_csv(FEATURES_BASELINE_PATH, index=False)
    print(f"Saved {len(features)} rows with personal z-score features to {FEATURES_BASELINE_PATH}")
    print(f"New columns: {[c for c in features.columns if 'zscore' in c]}")


if __name__ == "__main__":
    main()
