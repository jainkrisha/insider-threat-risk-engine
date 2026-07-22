import { useState, useEffect } from 'react'
import { AlertTriangle, Clock, Key, ShieldAlert, Smartphone, CheckCircle } from 'lucide-react'
import { postDemoLoginEvent, type DemoLoginRequest } from '../api'

import { useNavigate } from 'react-router-dom'

const generateRandomUser = () => `USR${Math.floor(1000 + Math.random() * 9000)}`
const generateRandomPass = () => `Pass${Math.floor(1000 + Math.random() * 9000)}!`
const generateRandomPhone = () => `+1-555-${Math.floor(1000 + Math.random() * 9000).toString().padStart(4, '0')}`

export default function LiveAttackDemo() {
  const navigate = useNavigate()

  const [demoUser, setDemoUser] = useState(generateRandomUser())
  const [demoPass, setDemoPass] = useState(generateRandomPass())
  const [demoPhone, setDemoPhone] = useState(generateRandomPhone())

  const [timestamp, setTimestamp] = useState<string>(
    new Date().toISOString().slice(0, 16)
  )
  
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  
  const [failedAttempts, setFailedAttempts] = useState(0)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)
  const [isSuccessModal, setIsSuccessModal] = useState(false)
  
  // Phase 1 states
  const [isSuspended, setIsSuspended] = useState(false)
  const [suspendReason, setSuspendReason] = useState<string | null>(null)
  
  // Phase 2 states
  const [stepUpRequired, setStepUpRequired] = useState(false)
  const [generatedOtp, setGeneratedOtp] = useState<string>('')
  const [otpInput, setOtpInput] = useState('')
  const [resendCount, setResendCount] = useState(0)
  const [cooldown, setCooldown] = useState(0)
  const [auditRecordId, setAuditRecordId] = useState<string | null>(null)

  // OTP cooldown timer
  useEffect(() => {
    if (cooldown > 0) {
      const timer = setTimeout(() => setCooldown(c => c - 1), 1000)
      return () => clearTimeout(timer)
    }
  }, [cooldown])

  const generateOtp = () => {
    const code = Math.floor(100000 + Math.random() * 900000).toString()
    setGeneratedOtp(code)
  }

  // Check if timestamp is off-hours (before 7am, after 9pm)
  const isOffHours = () => {
    const d = new Date(timestamp)
    const hours = d.getHours()
    return hours < 7 || hours >= 21
  }

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrorMsg(null)
    setSuccessMsg(null)

    const isCorrect = username === demoUser && password === demoPass
    let currentFails = failedAttempts

    if (!isCorrect) {
      currentFails += 1
      setFailedAttempts(currentFails)
      
      if (currentFails >= 6) {
        // Suspend
        setIsSuspended(true)
        setSuspendReason('too_many_failed_attempts')
        await notifyBackend('suspended', 'too_many_failed_attempts', currentFails)
      } else {
        setErrorMsg('Invalid credentials')
      }
    } else {
      // Correct credentials
      if (currentFails < 2) {
        // Normal successful login
        setIsSuccessModal(true)
        await notifyBackend('allowed', null, currentFails)
      } else if (currentFails >= 2 && currentFails < 6) {
        // Trigger step-up
        setStepUpRequired(true)
        generateOtp()
        await notifyBackend('step_up_required', null, currentFails)
      }
    }
  }

  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrorMsg(null)
    setSuccessMsg(null)

    if (otpInput === generatedOtp) {
      setIsSuccessModal(true)
      setStepUpRequired(false)
      await notifyBackend('allowed_monitored', null, failedAttempts)
    } else {
      setIsSuspended(true)
      setSuspendReason('failed_otp_verification')
      await notifyBackend('suspended', 'failed_otp_verification', failedAttempts)
    }
  }

  const handleResendOtp = async () => {
    if (resendCount >= 2 || cooldown > 0) return
    setResendCount(c => c + 1)
    setCooldown(30)
    generateOtp()
  }

  const notifyBackend = async (
    outcome: DemoLoginRequest['outcome'],
    reason: DemoLoginRequest['reason'],
    fails: number
  ) => {
    try {
      const state = await postDemoLoginEvent({
        user_id: demoUser,
        outcome,
        reason,
        off_hours: isOffHours(),
        failed_attempts: fails,
        timestamp: new Date(timestamp).toISOString()
      })
      if (state.audit_record_id) {
        setAuditRecordId(state.audit_record_id)
      }
    } catch (e) {
      console.error('Failed to notify backend', e)
    }
  }

  const resetDemo = () => {
    setUsername('')
    setPassword('')
    setFailedAttempts(0)
    setErrorMsg(null)
    setSuccessMsg(null)
    setIsSuspended(false)
    setSuspendReason(null)
    setStepUpRequired(false)
    setGeneratedOtp('')
    setOtpInput('')
    setResendCount(0)
    setCooldown(0)
    setIsSuccessModal(false)
    setAuditRecordId(null)
    setDemoUser(generateRandomUser())
    setDemoPass(generateRandomPass())
    setDemoPhone(generateRandomPhone())
  }

  const handleViewReport = () => {
    // Scale features based on failedAttempts to generate a dynamic ML score
    // that aligns with the demo's logical outcome.
    const isSuspended = failedAttempts >= 6
    const isStepUp = failedAttempts >= 2 && !isSuspended

    const payload = {
      user: demoUser,
      logon_count: failedAttempts + (isSuccessModal ? 1 : 0) * 2,
      off_hours_events: isOffHours() ? (failedAttempts + 2) : 0,
      unique_pcs: isSuspended ? 3 : (isStepUp ? 2 : 1),
      device_connects: isSuspended ? 1 : 0,
      device_off_hours: 0,
      file_events: isSuspended ? 10 : (isStepUp ? 3 : 0),
      removable_file_events: isSuspended ? 15 : 0,
      email_count: 5,
      external_email_count: isSuspended ? 10 : (isStepUp ? 4 : 0),
      suspicious_url_events: isSuspended ? 25 : (isStepUp ? 5 : 0),
      privilege_tier: 'standard'
    }
    sessionStorage.setItem('Vigil_payload', JSON.stringify(payload))
    const url = `/dashboard/report?user=${demoUser}` + (auditRecordId ? `&record=${auditRecordId}` : '')
    navigate(url)
  }

  return (
    <div className="max-w-4xl mx-auto p-4 sm:p-8 space-y-8 relative">
      <header className="mb-6 border-b border-[#cab593]/50 pb-4">
        <h1 className="text-3xl font-bold flex items-center gap-3 text-[#92402d]">
          <AlertTriangle className="w-8 h-8" />
          Live Attack Demo
        </h1>
        <p className="text-slate-600 mt-2">
          Attacker perspective walkthrough: simulate brute-force attempts and off-hours logins.
        </p>
      </header>

      {/* Task 2: Demo Setup Screen */}
      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-6 space-y-4">
          <h2 className="text-lg font-bold flex items-center gap-2">
            <Clock className="w-5 h-5 text-indigo-500" />
            Simulation Setup
          </h2>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Simulate login at:
            </label>
            <input
              type="datetime-local"
              value={timestamp}
              onChange={e => setTimestamp(e.target.value)}
              className="w-full bg-white border border-slate-300 rounded px-3 py-2 outline-none focus:border-indigo-500"
            />
            <p className="text-xs text-slate-500 mt-1">
              Off-hours (before 7am or after 9pm) will amplify risk scores.
            </p>
          </div>
        </div>

        <div className="bg-[#dfd2bc]/30 border border-[#cab593] rounded-xl p-6 space-y-4">
          <h2 className="text-lg font-bold flex items-center gap-2">
            <Key className="w-5 h-5 text-amber-600" />
            Demo Credentials
          </h2>
          <div className="bg-white p-3 rounded border border-slate-200 font-mono text-sm space-y-1">
            <p><span className="font-bold text-slate-500">Username:</span> {demoUser}</p>
            <p><span className="font-bold text-slate-500">Password:</span> {demoPass}</p>
            <p><span className="font-bold text-slate-500">Phone:</span> {demoPhone}</p>
          </div>
          <p className="text-xs text-slate-500 italic">
            This is a scripted demo identity.
          </p>
        </div>
      </div>

      {/* Task 3: Login Form */}
      <div className="max-w-md mx-auto bg-white border border-slate-200 rounded-xl shadow-sm p-8">
        <h2 className="text-2xl font-bold text-center mb-6">System Login</h2>
        
        {successMsg && (
          <div className="mb-4 p-3 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded text-center font-medium">
            {successMsg}
          </div>
        )}
        
        {errorMsg && (
          <div className="mb-4 p-3 bg-red-50 text-red-700 border border-red-200 rounded text-center font-medium">
            {errorMsg}
          </div>
        )}

        {stepUpRequired ? (
          <div className="space-y-4 animate-fade-in">
            <div className="p-4 bg-orange-50 border border-orange-200 rounded-xl text-center">
              <Smartphone className="w-8 h-8 text-orange-500 mx-auto mb-2" />
              <h3 className="font-bold text-orange-900 mb-1">Step-up verification required</h3>
              <p className="text-sm text-orange-800 mb-3">
                Enter the code sent to {demoPhone}
              </p>
              
              <div className="bg-white p-3 border border-orange-200 rounded font-mono text-lg font-bold tracking-widest text-slate-800 shadow-sm">
                <span className="block text-xs font-sans text-slate-400 font-normal tracking-normal mb-1">
                  DEMO OTP (shown for walkthrough purposes):
                </span>
                {generatedOtp}
              </div>
            </div>

            <form onSubmit={handleVerifyOtp} className="space-y-4">
              <div>
                <input
                  type="text"
                  placeholder="Enter 6-digit code"
                  value={otpInput}
                  onChange={e => setOtpInput(e.target.value)}
                  className="w-full text-center tracking-widest font-mono text-lg border border-slate-300 rounded px-3 py-2 outline-none focus:border-indigo-500"
                  maxLength={6}
                  required
                />
              </div>

              <button
                type="submit"
                className="w-full bg-orange-600 hover:bg-orange-700 text-white font-bold py-2.5 rounded transition-colors"
              >
                Verify
              </button>

              <div className="text-center pt-2">
                {resendCount < 2 ? (
                  <button
                    type="button"
                    onClick={handleResendOtp}
                    disabled={cooldown > 0}
                    className="text-sm font-medium text-indigo-600 hover:text-indigo-800 disabled:text-slate-400 transition-colors"
                  >
                    {cooldown > 0 ? `Resend OTP (${cooldown}s)` : 'Resend OTP'}
                  </button>
                ) : (
                  <span className="text-sm text-slate-500">No more resends available.</span>
                )}
              </div>
            </form>
          </div>
        ) : (
          <form onSubmit={handleLogin} className="space-y-4 animate-fade-in">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Username</label>
              <input
                type="text"
                value={username}
                onChange={e => setUsername(e.target.value)}
                className="w-full border border-slate-300 rounded px-3 py-2 outline-none focus:border-indigo-500"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Password</label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                className="w-full border border-slate-300 rounded px-3 py-2 outline-none focus:border-indigo-500"
                required
              />
            </div>
            
            <div className="flex justify-between items-center text-xs text-slate-500 pt-2">
              <span>Failed attempts: {failedAttempts}</span>
            </div>

            <button
              type="submit"
              disabled={isSuspended}
              className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2.5 rounded transition-colors disabled:opacity-50"
            >
              Login
            </button>
          </form>
        )}
      </div>

      {/* Task 5: Suspend Modal */}
      {isSuspended && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-2xl max-w-md w-full p-8 text-center animate-fade-in-up border-t-8 border-red-600">
            <ShieldAlert className="w-16 h-16 text-red-600 mx-auto mb-4" />
            <h2 className="text-3xl font-extrabold text-slate-900 mb-2">SUSPENDED</h2>
            <p className="text-slate-600 mb-8">
              This session has been suspended due to:<br/>
              <strong className="text-red-700 font-mono text-sm">{suspendReason}</strong>
            </p>
            <div className="flex justify-center gap-3">
              <button
                onClick={resetDemo}
                className="px-6 py-2.5 bg-slate-200 hover:bg-slate-300 text-slate-800 font-bold rounded-lg transition-colors"
              >
                Reset Demo
              </button>
              <button
                onClick={handleViewReport}
                className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-lg transition-colors"
              >
                View Full Report
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Success Modal */}
      {isSuccessModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-2xl max-w-md w-full p-8 text-center animate-fade-in-up border-t-8 border-emerald-500">
            <CheckCircle className="w-16 h-16 text-emerald-500 mx-auto mb-4" />
            <h2 className="text-3xl font-extrabold text-slate-900 mb-2">SUCCESS</h2>
            <p className="text-slate-600 mb-8">
              Login successful. Access has been granted to the system.
            </p>
            <div className="flex justify-center gap-3">
              <button
                onClick={resetDemo}
                className="px-6 py-2.5 bg-slate-200 hover:bg-slate-300 text-slate-800 font-bold rounded-lg transition-colors"
              >
                Reset Demo
              </button>
              <button
                onClick={handleViewReport}
                className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-lg transition-colors"
              >
                View Full Report
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
