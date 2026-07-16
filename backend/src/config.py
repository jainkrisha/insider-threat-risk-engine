"""
Single source of truth for paths, thresholds, and feature-column logic.

Every script (feature_engineering.py, train.py, predict.py, tune_model.py,
compare_features.py) imports from here instead of redefining things.
Change a threshold once, it's correct everywhere.
"""

import os

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_DIR = "data"
LOGON_PATH = os.path.join(DATA_DIR, "logon.csv")
DEVICE_PATH = os.path.join(DATA_DIR, "device.csv")
FILE_PATH = os.path.join(DATA_DIR, "file.csv")
EMAIL_PATH = os.path.join(DATA_DIR, "email.csv")
HTTP_PATH = os.path.join(DATA_DIR, "http_filtered.csv")
ANSWERS_PATH = os.path.join(DATA_DIR, "answers", "insiders.csv")
PSYCHOMETRIC_PATH = os.path.join(DATA_DIR, "psychometric.csv")

FEATURES_RAW_PATH = "features.csv"
FEATURES_BASELINE_PATH = "features_baseline.csv"

MODEL_DIR = "models"  # train.py saves versioned artifacts here

# ---------------------------------------------------------------------------
# Feature engineering constants
# ---------------------------------------------------------------------------
OFF_HOURS_START = 20  # 8 PM
OFF_HOURS_END = 6     # 6 AM

SUSPICIOUS_KEYWORDS = [
    "wikileaks", "leak", "confidential", "classified", "job", "career",
    "resume", "indeed.com", "linkedin.com/jobs", "monster.com",
]

INTERNAL_EMAIL_DOMAIN = "dtaa.com"

# Raw columns we compute *personal* (per-user) z-scores for.
# NOTE: z-score stats must be fit on TRAIN data only -- see baseline_features.py
BASELINE_COLS = [
    "logon_count", "off_hours_events", "unique_pcs",
    "device_connects", "device_off_hours",
    "file_events", "removable_file_events",
    "email_count", "external_email_count",
]

# ---------------------------------------------------------------------------
# Model constants
# ---------------------------------------------------------------------------
CONTAMINATION = 0.05
RANDOM_STATE = 42
N_ESTIMATORS = 200

# The six raw "hand-picked" signal columns + every *_personal_zscore column
# found in the dataframe. This used to be copy-pasted (slightly differently!)
# across model.py, tune_model.py, and compare_features.py.
CORE_RAW_FEATURES = [
    "off_hours_events", "device_off_hours", "removable_file_events",
    "unique_pcs", "external_email_count", "suspicious_url_events",
]


def get_feature_columns(df):
    """
    The ONE place that decides which columns feed the model.
    Returns only columns that actually exist in `df`, so this is safe
    to call whether or not HTTP/z-score features were included upstream.
    """
    zscore_cols = [c for c in df.columns if c.endswith("_personal_zscore")]
    cols = zscore_cols + CORE_RAW_FEATURES
    return [c for c in cols if c in df.columns]


# ---------------------------------------------------------------------------
# Time-based train/test split (fixes the evaluation leakage)
# ---------------------------------------------------------------------------
# Fraction of the dataset's date range used for training. CERT r4.2 spans
# ~17 months; 0.53 puts the cutoff at ~9 months in, matching "train on the
# first 8-9 months, evaluate on the rest". Computed as a fraction of the
# actual date range in your data (not a hardcoded date) so it's robust if
# your extract's exact start/end differs.
TRAIN_FRACTION = 0.53


# ---------------------------------------------------------------------------
# Risk tiers (for the UI / backend contract)
# ---------------------------------------------------------------------------
# Percentile-based cutoffs on the 0-100 risk_score distribution produced at
# TRAIN time. Saved alongside the model (see train.py) so predict.py always
# uses the cutoffs that matched the training distribution, not a moving
# target recomputed on every live batch.
RISK_TIER_PERCENTILES = {
    "Low": 0.0,
    "Medium": 0.80,
    "High": 0.95,
    "Critical": 0.99,
}


