"""
Tests for src/vault.py — quantum-safe hybrid audit vault.

Run from the project root:
    python test_vault.py

Test framework matches test_explain.py: plain Python assertions with
descriptive output, no external test runner required.
"""
import json
import os
import sys
import tempfile
import shutil

from src.vault import (
    HybridVault,
    VaultDecryptionError,
    VaultRecordNotFoundError,
    MLKEM768_CIPHERTEXT_SIZE,
    VAULT_STORE_PATH,
    VAULT_INDEX_PATH,
)


# ---------------------------------------------------------------------------
# Test fixtures — use a dedicated temp directory so tests don't pollute the
# real vault_keys/ directory or vault_store.jsonl.
# ---------------------------------------------------------------------------

def make_temp_vault():
    """Create a HybridVault backed by a fresh temporary directory."""
    tmp_dir = tempfile.mkdtemp(prefix="vault_test_")
    v = HybridVault(key_dir=tmp_dir)
    return v, tmp_dir


SAMPLE_ENTRY = {
    "user_id": "CCA0046",
    "risk_tier": "Critical",
    "action_taken": ["require_mfa", "restrict_removable_media", "alert_soc_immediately"],
    "explanation": "User CCA0046 was flagged as a Critical risk (Score: 98.2/100).",
    "timestamp": "2026-07-15T10:00:00Z",
    "session_id": "2011-06-14",
}


# ---------------------------------------------------------------------------
# Test 1: encrypt -> decrypt round-trip returns the exact original dict
# ---------------------------------------------------------------------------
print("=" * 60)
print("TEST 1: encrypt_entry -> decrypt_entry round-trip")

vault1, tmp1 = make_temp_vault()
try:
    encrypted = vault1.encrypt_entry(SAMPLE_ENTRY)
    decrypted = vault1.decrypt_entry(encrypted)
    assert decrypted == SAMPLE_ENTRY, (
        f"Round-trip failed.\n  Expected: {SAMPLE_ENTRY}\n  Got:      {decrypted}"
    )
    print("  PASS: decrypted entry matches original dict exactly")
finally:
    shutil.rmtree(tmp1)


# ---------------------------------------------------------------------------
# Test 2: the raw bytes in vault_store.jsonl contain NO readable field values
# ---------------------------------------------------------------------------
print("=" * 60)
print("TEST 2: vault_store.jsonl contains no readable plaintext")

# Use real store paths for this test (need actual file I/O)
# Save and restore original store/index files if they exist
_store_backup = None
_index_backup = None
if os.path.exists(VAULT_STORE_PATH):
    with open(VAULT_STORE_PATH, "rb") as f:
        _store_backup = f.read()
if os.path.exists(VAULT_INDEX_PATH):
    with open(VAULT_INDEX_PATH, "rb") as f:
        _index_backup = f.read()

# Clean slate for this test
for p in (VAULT_STORE_PATH, VAULT_INDEX_PATH):
    if os.path.exists(p):
        os.remove(p)

vault2, tmp2 = make_temp_vault()
try:
    vault2.store_entry(SAMPLE_ENTRY)
    with open(VAULT_STORE_PATH, "rb") as f:
        raw_bytes = f.read()

    # None of these plaintext values should appear verbatim in the store file
    forbidden_substrings = [
        b"CCA0046",
        b"Critical",
        b"require_mfa",
        b"alert_soc_immediately",
        b"98.2",
        b"2026-07-15",
        b"user_id",
        b"risk_tier",
        b"action_taken",
    ]
    for sub in forbidden_substrings:
        assert sub not in raw_bytes, (
            f"FAIL: plaintext substring {sub!r} found verbatim in vault_store.jsonl!"
        )
    print(f"  PASS: none of {len(forbidden_substrings)} plaintext substrings appear in the stored bytes")
finally:
    shutil.rmtree(tmp2)
    # Restore original store/index
    for p, bak in ((VAULT_STORE_PATH, _store_backup), (VAULT_INDEX_PATH, _index_backup)):
        if os.path.exists(p):
            os.remove(p)
        if bak is not None:
            with open(p, "wb") as f:
                f.write(bak)


# ---------------------------------------------------------------------------
# Test 3: tampering with any byte triggers VaultDecryptionError
# (proves AES-GCM authentication tag is actually active)
# ---------------------------------------------------------------------------
print("=" * 60)
print("TEST 3: byte-level tampering is detected via AES-GCM authentication")

vault3, tmp3 = make_temp_vault()
try:
    encrypted = vault3.encrypt_entry(SAMPLE_ENTRY)
    record = json.loads(encrypted)

    # Tamper with the ciphertext (flip a byte in the AES-GCM ciphertext)
    import base64
    ct_bytes = bytearray(base64.b64decode(record["ciphertext"]))
    ct_bytes[0] ^= 0xFF  # flip all bits of first byte
    record["ciphertext"] = base64.b64encode(bytes(ct_bytes)).decode()
    tampered = json.dumps(record, separators=(",", ":"))

    raised = False
    try:
        vault3.decrypt_entry(tampered)
    except VaultDecryptionError:
        raised = True

    assert raised, "FAIL: tampering with ciphertext should raise VaultDecryptionError but did not!"
    print("  PASS: ciphertext tampering correctly raises VaultDecryptionError")

    # Also test nonce tampering
    vault3b, tmp3b = make_temp_vault()
    try:
        encrypted2 = vault3b.encrypt_entry(SAMPLE_ENTRY)
        record2 = json.loads(encrypted2)
        nonce_bytes = bytearray(base64.b64decode(record2["nonce"]))
        nonce_bytes[0] ^= 0x01
        record2["nonce"] = base64.b64encode(bytes(nonce_bytes)).decode()
        tampered2 = json.dumps(record2, separators=(",", ":"))

        raised2 = False
        try:
            vault3b.decrypt_entry(tampered2)
        except VaultDecryptionError:
            raised2 = True

        assert raised2, "FAIL: nonce tampering should raise VaultDecryptionError but did not!"
        print("  PASS: nonce tampering correctly raises VaultDecryptionError")
    finally:
        shutil.rmtree(tmp3b)
