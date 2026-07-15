import sys
sys.path.insert(0, 'src')
# pyrefly: ignore [missing-import]
from predict import RiskPredictor

predictor = RiskPredictor('models/model_v1.pkl')

# User 1: High risk because of a spike
res1 = predictor.score_row({
    'user': 'CCA0046', 'day': '2026-07-15',
    'logon_count': 5, 'off_hours_events': 15, 'suspicious_url_events': 20
})

# User 2: Medium/High risk because of a drop
res2 = predictor.score_row({
    'user': 'BAL0044', 'day': '2026-07-15',
    'logon_count': 0, 'off_hours_events': 0, 'suspicious_url_events': 0
})

def print_res(res, name):
    print(f"\n{name}:")
    print(f"Score: {res['risk_score']:.1f} Tier: {res['risk_tier']}")
    reasons = [s['label'] for s in res.get('top_signals', [])]
    if reasons:
        reasons_str = ', and '.join(reasons) if len(reasons) <= 2 else ', '.join(reasons[:-1]) + ', and ' + reasons[-1]
        print(f"Narrative: This is primarily because they had {reasons_str}.")
    else:
        print("Narrative: Their activity aligns with their normal historical baseline.")

print_res(res1, "User 1 (Spike)")
print_res(res2, "User 2 (Drop)")
