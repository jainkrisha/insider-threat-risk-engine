"""
Inference-only scoring. Loads a saved model bundle (model + scaler +
baseline stats + feature columns + tier cutoffs, all produced by train.py)
and scores new user-day feature rows. NEVER fits anything -- this is safe
to call on every live request.

Usage as a library (what your backend should do):

    from predict import RiskPredictor
    predictor = RiskPredictor("models/model_v1.pkl")
    result = predictor.score_row({
        "user": "ABC1234", "day": "2011-03-14",
        "logon_count": 5, "off_hours_events": 2, ...
    })
    # result = {
    #   "user": "ABC1234",
    #   "risk_score": 63.2,
    #   "risk_tier": "High",
    #   "top_signals": [
    #     {"feature": "removable_file_events", "zscore": 6.1,
    #      "raw_value": 18.0, "user_baseline": 0.4,
    #      "label": "18 removable media file events (your normal: ~0.4)"},
    #     ...
    #   ]
    # }

Usage from the command line (scores a CSV of new user-day rows):

    python src/predict.py --input new_features.csv --output scored.csv
"""

import argparse
import numpy as np
import pandas as pd
import joblib

from config import BASELINE_COLS, score_to_tier, ENSEMBLE_WEIGHT_IF, ENSEMBLE_WEIGHT_SUPERVISED
from baseline_features import apply_baseline_stats


# ---------------------------------------------------------------------------
# Human-readable labels for every feature the model uses.
# Keyed by the RAW feature name (before "_personal_zscore" suffix).
# Used by _get_top_signals() to build the explanation string.
# ---------------------------------------------------------------------------
FEATURE_LABELS = {
    "logon_count":           "logon events",
    "off_hours_events":      "off-hours logins",
    "unique_pcs":            "unique PCs accessed",
    "device_connects":       "USB/device connections",
    "device_off_hours":      "off-hours device events",
    "file_events":           "file access events",
    "removable_file_events": "removable media file events",
    "email_count":           "emails sent",
    "external_email_count":  "external emails sent",
    "suspicious_url_events": "suspicious URL visits",
}


