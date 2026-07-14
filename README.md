# FinSpark: Privileged Access Misuse & Insider Threat Detection

FinSpark is an AI-driven behavioral analysis engine designed to detect misuse of privileged accounts and identify insider threats in real-time. This prototype was built to fulfill the **Privileged Access Misuse & Insider Threat Detection** problem statement.

## 🌟 Key Features

- **Hybrid AI Risk Engine**: Uses a robust ensemble of Unsupervised Learning (Isolation Forest) and Supervised Learning (Random Forest) to catch both sudden anomalies and slow-burn data exfiltration.
- **Explainable AI (XAI)**: Generates human-readable narrative explanations for why a user was flagged, breaking down exact feature deviations (z-scores) from their normal historical baseline.
- **Real-Time Detection API**: A lightning-fast FastAPI backend that scores user activity on the fly.
- **Risk-Based Access Control**: Automatically recommends security actions (e.g., `require_mfa`, `restrict_removable_media`) based on the dynamically calculated risk tier (Low, Medium, High, Critical).
- **Interactive Web Dashboard**: A built-in modern UI to analyze users and visualize threat intelligence instantly.

## 🚀 Tech Stack
- **Machine Learning**: `scikit-learn`, `pandas`, `numpy`, `joblib`
- **Backend API**: `FastAPI`, `uvicorn`, `pydantic`
- **Frontend UI**: HTML5, Tailwind CSS (Dark Mode/Glassmorphism)

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
      ├── src/                  # Source code
      ├── models/               # Pre-trained model bundle
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
