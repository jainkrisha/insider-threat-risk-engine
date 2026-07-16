"""
Trains the Isolation Forest on a TIME-BASED split of the data and evaluates
on the held-out later window. This replaces the old model.py, which trained
and "evaluated" on the exact same rows -- those numbers were optimistic
because Isolation Forest tends to score training points it memorized as
less anomalous, and because the personal z-scores were computed on full
history (see baseline_features.py for that fix).

What changed vs. model.py:
  - features.csv is split by `day` into train (first ~TRAIN_FRACTION of the
    date range) and test (the rest) BEFORE anything else happens.
  - Personal z-score baselines are fit on train only, then applied to both
    train and test (baseline_features.py).
  - The scaler is fit on train only, then used to transform test.
  - The Isolation Forest is fit on train only.
  - Evaluation (precision/recall/F1) runs on the held-out test window only.
    This number is lower than what model.py reported -- that's expected,
    and it's the real one.
  - Model + scaler + baseline stats + feature column list + risk tier
    cutoffs are saved together as one versioned artifact via joblib, so
    predict.py can load a single consistent bundle.

Usage:
    python src/train.py
"""

import os
import json
import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.preprocessing import StandardScaler

from config import (
    FEATURES_RAW_PATH, ANSWERS_PATH, MODEL_DIR,
    CONTAMINATION, RANDOM_STATE, N_ESTIMATORS, TRAIN_FRACTION,
    RISK_TIER_PERCENTILES, get_feature_columns,
    ENSEMBLE_WEIGHT_IF, ENSEMBLE_WEIGHT_SUPERVISED,
    HIGH_RISK_DAY_THRESHOLD, AGG_WEIGHT_MAX, AGG_WEIGHT_MEAN, AGG_WEIGHT_HIGHDAYS,
)
from baseline_features import fit_baseline_stats, apply_baseline_stats

MODEL_VERSION = "v1"


def load_features():
    df = pd.read_csv(FEATURES_RAW_PATH)
    df["day"] = pd.to_datetime(df["day"])
    return df


def load_malicious_users():
    answers = pd.read_csv(ANSWERS_PATH)
    r42 = answers[answers["dataset"] == 4.2]
    return set(r42["user"])


def time_split(df, train_fraction=TRAIN_FRACTION):
    """
    Split by DATE, not by row -- everything before the cutoff is train,
    everything on/after is test. This mimics the real deployment setting:
    you only ever have past data to train on.
    """
    min_day, max_day = df["day"].min(), df["day"].max()
    span = (max_day - min_day)
    cutoff = min_day + span * train_fraction

    train_df = df[df["day"] < cutoff].copy()
    test_df = df[df["day"] >= cutoff].copy()

    print(f"Date range: {min_day.date()} to {max_day.date()} ({span.days} days)")
    print(f"Train: {min_day.date()} to {cutoff.date()} ({len(train_df)} rows)")
    print(f"Test:  {cutoff.date()} to {max_day.date()} ({len(test_df)} rows)")

    return train_df, test_df, cutoff


