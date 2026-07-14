"""
Unified feature engineering for CERT r4.2 insider threat detection.

Builds ONE per-user-per-day feature table from logon, device, file,
email, and (optionally) http data. Output: a single features.csv
ready to feed directly into the Isolation Forest model.

Usage:
    python src/feature_engineering.py
"""

import pandas as pd
import numpy as np
from config import (
    LOGON_PATH, DEVICE_PATH, FILE_PATH, EMAIL_PATH, HTTP_PATH,
    FEATURES_RAW_PATH, OFF_HOURS_START, OFF_HOURS_END, SUSPICIOUS_KEYWORDS,
    INTERNAL_EMAIL_DOMAIN,
)

OUTPUT_PATH = FEATURES_RAW_PATH

# Flip to True once http_filtered.csv exists (after the download
# finishes and you've run the grep filtering step)
INCLUDE_HTTP = True


def load_and_parse(path):
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"], format="%m/%d/%Y %H:%M:%S")
    df["day"] = df["date"].dt.date
    df["hour"] = df["date"].dt.hour
    df["weekday"] = df["date"].dt.dayofweek
    return df


def build_logon_features(logon):
    logon = logon.copy()
    logon["is_off_hours"] = (logon["hour"] >= OFF_HOURS_START) | (logon["hour"] < OFF_HOURS_END)
    logon["is_weekend"] = logon["weekday"] >= 5

    return logon.groupby(["user", "day"]).agg(
        logon_count=("activity", lambda x: (x == "Logon").sum()),
        logoff_count=("activity", lambda x: (x == "Logoff").sum()),
        unique_pcs=("pc", "nunique"),
        off_hours_events=("is_off_hours", "sum"),
        is_weekend=("is_weekend", "max"),
        first_hour=("hour", "min"),
        last_hour=("hour", "max"),
    ).reset_index()


def build_device_features(device):
    device = device.copy()
    device["is_off_hours"] = (device["hour"] >= OFF_HOURS_START) | (device["hour"] < OFF_HOURS_END)

    return device.groupby(["user", "day"]).agg(
        device_connects=("activity", lambda x: (x == "Connect").sum()),
        device_off_hours=("is_off_hours", "sum"),
    ).reset_index()


def build_file_features(file_df):
    file_df = file_df.copy()
    file_df["is_removable"] = file_df["filename"].astype(str).str.startswith("R:")

    return file_df.groupby(["user", "day"]).agg(
        file_events=("id", "count"),
        unique_files=("filename", "nunique"),
        removable_file_events=("is_removable", "sum"),
    ).reset_index()


def count_recipients(row):
    total = 0
    for field in ["to", "cc", "bcc"]:
        val = row.get(field)
        if pd.notna(val) and val != "":
            total += len(str(val).split(";"))
    return total


def is_external_domain(email_str, internal_domain=INTERNAL_EMAIL_DOMAIN):
    if pd.isna(email_str) or email_str == "":
        return False
    return any(internal_domain not in addr for addr in str(email_str).split(";"))


def build_email_features(email):
    email = email.copy()
    email["is_off_hours"] = (email["hour"] >= OFF_HOURS_START) | (email["hour"] < OFF_HOURS_END)
    email["recipient_count"] = email.apply(count_recipients, axis=1)
    email["has_bcc"] = email["bcc"].notna() & (email["bcc"] != "") if "bcc" in email.columns else False
    email["to_external"] = email["to"].apply(is_external_domain) if "to" in email.columns else False

    return email.groupby(["user", "day"]).agg(
        email_count=("id", "count"),
        avg_recipients=("recipient_count", "mean"),
        max_recipients=("recipient_count", "max"),
        bcc_count=("has_bcc", "sum"),
        external_email_count=("to_external", "sum"),
        email_off_hours=("is_off_hours", "sum"),
    ).reset_index()


def build_http_features(http):
    http = http.copy()
    http["url"] = http["url"].astype(str).str.lower()
    http["is_suspicious"] = http["url"].str.contains("|".join(SUSPICIOUS_KEYWORDS), regex=True)

    return http.groupby(["user", "day"]).agg(
        http_events=("id", "count"),
        unique_urls=("url", "nunique"),
        suspicious_url_events=("is_suspicious", "sum"),
    ).reset_index()


def main():
    print("Loading logon.csv...")
    logon_feat = build_logon_features(load_and_parse(LOGON_PATH))

    print("Loading device.csv...")
    device_feat = build_device_features(load_and_parse(DEVICE_PATH))

    print("Loading file.csv...")
    file_feat = build_file_features(load_and_parse(FILE_PATH))

    print("Loading email.csv...")
    email_feat = build_email_features(load_and_parse(EMAIL_PATH))

    features = logon_feat.merge(device_feat, on=["user", "day"], how="outer")
    features = features.merge(file_feat, on=["user", "day"], how="outer")
    features = features.merge(email_feat, on=["user", "day"], how="outer")

    if INCLUDE_HTTP:
        print("Loading http_filtered.csv...")
        http_feat = build_http_features(load_and_parse(HTTP_PATH))
        features = features.merge(http_feat, on=["user", "day"], how="outer")
    else:
        print("Skipping http.csv (INCLUDE_HTTP = False).")

    numeric_cols = features.select_dtypes(include=[np.number]).columns
    features[numeric_cols] = features[numeric_cols].fillna(0)
    features["is_weekend"] = features["is_weekend"].fillna(False)

    features.to_csv(OUTPUT_PATH, index=False)
    print(f"Saved {len(features)} user-day rows to {OUTPUT_PATH}")
    print(f"Unique users: {features['user'].nunique()}")
    print(f"Columns: {features.columns.tolist()}")


if __name__ == "__main__":
    main()