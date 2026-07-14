"""
Diagnostic: how well does the model actually rank malicious users?
Run from project root: python check_f1.py
"""
import sys, json
import pandas as pd
import numpy as np

sys.path.insert(0, "src")
from config import score_to_tier

scores = pd.read_csv("risk_scores_test.csv")

with open("models/model_v1_meta.json") as f:
    meta = json.load(f)

tier_cutoffs = meta["tier_cutoffs"]
scores["tier"] = scores["max_risk_score"].apply(lambda s: score_to_tier(s, tier_cutoffs))

total_users = len(scores)
total_malicious = int(scores["is_malicious"].sum())

# Prefer composite_score (new) over max_risk_score (old) for ranking
rank_col = "composite_score" if "composite_score" in scores.columns else "max_risk_score"

print("=== Test window overview ===")
print(f"Total users in test window : {total_users}")
print(f"Malicious users in window  : {total_malicious}")
print(f"Ranking by                 : {rank_col}")
print()

print("=== Score distribution ===")
print(scores[rank_col].describe().round(2))
print()

print("=== Precision / Recall / F1 at every top-N ===")
scores_sorted = scores.sort_values(rank_col, ascending=False).reset_index(drop=True)

for n in [10, 20, 30, 50, 70, 100, 150, 200]:
    if n > total_users:
        break
    top_n = scores_sorted.head(n)
    tp = int(top_n["is_malicious"].sum())
    precision = tp / n
    recall = tp / total_malicious if total_malicious > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    print(f"  Top {n:3d}:  caught {tp:2d}/{total_malicious}  |  P={precision:.3f}  R={recall:.3f}  F1={f1:.3f}")

print()
print("=== Tier breakdown ===")
tier_summary = scores.groupby("tier").agg(
    total=("is_malicious", "count"),
    malicious=("is_malicious", "sum"),
).reset_index()
tier_summary["precision"] = (tier_summary["malicious"] / tier_summary["total"]).round(3)
print(tier_summary.to_string(index=False))

print()
print("=== Where is each malicious user ranked? ===")
scores_sorted["rank"] = range(1, len(scores_sorted) + 1)
malicious_rows = scores_sorted[scores_sorted["is_malicious"]].copy()
malicious_rows = malicious_rows.sort_values("rank")
display_cols = ["user", "rank", rank_col, "max_risk_score", "mean_risk_score", "tier"]
display_cols = [c for c in display_cols if c in scores_sorted.columns]
print(malicious_rows[display_cols].to_string(index=False))

print()
missed = malicious_rows[malicious_rows["rank"] > 100]
print(f"Malicious users ranked OUTSIDE top-100: {len(missed)}")
if len(missed) > 0:
    print(missed[["user", "rank", "max_risk_score"]].to_string(index=False))
