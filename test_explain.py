"""
Smoke test for the new _get_top_signals / score_row explainability feature.
Run from the project root:
    python test_explain.py
"""
import sys
import pandas as pd
sys.path.insert(0, "src")

from src.predict import RiskPredictor

predictor = RiskPredictor("models/model_v1.pkl")

df = pd.read_csv("features.csv")
df["day"] = pd.to_datetime(df["day"])

# ── Test 1: known malicious user (CCA0046 -- scenario 3, sysadmin threat) ──
cca = df[df["user"] == "CCA0046"].sort_values("off_hours_events", ascending=False).iloc[0]
row = cca.to_dict()
row["day"] = str(row["day"].date()) if hasattr(row["day"], "date") else row["day"]

result = predictor.score_row(row)
print("=" * 60)
print(f"USER:        {result['user']}")
print(f"RISK SCORE:  {result['risk_score']}")
print(f"RISK TIER:   {result['risk_tier']}")
print(f"MODEL VER:   {result['model_version']}")
print("\nTOP SIGNALS:")
for s in result["top_signals"]:
    print(f"  [{s['zscore']:+.2f}z]  {s['label']}")
if not result["top_signals"]:
    print("  (none -- user appears normal on this day)")

# ── Test 2: edge case -- completely unknown new user with minimal data ──
print("\n" + "=" * 60)
new_user_result = predictor.score_row({
    "user": "BRAND_NEW_USER_001",
    "day": "2011-06-01",
    "logon_count": 1,
    # all other fields intentionally omitted -- tests _validate_and_fill
})
print(f"USER:        {new_user_result['user']}")
print(f"RISK SCORE:  {new_user_result['risk_score']}")
print(f"RISK TIER:   {new_user_result['risk_tier']}")
print("\nTOP SIGNALS:")
for s in new_user_result["top_signals"]:
    print(f"  [{s['zscore']:+.2f}z]  {s['label']}")
if not new_user_result["top_signals"]:
    print("  (none -- new user, no elevated activity to flag)")

# ── Test 3: highly suspicious synthetic row ──
print("\n" + "=" * 60)
suspicious_result = predictor.score_row({
    "user": "CCA0046",
    "day": "2011-01-15",
    "off_hours_events": 12,
    "removable_file_events": 45,
    "suspicious_url_events": 8,
    "external_email_count": 20,
    "unique_pcs": 5,
})
print(f"USER:        {suspicious_result['user']}")
print(f"RISK SCORE:  {suspicious_result['risk_score']}")
print(f"RISK TIER:   {suspicious_result['risk_tier']}")
print("\nTOP SIGNALS:")
for s in suspicious_result["top_signals"]:
    print(f"  [{s['zscore']:+.2f}z]  {s['label']}")

print("\nAll tests passed -- no crashes.")
