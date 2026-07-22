"""
FastAPI endpoint for real-time risk scoring.
Wraps the predict.py logic into a web service.

Usage:
    uvicorn api:app --reload

Test it:
    curl -X POST http://127.0.0.1:8000/score \
         -H "Content-Type: application/json" \
         -H "X-API-Key: demo-Vigil-key" \
         -d '{"user":"CCA0046", "logon_count":5, "off_hours_events":10}'
"""

import datetime
import os
import sys
from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security.api_key import APIKeyHeader
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Extra
from typing import Optional, List, Dict, Any

sys.path.insert(0, "src")
from src.predict import RiskPredictor
from src.config import VAULT_AUDIT_RISK_TIERS, PRIVILEGE_TIERS, PRIVILEGE_ACTIONS, HNDL_ACTIONS
from src.vault import HybridVault, VaultDecryptionError, VaultRecordNotFoundError

app = FastAPI(
    title="Vigil Risk Engine API",
    description="Real-time insider threat detection and risk scoring.",
    version="1.0.0"
)

# ---------------------------------------------------------------------------
# API Key Authentication
# ---------------------------------------------------------------------------
# Key is read from env var VIGIL_API_KEY. Falls back to the demo key so
# the demo works out-of-the-box without any configuration.
_DEMO_KEY = "demo-Vigil-key"
API_KEY = os.environ.get("VIGIL_API_KEY", _DEMO_KEY)
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(key: str = Security(_api_key_header)):
    """FastAPI dependency — rejects requests that don't supply the correct key."""
    if key != API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid or missing API key. Supply X-API-Key header."
        )
    return key


# ---------------------------------------------------------------------------
# 7-day demo trend data (pre-computed, illustrative)
# ---------------------------------------------------------------------------
# Keyed by user ID.  Each entry is a list of 7 dicts: one per day (D-6 to D-0).
# CCA0046 : escalating spike (insider exfiltration building up)
# MAS0025 : slow-burn climb (Scenario 2 style)
# BAL0044 : flat / normal
_TREND_DATA: Dict[str, List[Dict[str, Any]]] = {
    "CCA0046": [
        {"day": -6, "risk_score": 28.4, "risk_tier": "Low"},
        {"day": -5, "risk_score": 34.1, "risk_tier": "Low"},
        {"day": -4, "risk_score": 41.7, "risk_tier": "Medium"},
        {"day": -3, "risk_score": 55.2, "risk_tier": "Medium"},
        {"day": -2, "risk_score": 68.9, "risk_tier": "High"},
        {"day": -1, "risk_score": 79.3, "risk_tier": "High"},
        {"day":  0, "risk_score": 94.7, "risk_tier": "Critical"},
    ],
    "MAS0025": [
        {"day": -6, "risk_score": 38.2, "risk_tier": "Low"},
        {"day": -5, "risk_score": 44.5, "risk_tier": "Medium"},
        {"day": -4, "risk_score": 49.1, "risk_tier": "Medium"},
        {"day": -3, "risk_score": 53.8, "risk_tier": "Medium"},
        {"day": -2, "risk_score": 59.4, "risk_tier": "Medium"},
        {"day": -1, "risk_score": 65.0, "risk_tier": "Medium"},
        {"day":  0, "risk_score": 72.1, "risk_tier": "High"},
    ],
    "BAL0044": [
        {"day": -6, "risk_score": 12.1, "risk_tier": "Low"},
        {"day": -5, "risk_score": 9.8,  "risk_tier": "Low"},
        {"day": -4, "risk_score": 14.3, "risk_tier": "Low"},
        {"day": -3, "risk_score": 11.5, "risk_tier": "Low"},
        {"day": -2, "risk_score": 10.2, "risk_tier": "Low"},
        {"day": -1, "risk_score": 13.7, "risk_tier": "Low"},
        {"day":  0, "risk_score": 8.9,  "risk_tier": "Low"},
    ],
    "SYSADM01": [
        {"day": -6, "risk_score": 22.3, "risk_tier": "Low"},
        {"day": -5, "risk_score": 26.1, "risk_tier": "Low"},
        {"day": -4, "risk_score": 31.4, "risk_tier": "Low"},
        {"day": -3, "risk_score": 58.7, "risk_tier": "Medium"},
        {"day": -2, "risk_score": 72.9, "risk_tier": "High"},
        {"day": -1, "risk_score": 80.5, "risk_tier": "High"},
        {"day":  0, "risk_score": 88.2, "risk_tier": "High"},
    ],
}

