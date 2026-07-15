"""
FastAPI endpoint for real-time risk scoring.
Wraps the predict.py logic into a web service.

Usage:
    uvicorn api:app --reload

Test it:
    curl -X POST http://127.0.0.1:8000/score \
         -H "Content-Type: application/json" \
         -d '{"user":"CCA0046", "logon_count":5, "off_hours_events":10}'
"""

import datetime
import sys
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Extra
from typing import Optional, List, Dict, Any

from src.predict import RiskPredictor
from src.config import VAULT_AUDIT_RISK_TIERS
from src.vault import HybridVault, VaultDecryptionError, VaultRecordNotFoundError

app = FastAPI(
    title="FinSpark Risk Engine API",
    description="Real-time insider threat detection and risk scoring.",
    version="1.0.0"
)

# Load the model bundle once on startup
try:
    predictor = RiskPredictor("models/model_v1.pkl")
except Exception as e:
    print(f"Warning: Could not load model bundle. Is models/model_v1.pkl present? Error: {e}")
    predictor = None

# Instantiate the quantum-safe audit vault once at startup.
# Long-term keypairs are generated on first run and reloaded on subsequent runs.
vault = HybridVault(key_dir="vault_keys")


# Define the expected JSON payload for a scoring request.
# Users must provide at least a 'user' ID. All other features are optional
# (the model pipeline will safely fill missing features with 0).
class ScoreRequest(BaseModel):
    user: str
    day: Optional[str] = None
    
    # Core anomaly features
    logon_count: Optional[int] = 0
    off_hours_events: Optional[int] = 0
    unique_pcs: Optional[int] = 0
    device_connects: Optional[int] = 0
    device_off_hours: Optional[int] = 0
    file_events: Optional[int] = 0
    removable_file_events: Optional[int] = 0
    email_count: Optional[int] = 0
    external_email_count: Optional[int] = 0
    suspicious_url_events: Optional[int] = 0

    class Config:
        # Allow extra fields (like 'role' or 'department') to be passed in
        # without throwing an error, in case the frontend sends a giant payload.
        extra = Extra.allow


@app.get("/health")
def health_check():
    """Simple health check to verify the API is running."""
    return {
        "status": "healthy",
        "model_loaded": predictor is not None,
        "model_version": predictor.version if predictor else None
    }