# Risk tiers that trigger an encrypted audit vault entry.
# Any /score result at or above these tiers will be stored in the hybrid vault.
VAULT_AUDIT_RISK_TIERS = ["High", "Critical"]


def score_to_tier(score, tier_cutoffs):
    """
    tier_cutoffs: dict like {"Low": 0.0, "Medium": 41.2, "High": 68.5, "Critical": 89.1}
    (actual score values, produced by train.py from RISK_TIER_PERCENTILES)
    """
    tier = "Low"
    for name, cutoff in sorted(tier_cutoffs.items(), key=lambda kv: kv[1]):
        if score >= cutoff:
            tier = name
    return tier


# ---------------------------------------------------------------------------
# Ensemble: Isolation Forest (unsupervised) + Random Forest (supervised)
# Blending means unknown/novel threats are still caught by IF, while
# known insider threat patterns are boosted by the supervised model.
# ---------------------------------------------------------------------------
ENSEMBLE_WEIGHT_IF         = 0.60   # Isolation Forest share
ENSEMBLE_WEIGHT_SUPERVISED = 0.40   # Supervised Random Forest share


# ---------------------------------------------------------------------------
# Per-user composite score aggregation
# Using only max_risk_score misses slow-burn threats (Scenario 2) that never
# spike dramatically but accumulate many moderately-suspicious days.
# The composite rewards BOTH peak anomaly days AND sustained high-risk activity.
# ---------------------------------------------------------------------------
HIGH_RISK_DAY_THRESHOLD = 70.0   # day score above this counts as a "high-risk day"
AGG_WEIGHT_MAX           = 0.50   # weight on max daily score
AGG_WEIGHT_MEAN          = 0.30   # weight on mean daily score
AGG_WEIGHT_HIGHDAYS      = 0.20   # weight on high-risk day rate (0-100 scaled)


# ---------------------------------------------------------------------------
# Privilege-aware scoring
# ---------------------------------------------------------------------------
# The four privilege tiers supported by the /score endpoint.
PRIVILEGE_TIERS = ["standard", "elevated", "admin", "domain_admin"]

# Extra recommended actions layered on top of the base tier actions when
# a privileged account exceeds a given risk tier.
# Structure: { privilege_tier: { risk_tier: [action, ...] } }
PRIVILEGE_ACTIONS = {
    "standard": {
        "Low":      [],
        "Medium":   [],
        "High":     [],
        "Critical": [],
    },
    "elevated": {
        "Low":      [],
        "Medium":   ["log_enhanced"],
        "High":     ["suspend_elevated_access", "log_enhanced"],
        "Critical": ["revoke_elevated_access", "alert_soc_immediately"],
    },
    "admin": {
        "Low":      [],
        "Medium":   ["log_enhanced"],
        "High":     ["revoke_admin_access", "alert_soc_immediately"],
        "Critical": ["revoke_admin_access", "isolate_account", "alert_soc_immediately"],
    },
    "domain_admin": {
        "Low":      ["log_standard"],
        "Medium":   ["log_enhanced", "peer_review"],
        "High":     ["suspend_domain_admin", "alert_soc_immediately", "incident_report"],
        "Critical": ["revoke_domain_admin", "isolate_account", "alert_soc_immediately", "incident_report"],
    },
}

# ---------------------------------------------------------------------------
# HNDL (Harvest-Now-Decrypt-Later) exposure actions
# ---------------------------------------------------------------------------
# Actions triggered based on the HNDL exposure tier, independent of
# the behavioral risk tier. Focuses on PQC migration and data egress review.
HNDL_ACTIONS = {
    "Low":      [],
    "Medium":   ["review_data_exports"],
    "High":     ["review_data_exports", "flag_pqc_migration"],
    "Critical": ["review_data_exports", "flag_pqc_migration", "restrict_external_transfer", "alert_soc_immediately"],
}
