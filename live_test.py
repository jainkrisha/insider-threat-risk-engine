import urllib.request
import json
import time

def run_test():
    print("--- Starting Live Click-Through Test ---")
    
    # 1. Trigger Critical Risk Analysis
    print("\n1. Triggering Critical risk via POST /score...")
    url = "http://127.0.0.1:8000/score"
    payload = json.dumps({
        "user": "CCA0046",
        "logon_count": 5,
        "off_hours_events": 10,
        "suspicious_url_events": 24,
        "external_email_count": 8
    }).encode('utf-8')
    req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'}, method='POST')
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            print(f"Risk Tier: {result['risk_tier']}")
            print(f"Risk Score: {result['risk_score']}")
            record_id = result.get('audit_record_id')
            print(f"Audit Record ID received: {record_id}")
            assert record_id is not None, "Audit record ID is missing!"
    except Exception as e:
        print(f"Failed to score: {e}")
        return

    # 2. Decrypt the content via GET /vault/{record_id}
    print(f"\n2. Verifying decryption via GET /vault/{record_id}...")
    vault_url = f"http://127.0.0.1:8000/vault/{record_id}"
    req2 = urllib.request.Request(vault_url, method='GET')
    try:
        with urllib.request.urlopen(req2) as response:
            vault_res = json.loads(response.read().decode('utf-8'))
            print("Decrypted Content Match:")
            print(json.dumps(vault_res['audit_entry'], indent=2))
            assert vault_res['audit_entry']['user_id'] == 'CCA0046', "Decrypted content doesn't match original user!"
            print("Success! Decrypted content matches.")
    except Exception as e:
        print(f"Failed to retrieve vault entry: {e}")
        return

    # 3. Check the raw stored line in vault_store.jsonl
    print("\n3. Verifying raw stored line is gibberish...")
    try:
        with open("vault_store.jsonl", "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
            last_line = lines[-1]
            print(f"Raw line length: {len(last_line)} characters")
            # Verify no plaintext is in the raw line
            assert "CCA0046" not in last_line, "Plaintext user ID found in vault store!"
            assert "Critical" not in last_line, "Plaintext risk tier found in vault store!"
            print("Raw stored line is securely encrypted (gibberish).")
    except Exception as e:
        print(f"Failed to verify raw vault store: {e}")
        return

    print("\n--- Live Click-Through Test Completed Successfully ---")

if __name__ == "__main__":
    # Give the server a moment to ensure it's up
    time.sleep(2)
    run_test()
