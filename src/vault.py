"""
Quantum-safe audit vault.

Implements genuine hybrid encryption combining:
  - X25519  (classical KEM)          — protects against current threats
  - ML-KEM-768  (post-quantum KEM)   — protects against future quantum attacks
  - HKDF (SHA-256)                   — combines both secrets into one 32-byte key
  - AES-256-GCM                      — authenticated encryption of the payload

Security property: an attacker must break BOTH X25519 AND ML-KEM-768 to recover
any audit record.  One algorithm being broken does not compromise the other
(this is the real "hybrid" guarantee, not just two independent encryption layers).

Encryption layout for one stored record (all base64 in a single JSON line):
    {
        "eph_x25519_pub": <32 bytes base64>,   # ephemeral X25519 pubkey
        "kem_ciphertext": <1088 bytes base64>, # ML-KEM-768 ciphertext
        "nonce":          <12 bytes base64>,   # AES-GCM nonce (random per record)
        "ciphertext":     <N bytes base64>     # AES-256-GCM authenticated ciphertext
    }

Key files (vault_keys/ directory, gitignored, generated once on first run):
    x25519_private.pem    — long-term X25519 private key
    x25519_public.pem     — long-term X25519 public key
    mlkem768_private.der  — long-term ML-KEM-768 private key (PKCS8 DER)
    mlkem768_public.der   — long-term ML-KEM-768 public key  (SPKI DER)

Runtime files (repo root, gitignored):
    vault_store.jsonl  — append-only JSONL of encrypted audit records
    vault_index.json   — {record_id: line_number} index for O(1) lookup
"""

import base64
import json
import os
import uuid

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.mlkem import (
    MLKEM768PrivateKey,
    MLKEM768PublicKey,
)
from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
    load_der_private_key,
    load_der_public_key,
)

# ML-KEM-768 ciphertext is exactly 1088 bytes.
# We assert this in encrypt_entry so tests can verify the real algorithm is running.
MLKEM768_CIPHERTEXT_SIZE = 1088

# HKDF info string for domain separation.
_HKDF_INFO = b"hybrid-kem-audit-vault-v1"

# Paths relative to the repo root (where the API process runs from).
VAULT_STORE_PATH = "vault_store.jsonl"
VAULT_INDEX_PATH = "vault_index.json"


class VaultDecryptionError(Exception):
    """Raised when an audit record cannot be authenticated or decrypted."""


class VaultRecordNotFoundError(KeyError):
    """Raised when a record_id is not present in the vault index."""


