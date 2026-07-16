"""
Integration check: verifies all cross-file wiring is correct.
Run from the project root: python integration_check.py
"""
import sys
import re

PASS = []
FAIL = []

def check(label, condition):
    if condition:
        PASS.append(label)
        print(f"  [OK]  {label}")
    else:
        FAIL.append(label)
        print(f"  [FAIL] {label}")

# ── Read files ─────────────────────────────────────────────────────────────
with open("api.py", encoding="utf-8") as f:
    api_py = f.read()

with open("frontend/src/api.ts", encoding="utf-8") as f:
    api_ts = f.read()

with open("frontend/src/pages/Dashboard.tsx", encoding="utf-8") as f:
    dashboard = f.read()

with open("frontend/src/pages/Report.tsx", encoding="utf-8") as f:
    report = f.read()

with open("frontend/src/components/EnforcementPanel.tsx", encoding="utf-8") as f:
    ep = f.read()

# ── Backend checks ──────────────────────────────────────────────────────────
print("\n=== Backend (api.py) ===")
check("require_api_key dependency defined",       "def require_api_key" in api_py)
check("/score endpoint has auth",                 "score_user_activity(request: ScoreRequest, _key: str = Depends(require_api_key))" in api_py)
check("/vault endpoint has auth",                 "read_vault_entry(record_id: str, _key: str = Depends(require_api_key))" in api_py)
check("/trend endpoint has auth",                 "get_user_trend(user_id: str, _key: str = Depends(require_api_key))" in api_py)
check("/trend endpoint returns 7 points",         "_TREND_DATA" in api_py)
check("HTML dashboard sends X-API-Key header",    "'X-API-Key': 'demo-finspark-key'" in api_py)
check("/health stays public (no auth dep)",       "@app.get(\"/health\")\ndef health_check():" in api_py)
check("SYSADM01 trend data defined",              '"SYSADM01"' in api_py)
check("4 demo users in trend data",               api_py.count('"day": -6') == 4)

# ── Frontend api.ts checks ──────────────────────────────────────────────────
print("\n=== Frontend API client (api.ts) ===")
check("AUTH_HEADERS constant defined",            "AUTH_HEADERS" in api_ts)
check("X-API-Key in AUTH_HEADERS",               "'X-API-Key'" in api_ts)
check("scoreUser uses AUTH_HEADERS",              "headers: AUTH_HEADERS" in api_ts)
check("fetchVaultEntry uses AUTH_HEADERS",        "fetchVaultEntry" in api_ts and "AUTH_HEADERS" in api_ts)
check("fetchUserTrend exported",                  "export async function fetchUserTrend" in api_ts)
check("TrendResponse type exported",              "export interface TrendResponse" in api_ts)
check("4 DEMO_SCENARIOS defined",                api_ts.count("label:") >= 4)
check("SYSADM01 scenario exists",                "SYSADM01" in api_ts)
check("privilege_tier in DEMO_SCENARIOS",        "privilege_tier:" in api_ts)

# ── Dashboard.tsx checks ────────────────────────────────────────────────────
print("\n=== Dashboard.tsx ===")
check("Imports EnforcementPanel",                "import EnforcementPanel" in dashboard)
check("Imports fetchUserTrend",                  "fetchUserTrend" in dashboard)
check("Uses EnforcementPanel component",         "<EnforcementPanel" in dashboard)
check("Uses TrendChart component",               "TrendChart" in dashboard)
check("4-column grid for scenarios",             "md:grid-cols-4" in dashboard)
check("trend state variable",                    "setTrend" in dashboard)
check("Privilege badge in result card",          "privilege_tier" in dashboard)
check("Crown icon for privileged scenarios",     "Crown" in dashboard)

# ── Report.tsx checks ───────────────────────────────────────────────────────
print("\n=== Report.tsx ===")
check("Imports EnforcementPanel",                "import EnforcementPanel" in report)
check("Uses EnforcementPanel component",         "<EnforcementPanel" in report)
check("ShieldCheck imported",                    "ShieldCheck" in report)
check("Old static chip list removed",            "flex flex-wrap gap-2" not in report or "EnforcementPanel" in report)

# ── EnforcementPanel.tsx checks ─────────────────────────────────────────────
print("\n=== EnforcementPanel.tsx ===")
check("Accepts actions: string[] prop",          "actions: string[]" in ep)
check("Has dispatched state",                    "dispatched" in ep)
check("Has Threat Contained banner",             "Threat Contained" in ep)
check("Has 620ms simulated delay",               "620" in ep)
check("Covers alert_soc_immediately",            "alert_soc_immediately" in ep)
check("Covers suspend_admin_session",            "suspend_admin_session" in ep)
check("Covers revoke_domain_admin_token",        "revoke_domain_admin_token" in ep)
check("Covers alert_ciso",                       "alert_ciso" in ep)

# ── Summary ──────────────────────────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"  PASSED: {len(PASS)}/{len(PASS)+len(FAIL)}")
if FAIL:
    print(f"  FAILED: {len(FAIL)}")
    for f in FAIL:
        print(f"    - {f}")
else:
    print("  All integration checks passed!")
