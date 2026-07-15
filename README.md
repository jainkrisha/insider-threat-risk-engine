# FinSpark: Privileged Access Misuse & Insider Threat Detection

FinSpark is an AI-driven behavioral analysis engine designed to detect misuse of privileged accounts and identify insider threats in real-time. This prototype was built to fulfill the **Privileged Access Misuse & Insider Threat Detection** problem statement.

## Key Features

- **Hybrid AI Risk Engine**: Uses a robust ensemble of Unsupervised Learning (Isolation Forest) and Supervised Learning (Random Forest) to catch both sudden anomalies and slow-burn data exfiltration.
- **Explainable AI (XAI)**: Generates human-readable narrative explanations for why a user was flagged, breaking down exact feature deviations (z-scores) from their normal historical baseline. The engine precisely differentiates between sudden, anomalous spikes in activity and sharp, suspicious drops.
- **Real-Time Detection API**: A lightning-fast FastAPI backend that scores user activity on the fly.
- **Risk-Based Access Control**: Automatically recommends security actions (e.g., `require_mfa`, `restrict_removable_media`) based on the dynamically calculated risk tier (Low, Medium, High, Critical).
- **Interactive Web Dashboard**: A built-in modern UI to analyze users and visualize threat intelligence instantly.
- **Quantum-safe audit vault (hybrid X25519 + ML-KEM-768)**: Every High/Critical risk action is encrypted using a genuine hybrid classical + post-quantum KEM before being stored — and can be decrypted on demand for live demo verification.

## 🚀 Tech Stack
- **Machine Learning**: `scikit-learn`, `pandas`, `numpy`, `joblib`
- **Backend API**: `FastAPI`, `uvicorn`, `pydantic`
- **Frontend UI**: HTML5, Tailwind CSS (Dark Mode/Glassmorphism)
- **Cryptography**: `pyca/cryptography` 48+ (ML-KEM-768, X25519, AES-256-GCM) — hybrid classical + post-quantum encryption for audit logs, requires OpenSSL 3.5+.

---

## ⚙️ Setup & Installation

### 1. Clone the repository
```bash
git clone https://github.com/jainkrisha/insider-threat-risk-engine.git
cd insider-threat-risk-engine
```

### 2. Install Dependencies
Ensure you have Python 3.9+ installed, then run:
```bash
pip install -r requirements.txt
```

### 3. Download the Dataset
Because the raw CERT r4.2 dataset and generated feature tables are very large (15GB+), they are not hosted on GitHub.
1. Download the data from our [Google Drive Link](https://drive.google.com/drive/folders/1bOf72HOXVrsE6FwEVgyYv4tnBdLnCXTn?usp=sharing).
2. Extract the files and place them in the root directory so your folder structure looks like this:
   ```text
   Finspark/
      ├── data/                 # Raw CERT data (http.csv, email.csv, etc.)
      ├── features.csv          # 34MB generated feature table
      ├── features_baseline.csv # 64MB historical baselines
      ├── src/
      │   ├── vault.py          # Quantum-safe hybrid audit vault (X25519 + ML-KEM-768)
      │   └── ...               # Other source modules
      ├── models/               # Pre-trained model bundle
      ├── test_vault.py         # Vault unit tests
      ├── vault_keys/           # [gitignored] Long-term X25519 + ML-KEM-768 keypairs
      ├── vault_store.jsonl     # [gitignored] Append-only encrypted audit log
      ├── vault_index.json      # [gitignored] record_id -> line-number lookup index
      └── api.py                # FastAPI app
   ```

---

## 🎯 How to Run the Prototype

### The Interactive Web Dashboard (Recommended)
We built a beautiful, real-time web dashboard directly into the API for easy demonstration.

1. **Start the server:**
   ```bash
   uvicorn api:app --reload
   ```
2. **Open the Dashboard:**
   Go to **http://127.0.0.1:8000/** in your web browser.
3. **Run an Analysis:**
   Click the "Demo: Critical Threat" button and click "Run Analysis" to see the engine detect a malicious user, explain exactly why they were flagged, and recommend access control actions.

### The Developer API (Swagger UI)
If you want to test the raw JSON endpoint:
1. Ensure the server is running (`uvicorn api:app --reload`).
2. Go to **http://127.0.0.1:8000/docs**.
3. Use the interactive Swagger UI to send `POST` requests to the `/score` endpoint.

### The CLI Demo
If you prefer the command line, you can run the terminal demo script:
```bash
python demo.py
```

---

## 🧠 Model Architecture

The Risk Engine (`src/train.py` and `src/predict.py`) processes 15 behavioral features per user, per day. 
1. **Isolation Forest (60% weight)**: Learns what "normal" looks like and flags anomalous days based on z-score deviations from the user's personal baseline.
2. **Random Forest (40% weight)**: Trained on known malicious signatures to catch specific threat scenarios (like Scenario 2: slow exfiltration).
3. **Composite Aggregation**: Scores are aggregated across a time window (max score, mean score, and frequency of high-risk days) to ensure slow-burn threats are caught just as effectively as sudden spikes.

**Evaluation:** On a held-out test window of 937 users, the model successfully caught **47 out of 48** malicious users within the Top-100 riskiest profiles (F1 Score: 0.635).

---

## 🔒 Quantum-Safe Audit Vault

Every High or Critical risk event triggers an encrypted audit entry stored in `vault_store.jsonl`. The encryption uses a **genuine hybrid KEM combiner** — the same pattern Chrome and Cloudflare use for post-quantum TLS.

### Why hybrid?

A purely classical scheme (e.g. ECDH alone) becomes vulnerable once a large quantum computer is available — a "harvest now, decrypt later" attacker could record today's ciphertext and decrypt it years from now. A purely post-quantum scheme is newer and less battle-tested against classical attacks.

Hybrid encryption solves both:
1. **X25519** (classical ECDH) — extremely well-studied, fast, currently unbroken
2. **ML-KEM-768** (NIST FIPS 203 standard) — quantum-resistant, lattice-based
3. **HKDF-SHA256** combines both shared secrets into one 32-byte AES key — an attacker must break **both** algorithms to recover any key
4. **AES-256-GCM** encrypts the audit payload with authenticated encryption (tamper-evident)

### How it works per record

```
Encrypt:
  1. Generate fresh ephemeral X25519 keypair
  2. ECDH(ephemeral_priv, vault_x25519_pub) → classical_secret
  3. ML-KEM-768.Encapsulate(vault_mlkem_pub) → (pq_secret, kem_ciphertext)
  4. HKDF(classical_secret || pq_secret) → 32-byte AES key
  5. AES-256-GCM.Encrypt(key, audit_json) → ciphertext
  6. Store: {eph_x25519_pub, kem_ciphertext, nonce, ciphertext} as one JSONL line

Decrypt:
  Reverse steps 5→1 using vault's stored long-term private keys
```

### Live demo verification

After running a High/Critical analysis in the dashboard, a record ID appears. You can verify the audit entry was genuinely stored and can be decrypted:

```bash
curl http://127.0.0.1:8000/vault/<record_id>
```