finally:
    shutil.rmtree(tmp3)


# ---------------------------------------------------------------------------
# Test 4: read_entry with nonexistent record_id raises VaultRecordNotFoundError
# ---------------------------------------------------------------------------
print("=" * 60)
print("TEST 4: read_entry with nonexistent record_id raises VaultRecordNotFoundError")

# Use a clean store
for p in (VAULT_STORE_PATH, VAULT_INDEX_PATH):
    if os.path.exists(p):
        os.remove(p)

vault4, tmp4 = make_temp_vault()
try:
    raised4 = False
    try:
        vault4.read_entry("nonexistent_record_id_that_definitely_does_not_exist")
    except VaultRecordNotFoundError:
        raised4 = True

    assert raised4, "FAIL: VaultRecordNotFoundError should be raised for unknown record_id"
    print("  PASS: VaultRecordNotFoundError raised for unknown record_id")
finally:
    shutil.rmtree(tmp4)
    for p in (VAULT_STORE_PATH, VAULT_INDEX_PATH):
        if os.path.exists(p):
            os.remove(p)
    # Restore originals again if needed
    for p, bak in ((VAULT_STORE_PATH, _store_backup), (VAULT_INDEX_PATH, _index_backup)):
        if bak is not None:
            with open(p, "wb") as f:
                f.write(bak)


# ---------------------------------------------------------------------------
# Test 5: vault is genuinely using ML-KEM-768
# (ciphertext length = 1088 bytes; fails loudly if the PQ component is absent)
# ---------------------------------------------------------------------------
print("=" * 60)
print("TEST 5: ML-KEM-768 is actually being used (ciphertext size check)")

vault5, tmp5 = make_temp_vault()
try:
    encrypted5 = vault5.encrypt_entry(SAMPLE_ENTRY)
    record5 = json.loads(encrypted5)

    kem_ct_bytes = base64.b64decode(record5["kem_ciphertext"])
    actual_len = len(kem_ct_bytes)

    assert actual_len == MLKEM768_CIPHERTEXT_SIZE, (
        f"FAIL: kem_ciphertext is {actual_len} bytes, expected {MLKEM768_CIPHERTEXT_SIZE} "
        f"(ML-KEM-768 standard). The vault may have silently degraded to a weaker scheme!"
    )
    print(f"  PASS: kem_ciphertext is {actual_len} bytes == ML-KEM-768 spec (1088 bytes)")

    # Also verify the eph_x25519_pub is 32 bytes (X25519 raw pubkey size)
    eph_pub_bytes = base64.b64decode(record5["eph_x25519_pub"])
    assert len(eph_pub_bytes) == 32, (
        f"FAIL: eph_x25519_pub is {len(eph_pub_bytes)} bytes, expected 32 (X25519 raw pubkey)"
    )
    print(f"  PASS: eph_x25519_pub is {len(eph_pub_bytes)} bytes == X25519 spec (32 bytes)")
    print(f"  PASS: MLKEM768_CIPHERTEXT_SIZE constant = {MLKEM768_CIPHERTEXT_SIZE} (asserted inside encrypt_entry too)")
finally:
    shutil.rmtree(tmp5)


# ---------------------------------------------------------------------------
# Test 6 (bonus): store_entry -> read_entry end-to-end round-trip
# ---------------------------------------------------------------------------
print("=" * 60)
print("TEST 6: store_entry -> read_entry end-to-end round-trip")

# Clean store for this test
for p in (VAULT_STORE_PATH, VAULT_INDEX_PATH):
    if os.path.exists(p):
        os.remove(p)

vault6, tmp6 = make_temp_vault()
try:
    rid = vault6.store_entry(SAMPLE_ENTRY)
    assert isinstance(rid, str) and len(rid) == 32, (
        f"FAIL: record_id should be a 32-char hex string, got: {rid!r}"
    )
    retrieved = vault6.read_entry(rid)
    assert retrieved == SAMPLE_ENTRY, (
        f"Round-trip via store/read failed.\n  Expected: {SAMPLE_ENTRY}\n  Got: {retrieved}"
    )
    print(f"  PASS: store_entry returned record_id={rid[:8]}... (truncated)")
    print("  PASS: read_entry returned the exact original dict")
finally:
    shutil.rmtree(tmp6)
    for p in (VAULT_STORE_PATH, VAULT_INDEX_PATH):
        if os.path.exists(p):
            os.remove(p)
    # Final restore of original store/index
    for p, bak in ((VAULT_STORE_PATH, _store_backup), (VAULT_INDEX_PATH, _index_backup)):
        if bak is not None:
            with open(p, "wb") as f:
                f.write(bak)


print()
print("=" * 60)
print("All vault tests passed.")