class RiskPredictor:
    def __init__(self, bundle_path):
        bundle = joblib.load(bundle_path)
        self.model            = bundle["model"]
        self.supervised_model = bundle.get("supervised_model")  # None for old bundles
        self.scaler           = bundle["scaler"]
        self.baseline_stats   = bundle["baseline_stats"]
        self.feature_cols     = bundle["feature_cols"]
        self.tier_cutoffs     = bundle["tier_cutoffs"]
        self.score_min, self.score_max = bundle["score_range"]
        self.version          = bundle["version"]

    # -----------------------------------------------------------------
    # Input validation / repair
    # -----------------------------------------------------------------
    def _validate_and_fill(self, df):
        """
        Guarantees every column the model needs is present and numeric,
        the same guarantee feature_engineering.py gives the batch pipeline
        (fillna(0)). Live rows won't always have every column -- e.g. a
        user with no email activity that day simply won't have email
        columns in the incoming payload at all.
        """
        df = df.copy()

        if "user" not in df.columns:
            raise ValueError("Input rows must include a 'user' column.")

        # Any raw column the baseline z-scores or core features need,
        # but that's missing from this batch entirely -> add as 0.
        required_raw_cols = set(BASELINE_COLS) | {
            "off_hours_events", "device_off_hours", "removable_file_events",
            "unique_pcs", "external_email_count", "suspicious_url_events",
        }
        for col in required_raw_cols:
            if col not in df.columns:
                df[col] = 0

        # Fill any missing/NaN values in numeric columns with 0, matching
        # the batch feature_engineering.py behavior.
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        df[numeric_cols] = df[numeric_cols].fillna(0)

        # Any non-numeric weirdness (e.g. a stray string in a numeric field)
        # gets coerced; anything that can't be coerced becomes 0 rather than
        # crashing the whole batch.
        for col in required_raw_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        return df

    # -----------------------------------------------------------------
    # Explainability
    # -----------------------------------------------------------------
    def _get_top_signals(self, row, user, top_n=4):
        """
        Returns the top_n features that most explain the risk score for a
        single user-day row (a pandas Series after baseline stats are applied).

        Strategy: use the personal z-score as the signal strength for every
        feature that has one. For suspicious_url_events (no z-score because
        it wasn't in BASELINE_COLS) use the raw count directly as the signal.
        Only features that are actually elevated (z > 0 or raw > 0) are
        included, so a user with zero suspicious activity gets an empty list.

        row  : pandas Series -- one user-day AFTER score_batch() processing
               (so z-score columns are already present).
        user : str -- the user ID, used to look up their personal baseline.
        """
        signals = []

        for base_feat, label in FEATURE_LABELS.items():
            zscore_col = f"{base_feat}_personal_zscore"
            raw_val = float(row.get(base_feat, 0) or 0)

            # Determine signal strength
            if zscore_col in row.index and not pd.isna(row[zscore_col]):
                z = float(row[zscore_col])
            elif base_feat == "suspicious_url_events":
                # No personal z-score for this feature; treat raw count as
                # strength (0 = no signal, any visit is unusual enough to flag).
                z = raw_val
            else:
                continue  # feature not in row at all, skip

            # Skip features that aren't elevated -- no point surfacing them
            if z <= 0 and raw_val == 0:
                continue

            # Look up the user's personal mean from the saved baseline stats
            user_baseline = None
            if base_feat in self.baseline_stats:
                mean_series = self.baseline_stats[base_feat]["mean"]
                user_baseline = float(
                    mean_series.get(user, mean_series.mean())
                )

            # Build the human-readable description
            if user_baseline is not None and user_baseline >= 0.05:
                desc = (
                    f"{int(raw_val)} {label} "
                    f"(your normal: ~{user_baseline:.1f})"
                )
            elif user_baseline is not None and raw_val > 0:
                desc = f"{int(raw_val)} {label} (normally none)"
            else:
                desc = f"{int(raw_val)} {label}"

            signals.append({
                "feature":       base_feat,
                "zscore":        round(z, 2),
                "raw_value":     raw_val,
                "user_baseline": round(user_baseline, 2) if user_baseline is not None else None,
                "label":         desc,
            })

        # Sort by absolute z-score descending; return top N
        signals.sort(key=lambda s: abs(s["zscore"]), reverse=True)
        return signals[:top_n]

    # -----------------------------------------------------------------
    # Scoring
    # -----------------------------------------------------------------
    def score_batch(self, df):
        """
        df: DataFrame of new user-day rows (one or many). Returns a
        DataFrame with 'risk_score' (0-100, clipped) and 'risk_tier' added.
        Note: z-score columns are also present on the returned DataFrame --
        score_row() uses them for explainability without a second pass.
        """
        df = self._validate_and_fill(df)

        # Apply the SAME baseline stats fit at train time. Unseen users
        # fall back to the global mean/std inside apply_baseline_stats.
        df = apply_baseline_stats(df, self.baseline_stats)

        # Make sure every model feature column exists post-baseline-apply
        # (e.g. a z-score column for a BASELINE_COLS entry that wasn't in
        # this batch at all still needs to exist, filled at 0 / neutral).
        for col in self.feature_cols:
            if col not in df.columns:
                df[col] = 0.0

        X = df[self.feature_cols].astype(float)
        X_scaled = self.scaler.transform(X)

        raw_scores = -self.model.decision_function(X_scaled)

        # Clip Isolation Forest score against the TRAIN-time range
        if_scaled = 100 * (raw_scores - self.score_min) / (self.score_max - self.score_min)
        if_scores = np.clip(if_scaled, 0, 100)

        # Blend with supervised model when available.
        # Old bundles (no supervised_model key) degrade to pure IF scoring.
        if self.supervised_model is not None:
            sup_scores = self.supervised_model.predict_proba(X_scaled)[:, 1] * 100
            df["if_score"]         = if_scores
            df["supervised_score"] = sup_scores
            final_scores = np.clip(
                ENSEMBLE_WEIGHT_IF * if_scores + ENSEMBLE_WEIGHT_SUPERVISED * sup_scores,
                0, 100,
            )
        else:
            final_scores = if_scores

        df["risk_score"] = final_scores
        df["risk_tier"]  = df["risk_score"].apply(lambda s: score_to_tier(s, self.tier_cutoffs))

        return df

    def score_row(self, row_dict, top_n=4):
        """
        Score a single user-day (dict or JSON body) and return a rich result.

        Returns
        -------
        dict with keys:
            user          -- user ID
            risk_score    -- 0-100 float
            risk_tier     -- Low / Medium / High / Critical
            model_version -- version string from the saved bundle
            top_signals   -- list of up to `top_n` dicts, each with:
                               feature       raw feature name
                               zscore        deviation from user's personal baseline
                               raw_value     actual count/value for this day
                               user_baseline user's typical daily average
                               label         human-readable explanation string
        """
        df = pd.DataFrame([row_dict])
        scored = self.score_batch(df)   # z-score cols are on `scored` after this
        out = scored.iloc[0]
        user = str(out["user"])

        return {
            "user":          user,
            "risk_score":    round(float(out["risk_score"]), 2),
            "risk_tier":     out["risk_tier"],
            "model_version": self.version,
            "top_signals":   self._get_top_signals(out, user, top_n=top_n),
        }


def main():
    parser = argparse.ArgumentParser(description="Score new user-day rows with a saved model bundle.")
    parser.add_argument("--model", default="models/model_v1.pkl", help="Path to saved model bundle")
    parser.add_argument("--input", required=True, help="CSV of new user-day feature rows")
    parser.add_argument("--output", default="scored_output.csv", help="Where to write scored results")
    parser.add_argument("--explain", action="store_true",
                        help="Print top signals for the highest-risk users")
    args = parser.parse_args()

    predictor = RiskPredictor(args.model)
    df = pd.read_csv(args.input)
    scored = predictor.score_batch(df)

    # Drop internal z-score columns from the CSV output to keep it readable
    output_cols = [c for c in scored.columns if not c.endswith("_personal_zscore")]
    scored[output_cols].to_csv(args.output, index=False)
    print(f"Scored {len(scored)} rows -> {args.output}")
    print(scored[["user", "risk_score", "risk_tier"]].sort_values("risk_score", ascending=False).head(20))

    if args.explain:
        print("\n=== Top signals for highest-risk users ===")
        top_users = scored.sort_values("risk_score", ascending=False).head(10)
        for _, row in top_users.iterrows():
            user = str(row["user"])
            signals = predictor._get_top_signals(row, user)
            print(f"\n{user}  score={row['risk_score']:.1f}  tier={row['risk_tier']}")
            if signals:
                for s in signals:
                    print(f"  [{s['zscore']:+.1f}σ]  {s['label']}")
            else:
                print("  (no elevated signals found)")


if __name__ == "__main__":
    main()