@app.get("/", response_class=HTMLResponse)
def get_ui():
    """Returns a beautiful Web UI for demoing the risk engine to judges."""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>FinSpark Risk Engine</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
        <style>
            body { font-family: 'Inter', sans-serif; background: #0f172a; color: #f8fafc; }
            .glass { background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.1); }
            .glow-red { box-shadow: 0 0 20px rgba(239, 68, 68, 0.5); }
            .glow-green { box-shadow: 0 0 20px rgba(34, 197, 94, 0.5); }
        </style>
    </head>
    <body class="min-h-screen p-8">
        <div class="max-w-5xl mx-auto">
            <header class="mb-10 text-center">
                <h1 class="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-emerald-400">FinSpark Risk Engine</h1>
                <p class="text-slate-400 mt-2">Real-time Insider Threat Detection</p>
            </header>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
                <!-- Input Panel -->
                <div class="glass p-6 rounded-2xl">
                    <h2 class="text-xl font-semibold mb-4">Analyze User Activity</h2>
                    
                    <div class="flex gap-2 mb-6">
                        <button onclick="loadDemo('CCA0046', 5, 10, 24, 8)" class="text-xs bg-slate-700 hover:bg-slate-600 px-3 py-1 rounded transition">Demo: Critical Threat</button>
                        <button onclick="loadDemo('BAL0044', 1, 0, 0, 0)" class="text-xs bg-slate-700 hover:bg-slate-600 px-3 py-1 rounded transition">Demo: Normal User</button>
                    </div>

                    <div class="space-y-4">
                        <div><label class="text-sm text-slate-400">User ID</label><input id="f_user" type="text" class="w-full bg-slate-800 rounded p-2 text-white border border-slate-700 focus:border-blue-500 outline-none" value="CCA0046"></div>
                        <div class="grid grid-cols-2 gap-4">
                            <div><label class="text-sm text-slate-400">Logon Count</label><input id="f_logon" type="number" class="w-full bg-slate-800 rounded p-2 text-white border border-slate-700" value="0"></div>
                            <div><label class="text-sm text-slate-400">Off-Hours Events</label><input id="f_offhours" type="number" class="w-full bg-slate-800 rounded p-2 text-white border border-slate-700" value="0"></div>
                            <div><label class="text-sm text-slate-400">Suspicious URLs</label><input id="f_urls" type="number" class="w-full bg-slate-800 rounded p-2 text-white border border-slate-700" value="0"></div>
                            <div><label class="text-sm text-slate-400">External Emails</label><input id="f_emails" type="number" class="w-full bg-slate-800 rounded p-2 text-white border border-slate-700" value="0"></div>
                        </div>
                        <button onclick="analyzeRisk()" class="w-full mt-4 bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-400 hover:to-blue-500 py-3 rounded-lg font-semibold shadow-lg transition transform hover:-translate-y-0.5">Run Analysis</button>
                    </div>
                </div>

                <!-- Results Panel -->
                <div class="glass p-6 rounded-2xl flex flex-col items-center justify-center min-h-[400px]" id="result-panel">
                    <div class="text-slate-500 text-center" id="empty-state">
                        <svg class="w-16 h-16 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"></path></svg>
                        <p>Run an analysis to see risk insights</p>
                    </div>
                    
                    <div id="results" class="w-full hidden">
                        <div class="text-center mb-6">
                            <h3 class="text-sm text-slate-400 uppercase tracking-widest">Risk Score</h3>
                            <div class="text-6xl font-bold my-2" id="res-score">--</div>
                            <span id="res-tier" class="px-4 py-1 rounded-full text-sm font-semibold uppercase tracking-wider">--</span>
                        </div>
                        
                        <div class="bg-slate-800/50 p-4 rounded-lg border border-slate-700/50 mb-4">
                            <h4 class="text-sm font-semibold text-slate-300 mb-2">Narrative Explanation</h4>
                            <p id="res-narrative" class="text-sm text-slate-300 leading-relaxed"></p>
                        </div>

                        <div class="bg-slate-800/50 p-4 rounded-lg border border-slate-700/50 mb-4">
                            <h4 class="text-sm font-semibold text-slate-300 mb-2">Recommended Actions</h4>
                            <ul id="res-actions" class="text-sm text-slate-300 list-disc list-inside"></ul>
                        </div>

                        <div id="audit-badge" class="hidden bg-indigo-900/40 border border-indigo-500/40 p-3 rounded-lg text-xs text-indigo-300 flex items-start gap-2">
                            <span class="text-base leading-none mt-0.5">&#128274;</span>
                            <span>
                                <strong class="text-indigo-200">Audit entry encrypted</strong>
                                (hybrid: X25519 + ML-KEM-768)<br>
                                Record ID: <code id="audit-record-id" class="font-mono text-indigo-100 text-xs"></code>
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            function loadDemo(user, logon, offhours, urls, emails) {
                document.getElementById('f_user').value = user;
                document.getElementById('f_logon').value = logon;
                document.getElementById('f_offhours').value = offhours;
                document.getElementById('f_urls').value = urls;
                document.getElementById('f_emails').value = emails;
            }

            async function analyzeRisk() {
                const payload = {
                    user: document.getElementById('f_user').value,
                    logon_count: parseInt(document.getElementById('f_logon').value),
                    off_hours_events: parseInt(document.getElementById('f_offhours').value),
                    suspicious_url_events: parseInt(document.getElementById('f_urls').value),
                    external_email_count: parseInt(document.getElementById('f_emails').value)
                };

                const res = await fetch('/score', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();

                document.getElementById('empty-state').classList.add('hidden');
                document.getElementById('results').classList.remove('hidden');
                
                document.getElementById('res-score').innerText = data.risk_score.toFixed(1);
                document.getElementById('res-narrative').innerText = data.narrative_explanation;
                
                const tierEl = document.getElementById('res-tier');
                const panelEl = document.getElementById('result-panel');
                tierEl.innerText = data.risk_tier;
                
                panelEl.classList.remove('glow-red', 'glow-green');
                if (data.risk_tier === 'Critical' || data.risk_tier === 'High') {
                    tierEl.className = 'px-4 py-1 rounded-full text-sm font-semibold uppercase tracking-wider bg-red-500/20 text-red-400 border border-red-500/30';
                    panelEl.classList.add('glow-red');
                } else {
                    tierEl.className = 'px-4 py-1 rounded-full text-sm font-semibold uppercase tracking-wider bg-green-500/20 text-green-400 border border-green-500/30';
                    panelEl.classList.add('glow-green');
                }

                const actionsUl = document.getElementById('res-actions');
                actionsUl.innerHTML = '';
                if (data.recommended_actions.length > 0) {
                    data.recommended_actions.forEach(action => {
                        const li = document.createElement('li');
                        li.innerText = action.replace(/_/g, ' ').toUpperCase();
                        actionsUl.appendChild(li);
                    });
                } else {
                    actionsUl.innerHTML = '<li class="text-slate-500">No strict actions required</li>';
                }

                // Show audit badge for High/Critical results
                const auditBadge = document.getElementById('audit-badge');
                if (data.audit_record_id) {
                    document.getElementById('audit-record-id').innerText = data.audit_record_id;
                    auditBadge.classList.remove('hidden');
                } else {
                    auditBadge.classList.add('hidden');
                }
            }
        </script>
    </body>
    </html>
    """



@app.post("/score")
def score_user_activity(request: ScoreRequest):
    """
    Score a single user's daily activity in real-time.
    Returns the risk score, risk tier, and human-readable explanations.
    """
    if predictor is None:
        raise HTTPException(status_code=503, detail="Risk Engine model is not loaded.")

    try:
        # Convert the Pydantic model to a standard dictionary
        row_dict = request.dict()
        
        # Call the exact same score_row() function we use in the CLI
        result = predictor.score_row(row_dict)
        
        # Add risk-based access control recommendations based on the tier
        tier = result["risk_tier"]
        if tier == "Critical":
            result["recommended_actions"] = ["require_mfa", "restrict_removable_media", "alert_soc_immediately"]
        elif tier == "High":
            result["recommended_actions"] = ["require_mfa", "log_enhanced"]
        elif tier == "Medium":
            result["recommended_actions"] = ["log_standard"]
        else:
            result["recommended_actions"] = []

        # Generate a normal text explanation
        if result.get("top_signals"):
            reasons = [s["label"] for s in result["top_signals"]]
            reasons_str = ", and ".join(reasons) if len(reasons) <= 2 else ", ".join(reasons[:-1]) + ", and " + reasons[-1]
            result["narrative_explanation"] = (
                f"User {result['user']} was flagged as a {tier} risk (Score: {result['risk_score']:.1f}/100). "
                f"This is primarily because they had {reasons_str}."
            )
        else:
            result["narrative_explanation"] = (
                f"User {result['user']} is currently a {tier} risk (Score: {result['risk_score']:.1f}/100). "
                f"Their activity aligns with their normal historical baseline."
            )

        # Encrypt and store an audit record for High/Critical risk events.
        # The returned record_id is added to the response for demo verification.
        if tier in VAULT_AUDIT_RISK_TIERS:
            audit_entry = {
                "user_id": result["user"],
                "risk_tier": tier,
                "action_taken": result["recommended_actions"],
                "explanation": result["narrative_explanation"],
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "session_id": row_dict.get("day") or "live-request",
            }
            record_id = vault.store_entry(audit_entry)
            result["audit_record_id"] = record_id
        else:
            result["audit_record_id"] = None

        return result

    except VaultDecryptionError as e:
        # Vault failures must never be silently hidden — raise a specific 503
        # so it's clear the scoring succeeded but the audit store failed.
        raise HTTPException(status_code=503, detail=f"Vault storage failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scoring failed: {str(e)}")


@app.get("/vault/{record_id}")
def read_vault_entry(record_id: str):
    """
    Retrieve and decrypt a vault audit record by its record_id.
    Returns the original plaintext audit entry for demo/verification purposes.
    Only records for High and Critical risk events are stored.
    """
    try:
        entry = vault.read_entry(record_id)
        return {"record_id": record_id, "audit_entry": entry}
    except VaultRecordNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except VaultDecryptionError as exc:
        raise HTTPException(status_code=500, detail=f"Vault decryption failed: {exc}")