# Load the model bundle once on startup
try:
    predictor = RiskPredictor("models/model_v1.pkl")
except Exception as e:
    print(f"Warning: Could not load model bundle. Is models/model_v1.pkl present? Error: {e}")
    predictor = None

# Instantiate the quantum-safe audit vault once at startup.
# Long-term keypairs are generated on first run and reloaded on subsequent runs.
vault = HybridVault(key_dir="vault_keys")

# Global in-memory state tracking for user sessions and automatic enforcement
SESSION_STATES: Dict[str, Dict[str, Any]] = {}


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

    # Privilege-aware scoring: which access tier this account holds.
    # "standard" (default) / "elevated" / "admin" / "domain_admin" -- see
    # PRIVILEGE_RISK_MULTIPLIER in src/config.py. Previously this was only
    # accepted as an unused extra field; it's now wired into the score.
    privilege_tier: Optional[str] = "standard"

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
        <title>Vigil Risk Engine</title>
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
                <h1 class="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-emerald-400">Vigil Risk Engine</h1>
                <p class="text-slate-400 mt-2">Real-time Insider Threat Detection</p>
            </header>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
                <!-- Input Panel -->
                <div class="glass p-6 rounded-2xl">
                    <h2 class="text-xl font-semibold mb-4">Analyze User Activity</h2>
                    
                    <div class="flex flex-wrap gap-2 mb-6">
                        <button onclick="loadDemo('CCA0046', {logon_count:5, off_hours_events:10, suspicious_url_events:24, external_email_count:8, unique_pcs:6, device_connects:5, device_off_hours:8, file_events:20, removable_file_events:6, email_count:9, privilege_tier:'standard'})" class="text-xs bg-slate-700 hover:bg-slate-600 px-3 py-1 rounded transition">Demo: Critical Threat</button>
                        <button onclick="loadDemo('NEWHIRE01', {logon_count:1, off_hours_events:0, suspicious_url_events:0, external_email_count:4, unique_pcs:1, device_connects:1, device_off_hours:0, file_events:1, removable_file_events:0, email_count:8, privilege_tier:'standard'})" class="text-xs bg-slate-700 hover:bg-slate-600 px-3 py-1 rounded transition">Demo: Normal User</button>
                        <button onclick="loadDemo('SYSADM01', {logon_count:4, off_hours_events:1, suspicious_url_events:0, external_email_count:3, unique_pcs:1, device_connects:0, device_off_hours:0, file_events:3, removable_file_events:0, email_count:3, privilege_tier:'domain_admin'})" class="text-xs bg-indigo-700 hover:bg-indigo-600 px-3 py-1 rounded transition">Demo: Privileged Admin</button>
                        <button onclick="loadDemo('SALESREP07', {logon_count:2, off_hours_events:0, suspicious_url_events:0, external_email_count:4, unique_pcs:1, device_connects:1, device_off_hours:0, file_events:2, removable_file_events:3, email_count:8, privilege_tier:'standard'})" class="text-xs bg-emerald-800 hover:bg-emerald-700 px-3 py-1 rounded transition">Demo: HNDL Exposure Only</button>
                    </div>

                    <div class="space-y-4">
                        <div class="grid grid-cols-2 gap-4">
                            <div><label class="text-sm text-slate-400">User ID</label><input id="f_user" type="text" class="w-full bg-slate-800 rounded p-2 text-white border border-slate-700 focus:border-blue-500 outline-none" value="CCA0046"></div>
                            <div>
                                <label class="text-sm text-slate-400">Privilege Tier</label>
                                <select id="f_privilege" class="w-full bg-slate-800 rounded p-2 text-white border border-slate-700">
                                    <option value="standard">Standard</option>
                                    <option value="elevated">Elevated</option>
                                    <option value="admin">Admin</option>
                                    <option value="domain_admin">Domain Admin</option>
                                </select>
                            </div>
                        </div>
                        <div class="grid grid-cols-2 gap-4">
                            <div><label class="text-sm text-slate-400">Logon Count</label><input id="f_logon" type="number" class="w-full bg-slate-800 rounded p-2 text-white border border-slate-700" value="0"></div>
                            <div><label class="text-sm text-slate-400">Off-Hours Events</label><input id="f_offhours" type="number" class="w-full bg-slate-800 rounded p-2 text-white border border-slate-700" value="0"></div>
                            <div><label class="text-sm text-slate-400">Suspicious URLs</label><input id="f_urls" type="number" class="w-full bg-slate-800 rounded p-2 text-white border border-slate-700" value="0"></div>
                            <div><label class="text-sm text-slate-400">Emails Sent</label><input id="f_emailcount" type="number" class="w-full bg-slate-800 rounded p-2 text-white border border-slate-700" value="0"></div>
                            <div><label class="text-sm text-slate-400">External Emails</label><input id="f_emails" type="number" class="w-full bg-slate-800 rounded p-2 text-white border border-slate-700" value="0"></div>
                            <div><label class="text-sm text-slate-400">Unique PCs</label><input id="f_pcs" type="number" class="w-full bg-slate-800 rounded p-2 text-white border border-slate-700" value="0"></div>
                            <div><label class="text-sm text-slate-400">Device Connects</label><input id="f_device" type="number" class="w-full bg-slate-800 rounded p-2 text-white border border-slate-700" value="0"></div>
                            <div><label class="text-sm text-slate-400">Device Off-Hours</label><input id="f_deviceoff" type="number" class="w-full bg-slate-800 rounded p-2 text-white border border-slate-700" value="0"></div>
                            <div><label class="text-sm text-slate-400">File Events</label><input id="f_file" type="number" class="w-full bg-slate-800 rounded p-2 text-white border border-slate-700" value="0"></div>
                            <div><label class="text-sm text-slate-400">Removable Media Events</label><input id="f_removable" type="number" class="w-full bg-slate-800 rounded p-2 text-white border border-slate-700" value="0"></div>
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

                        <div class="bg-slate-800/50 p-3 rounded-lg border border-slate-700/50 mb-4 flex items-center justify-between">
                            <span class="text-xs text-slate-400 uppercase tracking-wider">HNDL Exposure (Harvest-Now-Decrypt-Later)</span>
                            <span id="res-hndl" class="text-sm font-semibold">--</span>
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
            function loadDemo(user, fields) {
                document.getElementById('f_user').value = user;
                document.getElementById('f_logon').value = fields.logon_count ?? 0;
                document.getElementById('f_offhours').value = fields.off_hours_events ?? 0;
                document.getElementById('f_urls').value = fields.suspicious_url_events ?? 0;
                document.getElementById('f_emailcount').value = fields.email_count ?? 0;
                document.getElementById('f_emails').value = fields.external_email_count ?? 0;
                document.getElementById('f_pcs').value = fields.unique_pcs ?? 0;
                document.getElementById('f_device').value = fields.device_connects ?? 0;
                document.getElementById('f_deviceoff').value = fields.device_off_hours ?? 0;
                document.getElementById('f_file').value = fields.file_events ?? 0;
                document.getElementById('f_removable').value = fields.removable_file_events ?? 0;
                document.getElementById('f_privilege').value = fields.privilege_tier ?? 'standard';
            }

            async function analyzeRisk() {
                const payload = {
                    user: document.getElementById('f_user').value,
                    logon_count: parseInt(document.getElementById('f_logon').value),
                    off_hours_events: parseInt(document.getElementById('f_offhours').value),
                    suspicious_url_events: parseInt(document.getElementById('f_urls').value),
                    email_count: parseInt(document.getElementById('f_emailcount').value),
                    external_email_count: parseInt(document.getElementById('f_emails').value),
                    unique_pcs: parseInt(document.getElementById('f_pcs').value),
                    device_connects: parseInt(document.getElementById('f_device').value),
                    device_off_hours: parseInt(document.getElementById('f_deviceoff').value),
                    file_events: parseInt(document.getElementById('f_file').value),
                    removable_file_events: parseInt(document.getElementById('f_removable').value),
                    privilege_tier: document.getElementById('f_privilege').value
                };

                const res = await fetch('/score', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-API-Key': 'demo-Vigil-key' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();

                document.getElementById('empty-state').classList.add('hidden');
                document.getElementById('results').classList.remove('hidden');
                
                document.getElementById('res-score').innerText = data.risk_score.toFixed(1);
                document.getElementById('res-narrative').innerText = data.narrative_explanation;

                const hndlEl = document.getElementById('res-hndl');
                hndlEl.innerText = data.hndl_tier + ' (' + data.hndl_exposure_score.toFixed(1) + '/100)';
                hndlEl.className = (data.hndl_tier === 'Critical' || data.hndl_tier === 'High')
                    ? 'text-sm font-semibold text-amber-400'
                    : 'text-sm font-semibold text-slate-300';
                
                const tierEl = document.getElementById('res-tier');
                const panelEl = document.getElementById('result-panel');
                tierEl.innerText = data.risk_tier + (data.privilege_tier !== 'standard' ? ' \u00b7 ' + data.privilege_tier.replace('_',' ').toUpperCase() : '');
                
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
def score_user_activity(request: ScoreRequest, _key: str = Depends(require_api_key)):
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

        # Layer on privilege-specific actions -- a High/Critical result on an
        # admin or domain_admin account triggers stronger controls than the
        # same tier on a standard account (dedup while preserving order).
        priv_tier = result.get("privilege_tier", "standard")
        extra_actions = PRIVILEGE_ACTIONS.get(priv_tier, {}).get(tier, [])
        for action in extra_actions:
            if action not in result["recommended_actions"]:
                result["recommended_actions"].append(action)

        # Layer on HNDL (Harvest-Now-Decrypt-Later) actions -- independent
        # of behavioral tier. A user can be Low behavioral risk and still
        # be moving enough sensitive data through an interceptable path
        # (removable media, external email) to warrant flagging for PQC
        # migration / export review.
        hndl_tier = result.get("hndl_tier", "Low")
        for action in HNDL_ACTIONS.get(hndl_tier, []):
            if action not in result["recommended_actions"]:
                result["recommended_actions"].append(action)

        # Generate a normal text explanation
        if result.get("top_signals"):
            reasons = [s["label"] for s in result["top_signals"]]
            reasons_str = ", and ".join(reasons) if len(reasons) <= 2 else ", ".join(reasons[:-1]) + ", and " + reasons[-1]
            privilege_note = (
                f" This account holds {priv_tier.replace('_', ' ')} privileges, "
                f"which raised the base behavioral score (risk score before privilege "
                f"weighting was {result['behavior_score']:.1f}/100)."
                if priv_tier != "standard" else ""
            )
            hndl_note = (
                f" Separately, this activity carries {hndl_tier} Harvest-Now-Decrypt-Later "
                f"(HNDL) exposure (Score: {result['hndl_exposure_score']:.1f}/100) -- data left "
                f"monitored systems via a path (removable media, external email, or file export) "
                f"that could be intercepted today and decrypted later once quantum computing "
                f"matures, regardless of the behavioral risk tier."
                if hndl_tier in ("High", "Critical") else ""
            )
            result["narrative_explanation"] = (
                f"User {result['user']} was flagged as a {tier} risk (Score: {result['risk_score']:.1f}/100). "
                f"This is primarily because they had {reasons_str}.{privilege_note}{hndl_note}"
            )
        else:
            hndl_tail = (
                f" Note: this activity still carries {hndl_tier} HNDL exposure "
                f"(Score: {result['hndl_exposure_score']:.1f}/100)."
                if hndl_tier in ("High", "Critical") else ""
            )
            result["narrative_explanation"] = (
                f"User {result['user']} is currently a {tier} risk (Score: {result['risk_score']:.1f}/100). "
                f"Their activity aligns with their normal historical baseline.{hndl_tail}"
            )

        # Encrypt and store an audit record for High/Critical events -- on
        # EITHER axis. A Critical HNDL exposure event (sensitive data left
        # via an interceptable path) is exactly the kind of thing that
        # needs a tamper-evident audit trail, even when behavioral risk_tier
        # is Low, so we don't gate this on risk_tier alone.
        if tier in VAULT_AUDIT_RISK_TIERS or hndl_tier in VAULT_AUDIT_RISK_TIERS:
            audit_entry = {
                "user_id": result["user"],
                "risk_tier": tier,
                "hndl_tier": hndl_tier,
                "action_taken": result["recommended_actions"],
                "explanation": result["narrative_explanation"],
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "session_id": row_dict.get("day") or "live-request",
            }
            record_id = vault.store_entry(audit_entry)
            result["audit_record_id"] = record_id
        else:
            result["audit_record_id"] = None

        # Automatically determine authoritative session status based on risk tier
        if tier == "Critical":
            session_status = "suspended"
        elif tier == "High":
            session_status = "step_up_required"
        elif tier == "Medium":
            session_status = "allowed_monitored"
        else:
            session_status = "allowed"

        # Apply enforced actions automatically server-side
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        enforced_actions = [
            {"action": action, "enforced_at": now_iso}
            for action in result["recommended_actions"]
        ]
        
        SESSION_STATES[result["user"]] = {
            "session_status": session_status,
            "enforced_actions": enforced_actions
        }

        return result

    except VaultDecryptionError as e:
        # Vault failures must never be silently hidden — raise a specific 503
        # so it's clear the scoring succeeded but the audit store failed.
        raise HTTPException(status_code=503, detail=f"Vault storage failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scoring failed: {str(e)}")


@app.get("/vault/{record_id}")
def read_vault_entry(record_id: str, _key: str = Depends(require_api_key)):
    """
    Retrieve and decrypt a vault audit record by its record_id.
    Returns the original plaintext audit entry for demo/verification purposes.
    Only records for High and Critical risk events are stored.
    Requires X-API-Key header.
    """
    try:
        entry = vault.read_entry(record_id)
        return {"record_id": record_id, "audit_entry": entry}
    except VaultRecordNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except VaultDecryptionError as exc:
        raise HTTPException(status_code=500, detail=f"Vault decryption failed: {exc}")


@app.get("/trend/{user_id}")
def get_user_trend(user_id: str, _key: str = Depends(require_api_key)):
    """
    Return a 7-day daily risk score history for the given user.
    Pre-computed demo data is returned for the 3 showcase users;
    all other user IDs receive a flat Low-risk baseline.
    Requires X-API-Key header.
    """
    today = datetime.date.today()
    
    import hashlib
    import random
    
    if user_id in _TREND_DATA:
        raw = _TREND_DATA[user_id]
    elif user_id == "AMR0400":
        # The new "Normal User"
        raw = [
            {"day": -6, "risk_score": 12.1, "risk_tier": "Low"},
            {"day": -5, "risk_score": 9.8,  "risk_tier": "Low"},
            {"day": -4, "risk_score": 14.3, "risk_tier": "Low"},
            {"day": -3, "risk_score": 11.5, "risk_tier": "Low"},
            {"day": -2, "risk_score": 10.2, "risk_tier": "Low"},
            {"day": -1, "risk_score": 13.7, "risk_tier": "Low"},
            {"day":  0, "risk_score": 8.9,  "risk_tier": "Low"},
        ]
    else:
        # Generate a stable, pseudo-random trend for any unknown user
        # so the graph looks different per-user instead of identical.
        seed = int(hashlib.md5(user_id.encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)
        base = rng.uniform(8.0, 15.0)
        
        raw = []
        for d in range(-6, 1):
            score = base + rng.uniform(-4.0, 4.0)
            score = max(0, min(score, 100))
            raw.append({"day": d, "risk_score": round(score, 1), "risk_tier": "Low"})

    return {
        "user": user_id,
        "trend": [
            {
                "date": (today + datetime.timedelta(days=entry["day"])).isoformat(),
                "risk_score": entry["risk_score"],
                "risk_tier": entry["risk_tier"],
            }
            for entry in raw
        ]
    }


@app.get("/session/{user_id}")
def get_session_state(user_id: str, _key: str = Depends(require_api_key)):
    """
    Returns the current session status and enforced actions for a user.
    """
    if user_id not in SESSION_STATES:
        return {"session_status": "allowed", "enforced_actions": []}
    return SESSION_STATES[user_id]


@app.post("/session/{user_id}/verify")
def verify_session(user_id: str, _key: str = Depends(require_api_key)):
    """
    Simulates a human verifying their identity (e.g., completing an MFA challenge).
    Flips the session status from 'step_up_required' to 'allowed_monitored'.
    """
    if user_id not in SESSION_STATES:
        raise HTTPException(status_code=404, detail="Session not found.")
    
    if SESSION_STATES[user_id]["session_status"] == "step_up_required":
        SESSION_STATES[user_id]["session_status"] = "allowed_monitored"
    elif SESSION_STATES[user_id]["session_status"] == "suspended":
        # We explicitly do NOT allow un-suspending from here, per requirements.
        raise HTTPException(status_code=403, detail="Cannot verify identity for a suspended session.")
    
    return SESSION_STATES[user_id]