class HybridVault:
    """
    Quantum-safe audit vault.  Instantiate once at application startup.

    Parameters
    ----------
    key_dir : str
        Directory where long-term keypairs are stored (and generated if absent).
        Created automatically if it does not exist.
    """

    def __init__(self, key_dir: str = "vault_keys"):
        self._key_dir = key_dir
        os.makedirs(key_dir, exist_ok=True)
        self._x25519_priv, self._x25519_pub = self._load_or_generate_x25519()
        self._mlkem_priv, self._mlkem_pub = self._load_or_generate_mlkem()

    # ------------------------------------------------------------------
    # Key persistence helpers
    # ------------------------------------------------------------------

    def _x25519_priv_path(self) -> str:
        return os.path.join(self._key_dir, "x25519_private.pem")

    def _x25519_pub_path(self) -> str:
        return os.path.join(self._key_dir, "x25519_public.pem")

    def _mlkem_priv_path(self) -> str:
        return os.path.join(self._key_dir, "mlkem768_private.der")

    def _mlkem_pub_path(self) -> str:
        return os.path.join(self._key_dir, "mlkem768_public.der")

    def _load_or_generate_x25519(self):
        priv_path = self._x25519_priv_path()
        pub_path = self._x25519_pub_path()
        if os.path.exists(priv_path) and os.path.exists(pub_path):
            with open(priv_path, "rb") as f:
                priv = serialization.load_pem_private_key(f.read(), password=None)
            with open(pub_path, "rb") as f:
                pub = serialization.load_pem_public_key(f.read())
        else:
            priv = X25519PrivateKey.generate()
            pub = priv.public_key()
            with open(priv_path, "wb") as f:
                f.write(
                    priv.private_bytes(
                        Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()
                    )
                )
            with open(pub_path, "wb") as f:
                f.write(pub.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo))
            print(f"[vault] Generated new X25519 keypair -> {self._key_dir}/")
        return priv, pub

    def _load_or_generate_mlkem(self):
        priv_path = self._mlkem_priv_path()
        pub_path = self._mlkem_pub_path()
        if os.path.exists(priv_path) and os.path.exists(pub_path):
            with open(priv_path, "rb") as f:
                priv = load_der_private_key(f.read(), password=None)
            with open(pub_path, "rb") as f:
                pub = load_der_public_key(f.read())
        else:
            priv = MLKEM768PrivateKey.generate()
            pub = priv.public_key()
            with open(priv_path, "wb") as f:
                f.write(priv.private_bytes(Encoding.DER, PrivateFormat.PKCS8, NoEncryption()))
            with open(pub_path, "wb") as f:
                f.write(pub.public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo))
            print(f"[vault] Generated new ML-KEM-768 keypair -> {self._key_dir}/")
        return priv, pub

    # ------------------------------------------------------------------
    # Core crypto: key derivation
    # ------------------------------------------------------------------

    def _derive_key(self, classical_secret: bytes, pq_secret: bytes) -> bytes:
        """
        Combine classical + post-quantum secrets via HKDF-SHA256 into one
        32-byte AES key.  Both secrets must be compromised to recover this key.
        """
        return HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=_HKDF_INFO,
            backend=default_backend(),
        ).derive(classical_secret + pq_secret)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def encrypt_entry(self, entry: dict) -> str:
        """
        Hybrid-encrypt a single audit entry dict and return it as a compact
        JSON string (one base64-encoded field per component).

        The caller must NOT store the returned string directly as JSON inside
        another JSON object — store_entry() handles appending it as one line
        to vault_store.jsonl.
        """
        plaintext = json.dumps(entry, separators=(",", ":"), ensure_ascii=False).encode()

        # Step a: ephemeral X25519 keypair
        eph_priv = X25519PrivateKey.generate()
        eph_pub = eph_priv.public_key()

        # Step b: classical KEM — X25519 ECDH with vault's long-term public key
        classical_secret = eph_priv.exchange(self._x25519_pub)

        # Step c: post-quantum KEM — ML-KEM-768 encapsulation
        # encapsulate() returns (shared_key, ciphertext) — note the order!
        pq_secret, kem_ciphertext = self._mlkem_pub.encapsulate()
        assert len(kem_ciphertext) == MLKEM768_CIPHERTEXT_SIZE, (
            f"ML-KEM-768 ciphertext is {len(kem_ciphertext)} bytes, expected "
            f"{MLKEM768_CIPHERTEXT_SIZE}.  This is a critical crypto error."
        )

        # Step d: HKDF — combine both secrets into one 32-byte symmetric key
        aes_key = self._derive_key(classical_secret, pq_secret)

        # Step e: AES-256-GCM authenticated encryption
        nonce = os.urandom(12)
        ciphertext = AESGCM(aes_key).encrypt(nonce, plaintext, None)

        # Step f: serialize all components as a single compact JSON record
        record = {
            "eph_x25519_pub": base64.b64encode(
                eph_pub.public_bytes(Encoding.Raw, PublicFormat.Raw)
            ).decode(),
            "kem_ciphertext": base64.b64encode(kem_ciphertext).decode(),
            "nonce": base64.b64encode(nonce).decode(),
            "ciphertext": base64.b64encode(ciphertext).decode(),
        }
        return json.dumps(record, separators=(",", ":"))

    def decrypt_entry(self, record: str) -> dict:
        """
        Decrypt and authenticate a record string produced by encrypt_entry().

        Raises
        ------
        VaultDecryptionError
            If the record is malformed, authentication fails (tampered), or
            any decryption step fails.
        """
        try:
            parts = json.loads(record)
            eph_pub_bytes = base64.b64decode(parts["eph_x25519_pub"])
            kem_ciphertext = base64.b64decode(parts["kem_ciphertext"])
            nonce = base64.b64decode(parts["nonce"])
            ciphertext = base64.b64decode(parts["ciphertext"])
        except (KeyError, ValueError, json.JSONDecodeError) as exc:
            raise VaultDecryptionError(f"Malformed vault record: {exc}") from exc

        try:
            # Reverse step b: recover classical secret using vault's long-term private key
            eph_pub = X25519PublicKey.from_public_bytes(eph_pub_bytes)
            classical_secret = self._x25519_priv.exchange(eph_pub)

            # Reverse step c: ML-KEM-768 decapsulation recovers the PQ shared secret
            pq_secret = self._mlkem_priv.decapsulate(kem_ciphertext)

            # Reverse step d: re-derive the same AES key
            aes_key = self._derive_key(classical_secret, pq_secret)

            # Reverse step e: AES-256-GCM decrypt + authenticate
            # InvalidTag is raised here if ANY byte was tampered with
            plaintext = AESGCM(aes_key).decrypt(nonce, ciphertext, None)
        except VaultDecryptionError:
            raise
        except Exception as exc:
            raise VaultDecryptionError(
                f"Decryption or authentication failed (record may be tampered): {exc}"
            ) from exc

        try:
            return json.loads(plaintext.decode())
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise VaultDecryptionError(f"Decrypted payload is not valid JSON: {exc}") from exc

    def store_entry(self, entry: dict) -> str:
        """
        Encrypt entry and append it to vault_store.jsonl.
        Updates vault_index.json with {record_id: line_number}.
        Returns the record_id (uuid4 hex string).
        """
        encrypted_line = self.encrypt_entry(entry)
        record_id = uuid.uuid4().hex

        # Determine which 1-indexed line this will be written to
        # (we count existing lines first, then append)
        try:
            with open(VAULT_STORE_PATH, "r", encoding="utf-8") as f:
                existing_lines = sum(1 for line in f if line.strip())
        except FileNotFoundError:
            existing_lines = 0
        line_number = existing_lines + 1  # 1-indexed

        # Append the encrypted record
        with open(VAULT_STORE_PATH, "a", encoding="utf-8") as f:
            f.write(encrypted_line + "\n")

        # Update the index
        index = self._load_index()
        index[record_id] = line_number
        with open(VAULT_INDEX_PATH, "w", encoding="utf-8") as f:
            json.dump(index, f, separators=(",", ":"))

        return record_id

    def read_entry(self, record_id: str) -> dict:
        """
        Look up record_id in the index, read that line from vault_store.jsonl,
        and return the decrypted audit entry dict.

        Raises
        ------
        VaultRecordNotFoundError
            If record_id is not in the index.
        VaultDecryptionError
            If the stored record fails authentication or decryption.
        """
        index = self._load_index()
        if record_id not in index:
            raise VaultRecordNotFoundError(
                f"No vault record found for record_id='{record_id}'. "
                "It may not exist or the index may be out of sync."
            )

        line_number = index[record_id]  # 1-indexed

        try:
            with open(VAULT_STORE_PATH, "r", encoding="utf-8") as f:
                for current_line_num, line in enumerate(f, start=1):
                    if current_line_num == line_number:
                        return self.decrypt_entry(line.strip())
        except FileNotFoundError:
            raise VaultDecryptionError(
                f"vault_store.jsonl not found — cannot read record '{record_id}'."
            )

        raise VaultDecryptionError(
            f"Record '{record_id}' is indexed at line {line_number} but the "
            "vault store file does not have that many lines."
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_index(self) -> dict:
        try:
            with open(VAULT_INDEX_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
