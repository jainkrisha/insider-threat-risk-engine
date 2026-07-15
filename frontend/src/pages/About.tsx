import GlassCard from '../components/GlassCard'
import { Database, BarChart3, Layers, Target } from 'lucide-react'

const TIMELINE = [
  {
    icon: <Database className="w-5 h-5 text-indigo-400" />,
    title: 'CERT r4.2 Dataset',
    body: `The CERT Insider Threat Dataset r4.2 contains 17 months of synthetic but realistic
      enterprise activity across ~4,000 employees — logon events, file transfers, device connections,
      emails, and web browsing logs — with a ground-truth label of 70 malicious insiders.`,
  },
  {
    icon: <Layers className="w-5 h-5 text-emerald-400" />,
    title: 'Feature Engineering',
    body: `For each user-day, FinSpark computes 15 behavioural features: logon counts,
      off-hours activity, unique device count, removable media transfers, external email volume,
      suspicious URL visits, and more. Per-user z-scores compare each day to that individual's
      own historical baseline — not a generic company average.`,
  },
  {
    icon: <BarChart3 className="w-5 h-5 text-indigo-400" />,
    title: 'Hybrid Ensemble Model',
    body: `Isolation Forest (60% weight) handles novel, unseen anomalies without labelled data.
      Random Forest (40% weight) is trained on confirmed malicious signatures to boost known threat
      patterns. The composite score weights the peak day, mean activity, and frequency of
      high-risk days — catching both spikes and sustained slow-burn activity.`,
  },
  {
    icon: <Target className="w-5 h-5 text-yellow-400" />,
    title: 'Evaluation Results',
    body: `On a held-out test window of 937 users, the engine caught 47 of 48 malicious
      actors within the Top-100 highest-scoring profiles. Precision @ top-100: 0.47.
      F1 Score: 0.635. The one missed actor was a zero-day behavioural pattern outside the
      training distribution.`,
  },
]

export default function About() {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-16 space-y-16 animate-fade-in">

      <section className="space-y-4">
        <p className="section-label">About the project</p>
        <h1 className="text-4xl font-bold">How FinSpark detects insider threats</h1>
        <p className="text-slate-400 text-lg leading-relaxed">
          FinSpark is a research prototype built to solve the{' '}
          <span className="text-white font-medium">Privileged Access Misuse & Insider Threat Detection</span>{' '}
          problem statement. It demonstrates that production-grade threat detection is possible
          with open datasets and interpretable, auditable AI.
        </p>
      </section>

      <section className="space-y-6">
        {TIMELINE.map((step, i) => (
          <div key={step.title} className="flex gap-5">
            <div className="flex flex-col items-center">
              <div className="w-10 h-10 rounded-xl glass flex items-center justify-center shrink-0">
                {step.icon}
              </div>
              {i < TIMELINE.length - 1 && (
                <div className="w-px flex-1 bg-slate-700/60 mt-2" />
              )}
            </div>
            <GlassCard className="flex-1 mb-4 space-y-2">
              <h2 className="font-semibold text-lg">{step.title}</h2>
              <p className="text-sm text-slate-400 leading-relaxed whitespace-pre-line">{step.body}</p>
            </GlassCard>
          </div>
        ))}
      </section>

      <GlassCard className="glass-hover border-indigo-500/20 space-y-3">
        <h3 className="font-semibold text-indigo-300">⚠️ Prototype Disclaimer</h3>
        <p className="text-sm text-slate-400 leading-relaxed">
          FinSpark is a hackathon prototype trained on a synthetic dataset. The F1 score of 0.635
          is evaluated on the CERT r4.2 held-out test window. Real-world deployment would require
          periodic retraining, privacy review, and human-in-the-loop oversight before any access
          control actions are automatically enforced.
        </p>
      </GlassCard>

    </div>
  )
}
