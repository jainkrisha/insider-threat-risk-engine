import sys
sys.path.insert(0, "src")
from src.predict import RiskPredictor

def test_narrative_generation():
    predictor = RiskPredictor("models/model_v1.pkl")

    # 1. Low risk user (normal behavior matching baseline)
    res_low = predictor.score_row({
        "user": "BAL0044", "day": "2026-07-15",
        "logon_count": 5, "off_hours_events": 0, "suspicious_url_events": 0,
        "email_count": 11, "unique_pcs": 4, "device_connects": 3, "external_email_count": 5,
        "device_off_hours": 0, "file_events": 10, "removable_file_events": 0
    })

    # 2. Medium risk user (slight anomaly)
    res_med = predictor.score_row({
        "user": "ABC0001", "day": "2026-07-15",
        "logon_count": 5, "off_hours_events": 5, "suspicious_url_events": 0,
        "email_count": 8, "unique_pcs": 2, "device_connects": 1, "external_email_count": 4,
        "device_off_hours": 0, "file_events": 5, "removable_file_events": 0
    })

    # 3. Critical user with a SPIKE
    res_spike = predictor.score_row({
        "user": "CCA0046", "day": "2026-07-15",
        "logon_count": 5, "off_hours_events": 15, "suspicious_url_events": 20
    })

    # 4. Critical user with a DROP
    res_drop = predictor.score_row({
        "user": "BAL0044", "day": "2026-07-15",
        "logon_count": 0, "off_hours_events": 0, "suspicious_url_events": 0
    })

    def get_narrative(res):
        tier = res["risk_tier"]
        score = res["risk_score"]
        reasons = [s["label"] for s in res.get("top_signals", [])]
        if reasons:
            reasons_str = ", and ".join(reasons) if len(reasons) <= 2 else ", ".join(reasons[:-1]) + ", and " + reasons[-1]
            return f"User {res['user']} was flagged as a {tier} risk (Score: {score:.1f}/100). This is primarily because they had {reasons_str}."
        else:
            return f"User {res['user']} is currently a {tier} risk (Score: {score:.1f}/100). Their activity aligns with their normal historical baseline."

    n_low = get_narrative(res_low)
    n_med = get_narrative(res_med)
    n_spike = get_narrative(res_spike)
    n_drop = get_narrative(res_drop)

    print("--- Test Outputs ---")
    print("Low:", n_low)
    print("Medium:", n_med)
    print("Critical Spike:", n_spike)
    print("Critical Drop:", n_drop)

    # Assertions
    assert n_low != n_med, "Low and Medium narratives are identical!"
    assert n_med != n_spike, "Medium and Critical Spike narratives are identical!"
    assert n_spike != n_drop, "Critical Spike and Critical Drop narratives are identical!"

    assert "spike" in n_spike, "Spike narrative must contain the word 'spike'"
    assert "drop" in n_drop, "Drop narrative must contain the word 'drop'"

    print("\nSUCCESS: All narrative regression tests passed!")

if __name__ == "__main__":
    test_narrative_generation()