def fit_and_score(train_df, test_df):
    # 1. Baseline z-scores: fit on train, apply to both (no leakage)
    baseline_stats = fit_baseline_stats(train_df)
    train_df = apply_baseline_stats(train_df, baseline_stats)
    test_df = apply_baseline_stats(test_df, baseline_stats)

    # 2. Feature columns: one shared definition
    feature_cols = get_feature_columns(train_df)
    print(f"Using {len(feature_cols)} feature columns: {feature_cols}")

    X_train = train_df[feature_cols].astype(float)
    X_test = test_df[feature_cols].astype(float)

    # 3. Scaler: fit on train only
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # 4. Model: fit on train only
    model = IsolationForest(
        n_estimators=N_ESTIMATORS,
        contamination=CONTAMINATION,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    model.fit(X_train_scaled)

    # 5. Score TEST (held-out) data -- this is the honest number
    raw_scores = -model.decision_function(X_test_scaled)
    # Min/max from TEST scores for display scaling. Note: for live scoring
    # in predict.py we can't know future min/max, so predict.py clips
    # against the train-time observed range instead (see predict.py).
    train_raw_scores = -model.decision_function(X_train_scaled)
    score_min, score_max = train_raw_scores.min(), train_raw_scores.max()

    def to_0_100(raw):
        scaled = 100 * (raw - score_min) / (score_max - score_min)
        return np.clip(scaled, 0, 100)

    test_df = test_df.copy()
    test_df["risk_score"] = to_0_100(raw_scores)

    train_df = train_df.copy()
    train_df["risk_score"] = to_0_100(train_raw_scores)

    return model, scaler, baseline_stats, feature_cols, train_df, test_df, (score_min, score_max)


def fit_supervised(train_df, malicious_users, feature_cols, scaler):
    """
    Train a Random Forest classifier on the same scaled features used by the
    Isolation Forest, using user-level labels from the CERT answer key.

    Using class_weight='balanced' compensates for the severe imbalance
    (~5% malicious rows). max_depth cap prevents memorising individual users.

    Returns the fitted classifier, or None if no malicious users exist in the
    training window (pipeline degrades gracefully to pure IF scoring).
    """
    y = train_df["user"].isin(malicious_users).astype(int)

    if y.sum() == 0:
        print("  WARNING: no malicious users in train window -- supervised model skipped.")
        return None

    X = train_df[feature_cols].astype(float)
    X_scaled = scaler.transform(X)          # reuse already-fit scaler, don't refit

    clf = RandomForestClassifier(
        n_estimators=300,
        class_weight="balanced",             # compensates for class imbalance
        max_depth=8,                         # prevents memorising individual users
        min_samples_leaf=5,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    clf.fit(X_scaled, y)

    n_pos = int(y.sum())
    n_total = len(y)
    print(f"  RF trained on {n_total} rows: {n_pos} malicious ({100*n_pos/n_total:.1f}%) "
          f"| {n_total - n_pos} normal")
    return clf


def apply_ensemble_blend(df, clf, scaler, feature_cols):
    """
    Blend the Isolation Forest risk_score (already in df['risk_score']) with
    the supervised Random Forest probability score.

    If clf is None (no supervised model -- old bundle or no labels in train
    window), returns df unchanged so the rest of the pipeline still works.
    """
    if clf is None:
        return df

    df = df.copy()
    X = df[feature_cols].astype(float)
    X_scaled = scaler.transform(X)          # same scaler, no refit

    # predict_proba[:, 1] = P(malicious) in [0,1]; scale to 0-100
    sup_scores = clf.predict_proba(X_scaled)[:, 1] * 100

    df["if_score"]         = df["risk_score"]   # preserve raw IF score for reference
    df["supervised_score"] = sup_scores
    df["risk_score"] = np.clip(
        ENSEMBLE_WEIGHT_IF * df["if_score"] + ENSEMBLE_WEIGHT_SUPERVISED * sup_scores,
        0, 100,
    )
    return df


def aggregate_to_user_level(scored_df):
    """
    Aggregate per-user-day scores to a single per-user risk summary.

    composite_score = 0.5*max + 0.3*mean + 0.2*(high_risk_day_rate*100)

    This rewards BOTH single dramatic spike days (Scenario 3: sysadmin
    keylogger) AND sustained moderate-risk behaviour (Scenario 2: slow
    data exfiltration), which max_risk_score alone misses.
    """
    g = scored_df.groupby("user")
    user_risk = g.agg(
        max_risk_score=("risk_score", "max"),
        mean_risk_score=("risk_score", "mean"),
        num_days_observed=("day", "count"),
    ).reset_index()

    # Count days above the high-risk threshold
    high_days = scored_df[scored_df["risk_score"] > HIGH_RISK_DAY_THRESHOLD]
    day_counts = high_days.groupby("user").size().rename("high_risk_day_count")
    user_risk = user_risk.merge(day_counts, on="user", how="left")
    user_risk["high_risk_day_count"] = user_risk["high_risk_day_count"].fillna(0)

    # Weighted composite score
    high_risk_rate = (
        user_risk["high_risk_day_count"] /
        user_risk["num_days_observed"].clip(lower=1)
    )
    user_risk["composite_score"] = (
        AGG_WEIGHT_MAX      * user_risk["max_risk_score"]  +
        AGG_WEIGHT_MEAN     * user_risk["mean_risk_score"] +
        AGG_WEIGHT_HIGHDAYS * high_risk_rate * 100
    ).clip(0, 100)

    return user_risk.sort_values("composite_score", ascending=False)


def evaluate(user_risk, malicious_users, top_n_list=(50, 70, 100, 150)):
    """
    Evaluate ranking quality. Sorts by composite_score when available
    (the new default), falls back to max_risk_score for old result files.
    """
    user_risk = user_risk.copy()
    user_risk["is_malicious"] = user_risk["user"].isin(malicious_users)

    sort_col = "composite_score" if "composite_score" in user_risk.columns else "max_risk_score"
    user_risk = user_risk.sort_values(sort_col, ascending=False)

    print(f"  Ranking by: {sort_col}")
    print(f"\nMalicious users in answer key: {len(malicious_users)}")
    print(f"Users scored in TEST window: {len(user_risk)}")
    print(f"Malicious users present in TEST window: {int(user_risk['is_malicious'].sum())}\n")

    print("=== Evaluation on held-out TEST window ===")
    for n in top_n_list:
        if n > len(user_risk):
            continue
        top_n = user_risk.head(n)
        tp = int(top_n["is_malicious"].sum())
        precision = tp / n
        recall = tp / len(malicious_users)
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        print(f"Top {n}: {tp}/{len(malicious_users)} caught | "
              f"precision={precision:.3f} | recall={recall:.3f} | f1={f1:.3f}")

    return user_risk


def compute_risk_tier_cutoffs(train_df):
    """
    Percentile cutoffs computed on TRAIN scores (the distribution the model
    was fit to). Saved with the model so predict.py applies a stable,
    versioned set of tier boundaries rather than recomputing percentiles
    on whatever live batch happens to come in.
    """
    scores = train_df["risk_score"].values
    return {
        name: float(np.percentile(scores, pct * 100))
        for name, pct in RISK_TIER_PERCENTILES.items()
    }


def main():
    os.makedirs(MODEL_DIR, exist_ok=True)

    print("Loading features...")
    features = load_features()

    print("Loading malicious user list from answer key...")
    malicious_users = load_malicious_users()

    print("\nSplitting by time...")
    train_df, test_df, cutoff = time_split(features)

    print("\nFitting baseline stats, scaler, and Isolation Forest on TRAIN only...")
    (model, scaler, baseline_stats, feature_cols,
     train_scored, test_scored, score_range) = fit_and_score(train_df, test_df)

    print("\nFitting supervised Random Forest on TRAIN only...")
    clf = fit_supervised(train_scored, malicious_users, feature_cols, scaler)

    print("\nBlending Isolation Forest + supervised scores...")
    train_scored = apply_ensemble_blend(train_scored, clf, scaler, feature_cols)
    test_scored  = apply_ensemble_blend(test_scored,  clf, scaler, feature_cols)

    # Tier cutoffs calibrated to the BLENDED train distribution
    tier_cutoffs = compute_risk_tier_cutoffs(train_scored)
    print(f"\nRisk tier cutoffs (blended train distribution): {tier_cutoffs}")

    print("\nAggregating TEST window to per-user risk scores (composite)...")
    user_risk = aggregate_to_user_level(test_scored)

    print("Evaluating on held-out TEST window (the real number)...")
    user_risk = evaluate(user_risk, malicious_users)

    # ---- Save everything predict.py needs, as one versioned bundle ----
    bundle_path = os.path.join(MODEL_DIR, f"model_{MODEL_VERSION}.pkl")
    joblib.dump({
        "model":            model,
        "supervised_model": clf,          # None if no malicious users in train window
        "scaler":           scaler,
        "baseline_stats":   baseline_stats,
        "feature_cols":     feature_cols,
        "tier_cutoffs":     tier_cutoffs,
        "score_range":      score_range,
        "train_cutoff_date": str(cutoff.date()),
        "version":          MODEL_VERSION,
    }, bundle_path)
    print(f"\nSaved model bundle to {bundle_path}")

    # Human-readable metadata
    meta_path = os.path.join(MODEL_DIR, f"model_{MODEL_VERSION}_meta.json")
    with open(meta_path, "w") as f:
        json.dump({
            "version":           MODEL_VERSION,
            "train_cutoff_date": str(cutoff.date()),
            "feature_cols":      feature_cols,
            "tier_cutoffs":      tier_cutoffs,
            "ensemble_weights":  {
                "isolation_forest": ENSEMBLE_WEIGHT_IF,
                "random_forest":    ENSEMBLE_WEIGHT_SUPERVISED,
            },
            "aggregation_weights": {
                "max":           AGG_WEIGHT_MAX,
                "mean":          AGG_WEIGHT_MEAN,
                "high_risk_days": AGG_WEIGHT_HIGHDAYS,
            },
        }, f, indent=2)
    print(f"Saved metadata to {meta_path}")

    user_risk.to_csv("risk_scores_test.csv", index=False)
    print("\nSaved held-out test-window risk scores to risk_scores_test.csv")
    print("\nTop 20 riskiest users (TEST window, ranked by composite_score):")
    print(user_risk.head(20).to_string(index=False))


if __name__ == "__main__":
    main()
