"""
Verifies that http_filtered.csv contains exactly the expected users
(70 malicious + sampled normal users) with no extras.

Usage:
    python src/verify_http_filter.py
"""

import pandas as pd

ANSWERS_PATH = "data/answers/insiders.csv"
KEEP_IDS_PATH = "data/keep_user_ids.txt"
HTTP_FILTERED_PATH = "data/http_filtered.csv"


def main():
    # Rebuild keep_ids from the file you already saved earlier
    with open(KEEP_IDS_PATH) as f:
        keep_ids = set(line.strip() for line in f if line.strip())

    print(f"Expected user count (from keep_user_ids.txt): {len(keep_ids)}")

    http_filtered = pd.read_csv(HTTP_FILTERED_PATH)
    actual_users = set(http_filtered["user"])

    print(f"Users actually found in http_filtered.csv: {http_filtered['user'].nunique()}")

    extra = actual_users - keep_ids
    missing = keep_ids - actual_users

    print(f"\nExtra users (shouldn't be there): {len(extra)}")
    if extra:
        print(extra)

    print(f"\nMissing users (expected but not found): {len(missing)}")
    if missing:
        print(missing)

    if not extra and not missing:
        print("\n✅ Filtering looks correct.")
    elif missing and not extra:
        print("\n⚠️ Some users have no http activity at all -- this can be normal "
              "(same as the KPC0073 case in file.csv). Not necessarily a bug.")
    else:
        print("\n❌ Unexpected extra users found -- check grep pattern for substring matches.")


if __name__ == "__main__":
    main()