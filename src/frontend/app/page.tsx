"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import {
  fetchSignalSummary,
  fetchAllSignals,
  fetchVioxxBacktest,
  checkCTDDossier,
  checkCTDText,
  checkCTDPDF,
  checkHealth,
} from "../lib/api";

// ─── Types ─────────────────────────────────────────────────────────────────

interface PRRSignal {
  drug_name: string;
  event_term: string;
  n_drug_event: number;
  prr: number;
  chi_square: number;
  p_value: number;
  lower_ci_95: number;
  upper_ci_95: number;
  signal_status: "SIGNAL" | "WEAK_SIGNAL" | "NOISE";
}

interface VioxxBacktest {
  drug_name: string;
  event_term: string;
  trajectory: Array<{
    quarter: string;
    prr: number;
    chi_square: number;
    n_cases: number;
    signal_status: string;
  }>;
  first_signal_quarter: string;
  market_withdrawal_quarter: string;
  detection_lead_time_quarters: number;
  clinical_summary: string;
}

interface ModuleCompleteness {
  module_id: number;
  module_name: string;
  total_required: number;
  present_count: number;
  partial_count: number;
  missing_count: number;
  critical_missing_count: number;
  completeness_percentage: number;
}

interface GapReport {
  submission_title: string;
  drug_name: string;
  overall_completeness: number;
  total_sections_evaluated: number;
  present_total: number;
  partial_total: number;
  missing_total: number;
  critical_gaps_count: number;
  modules: Record<string, ModuleCompleteness>;
  priority_gaps: Array<{
    section_id: string;
    module_name: string;
    title: string;
    status: string;
    criticality: string;
    action_item: string | null;
    source_reference: string;
    match_evidence: { confidence_score: number; evidence_reasoning: string };
  }>;
  recommended_actions: string[];
  limitations: string[];
  timestamp: string;
}

// ─── Utility helpers ───────────────────────────────────────────────────────

const STATUS_COLORS: Record<string, string> = {
  SIGNAL: "#ef4444",
  WEAK_SIGNAL: "#f59e0b",
  NOISE: "#6b7280",
  PRESENT: "#22c55e",
  PARTIAL: "#f59e0b",
  MISSING: "#ef4444",
  INSUFFICIENT_EVIDENCE: "#8b5cf6",
};

const STATUS_BADGES: Record<string, string> = {
  SIGNAL: "bg-red-500/20 text-red-300 border border-red-500/30",
  WEAK_SIGNAL: "bg-amber-500/20 text-amber-300 border border-amber-500/30",
  NOISE: "bg-gray-500/20 text-gray-400 border border-gray-500/30",
  PRESENT: "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30",
  PARTIAL: "bg-amber-500/20 text-amber-300 border border-amber-500/30",
  MISSING: "bg-red-500/20 text-red-300 border border-red-500/30",
  INSUFFICIENT_EVIDENCE: "bg-violet-500/20 text-violet-300 border border-violet-500/30",
  CRITICAL: "bg-red-600/20 text-red-300 border border-red-600/30",
  MAJOR: "bg-orange-500/20 text-orange-300 border border-orange-500/30",
  STANDARD: "bg-blue-500/20 text-blue-300 border border-blue-500/30",
};

function Badge({ label }: { label: string }) {
  const cls = STATUS_BADGES[label] || "bg-gray-500/20 text-gray-400 border border-gray-500/30";
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold tracking-wide uppercase ${cls}`}>
      {label.replace("_", " ")}
    </span>
  );
}

function ProgressBar({ pct, color = "#3b82f6" }: { pct: number; color?: string }) {
  return (
    <div className="w-full bg-white/10 rounded-full h-2 overflow-hidden">
      <div
        className="h-full rounded-full transition-all duration-700"
        style={{ width: `${Math.min(100, pct)}%`, backgroundColor: color }}
      />
    </div>
  );
}

// ─── Main Application ──────────────────────────────────────────────────────

export default function HomePage() {
  const [tab, setTab] = useState<"signals" | "readiness">("signals");
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);

  useEffect(() => {
    checkHealth().then(setBackendOnline);
  }, []);

  return (
    <div className="min-h-screen" style={{ background: "linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%)" }}>
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-white/10 backdrop-blur-xl bg-black/30">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight">
              <span className="text-blue-400">BOB</span> AI Pharmacovigilance Platform
            </h1>
            <p className="text-xs text-white/50 mt-0.5">IBM BOB AI Hackathon 2026 · P2 · Demon Slayer</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 text-xs">
              <div
                className="w-2 h-2 rounded-full animate-pulse"
                style={{ backgroundColor: backendOnline === null ? "#6b7280" : backendOnline ? "#22c55e" : "#ef4444" }}
              />
              <span className="text-white/60">
                {backendOnline === null ? "Connecting…" : backendOnline ? "API Online" : "API Offline"}
              </span>
            </div>
            <span className="text-xs px-2 py-1 rounded-full bg-blue-500/20 text-blue-300 border border-blue-500/30">
              Gemini 2.5 Flash
            </span>
          </div>
        </div>
      </header>

      {/* Tab Bar */}
      <div className="max-w-7xl mx-auto px-4 pt-6">
        <div className="flex gap-2 p-1 rounded-xl bg-white/5 border border-white/10 w-fit">
          {(["signals", "readiness"] as const).map((t) => (
            <button
              key={t}
              id={`tab-${t}`}
              onClick={() => setTab(t)}
              className={`px-6 py-2.5 rounded-lg text-sm font-semibold transition-all duration-200 ${
                tab === t
                  ? "bg-blue-600 text-white shadow-lg shadow-blue-500/30"
                  : "text-white/60 hover:text-white hover:bg-white/10"
              }`}
            >
              {t === "signals" ? "🔬 Signal Detection" : "📋 Submission Readiness"}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        {tab === "signals" ? (
          <SignalDetectionTab backendOnline={!!backendOnline} />
        ) : (
          <SubmissionReadinessTab backendOnline={!!backendOnline} />
        )}
      </main>

      {/* Footer */}
      <footer className="text-center py-6 text-white/30 text-xs border-t border-white/5 mt-8">
        IBM BOB AI Hackathon 2026 · Problem P2 · Drug Safety Signal Detector & Regulatory Submission Readiness Checker
      </footer>
    </div>
  );
}

// ─── Tab 1: Signal Detection ───────────────────────────────────────────────

function SignalDetectionTab({ backendOnline }: { backendOnline: boolean }) {
  const [signals, setSignals] = useState<PRRSignal[]>([]);
  const [vioxx, setVioxx] = useState<VioxxBacktest | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>("SIGNAL");
  const [searchDrug, setSearchDrug] = useState("");
  const [showVioxx, setShowVioxx] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [sig, bt] = await Promise.all([
        fetchAllSignals(false),
        fetchVioxxBacktest(),
      ]);
      setSignals(sig);
      setVioxx(bt);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load signal data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (backendOnline) loadData();
  }, [backendOnline, loadData]);

  const filtered = signals.filter((s) => {
    const statusMatch = filterStatus === "ALL" || s.signal_status === filterStatus;
    const drugMatch = !searchDrug || s.drug_name.includes(searchDrug.toUpperCase());
    return statusMatch && drugMatch;
  });

  const signalCount = signals.filter((s) => s.signal_status === "SIGNAL").length;
  const weakCount = signals.filter((s) => s.signal_status === "WEAK_SIGNAL").length;

  return (
    <div className="space-y-6">
      {/* Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Total Pairs", val: signals.length, color: "#3b82f6" },
          { label: "Confirmed Signals", val: signalCount, color: "#ef4444" },
          { label: "Weak Signals", val: weakCount, color: "#f59e0b" },
          { label: "Noise", val: signals.length - signalCount - weakCount, color: "#6b7280" },
        ].map(({ label, val, color }) => (
          <div key={label} className="rounded-xl p-4 border border-white/10 bg-white/5 backdrop-blur">
            <div className="text-3xl font-bold" style={{ color }}>{loading ? "—" : val}</div>
            <div className="text-xs text-white/50 mt-1">{label}</div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <input
          id="signal-search-drug"
          type="text"
          placeholder="Search drug…"
          value={searchDrug}
          onChange={(e) => setSearchDrug(e.target.value)}
          className="px-4 py-2 rounded-lg bg-white/10 border border-white/20 text-white text-sm placeholder-white/40 focus:outline-none focus:border-blue-400 transition"
        />
        {["ALL", "SIGNAL", "WEAK_SIGNAL", "NOISE"].map((st) => (
          <button
            key={st}
            id={`filter-${st}`}
            onClick={() => setFilterStatus(st)}
            className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
              filterStatus === st
                ? "bg-blue-600 text-white"
                : "bg-white/10 text-white/60 hover:bg-white/20"
            }`}
          >
            {st.replace("_", " ")}
          </button>
        ))}
        <button
          id="btn-load-signals"
          onClick={loadData}
          disabled={loading}
          className="ml-auto px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold transition disabled:opacity-50"
        >
          {loading ? "Loading…" : "↻ Refresh"}
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-red-500/20 border border-red-500/30 text-red-300 text-sm">
          ⚠ {error} — {backendOnline ? "Backend error" : "Backend offline. Start the FastAPI server."}
        </div>
      )}

      {/* Signal Table */}
      <div className="rounded-xl border border-white/10 bg-white/5 overflow-hidden backdrop-blur">
        <div className="px-4 py-3 border-b border-white/10">
          <h2 className="text-sm font-semibold text-white">
            PRR Signal Rankings ({filtered.length} results)
          </h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-white/40 text-xs uppercase border-b border-white/10">
                <th className="text-left px-4 py-3">Drug</th>
                <th className="text-left px-4 py-3">Adverse Event</th>
                <th className="text-right px-4 py-3">N</th>
                <th className="text-right px-4 py-3">PRR</th>
                <th className="text-right px-4 py-3">Chi²</th>
                <th className="text-right px-4 py-3">95% CI</th>
                <th className="text-center px-4 py-3">Status</th>
              </tr>
            </thead>
            <tbody>
              {filtered.slice(0, 25).map((s, i) => (
                <tr key={i} className="border-b border-white/5 hover:bg-white/5 transition">
                  <td className="px-4 py-3 text-white font-medium">{s.drug_name}</td>
                  <td className="px-4 py-3 text-white/70">{s.event_term}</td>
                  <td className="px-4 py-3 text-right text-white/70">{s.n_drug_event}</td>
                  <td className="px-4 py-3 text-right font-mono text-white">{s.prr.toFixed(2)}</td>
                  <td className="px-4 py-3 text-right font-mono text-white/70">{s.chi_square.toFixed(1)}</td>
                  <td className="px-4 py-3 text-right text-white/50 text-xs">
                    [{s.lower_ci_95.toFixed(2)}, {s.upper_ci_95.toFixed(2)}]
                  </td>
                  <td className="px-4 py-3 text-center">
                    <Badge label={s.signal_status} />
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && !loading && (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-white/40">
                    {signals.length === 0 ? "Load signals to view results" : "No results match the current filter"}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Vioxx Backtest */}
      <div className="rounded-xl border border-white/10 bg-white/5 backdrop-blur">
        <button
          id="btn-vioxx-toggle"
          onClick={() => setShowVioxx((v) => !v)}
          className="w-full px-4 py-4 flex items-center justify-between text-left hover:bg-white/5 transition"
        >
          <div>
            <h2 className="text-sm font-semibold text-white">🕰 Vioxx (Rofecoxib) Historical Backtest</h2>
            <p className="text-xs text-white/50 mt-0.5">
              PRR signal would have been detected 4 years before market withdrawal
            </p>
          </div>
          <span className="text-white/40">{showVioxx ? "▲" : "▼"}</span>
        </button>

        {showVioxx && vioxx && (
          <div className="px-4 pb-4 space-y-4">
            <div className="grid grid-cols-3 gap-4">
              <div className="rounded-lg p-3 bg-red-500/10 border border-red-500/20">
                <div className="text-lg font-bold text-red-400">{vioxx.first_signal_quarter}</div>
                <div className="text-xs text-white/50">First Signal Detected</div>
              </div>
              <div className="rounded-lg p-3 bg-amber-500/10 border border-amber-500/20">
                <div className="text-lg font-bold text-amber-400">{vioxx.market_withdrawal_quarter}</div>
                <div className="text-xs text-white/50">Market Withdrawal</div>
              </div>
              <div className="rounded-lg p-3 bg-blue-500/10 border border-blue-500/20">
                <div className="text-lg font-bold text-blue-400">{vioxx.detection_lead_time_quarters}Q</div>
                <div className="text-xs text-white/50">Early Detection Lead</div>
              </div>
            </div>

            <div className="rounded-lg p-3 bg-white/5 border border-white/10 text-xs text-white/60 leading-relaxed">
              {vioxx.clinical_summary}
            </div>

            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={vioxx.trajectory} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                  <XAxis dataKey="quarter" tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 10 }} interval={3} />
                  <YAxis tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{ background: "#1e1b4b", border: "1px solid rgba(255,255,255,0.2)", borderRadius: 8 }}
                    labelStyle={{ color: "#fff" }}
                    itemStyle={{ color: "#a5b4fc" }}
                  />
                  <Legend />
                  <ReferenceLine y={2.0} stroke="#ef4444" strokeDasharray="5 5" label={{ value: "PRR Threshold (2.0)", fill: "#ef4444", fontSize: 10 }} />
                  <Line type="monotone" dataKey="prr" stroke="#3b82f6" strokeWidth={2} dot={false} name="PRR" />
                  <Line type="monotone" dataKey="n_cases" stroke="#f59e0b" strokeWidth={1.5} dot={false} name="Cases" yAxisId="right" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Tab 2: Submission Readiness ───────────────────────────────────────────

const SAMPLE_DOSSIER = `1.0 Comprehensive Table of Contents
1.1 Forms and Administrative Information - FDA Form 356h and cover letter
1.2 Prescribing Information and Product Labeling - SmPC, package insert
1.4 Risk Management Plan - Pharmacovigilance plan and REMS
2.1 CTD Table of Contents
2.2 CTD Introduction - pharmacological class and indication
2.3 Quality Overall Summary - CMC summary with CQAs
2.5 Clinical Overview - Benefit-risk analysis
2.6 Nonclinical Written and Tabulated Summaries
2.7 Clinical Summary
3.2.S.1 General Information - Drug substance nomenclature and structure
3.2.S.4 Control of Drug Substance - specifications and batch analysis
3.2.P.1 Description and Composition - Dosage form composition
3.2.P.5 Control of Drug Product - Release testing
4.2.1 Pharmacology Study Reports
4.2.3 Toxicology Study Reports - GLP 28-day repeat dose
5.3.5 Reports of Efficacy and Safety Studies - Pivotal Phase 3 CSRs`;

function SubmissionReadinessTab({ backendOnline }: { backendOnline: boolean }) {
  const [report, setReport] = useState<GapReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [inputMode, setInputMode] = useState<"text" | "json" | "pdf">("text");
  const [textInput, setTextInput] = useState(SAMPLE_DOSSIER);
  const [jsonInput, setJsonInput] = useState("");
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [activeGapFilter, setActiveGapFilter] = useState<string>("ALL");

  const runCheck = async () => {
    setLoading(true);
    setError(null);
    setReport(null);
    try {
      let result: GapReport;
      if (inputMode === "text") {
        result = await checkCTDText(textInput);
      } else if (inputMode === "json") {
        result = await checkCTDDossier(JSON.parse(jsonInput));
      } else if (pdfFile) {
        result = await checkCTDPDF(pdfFile);
      } else {
        throw new Error("No PDF file selected");
      }
      setReport(result);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  };

  const completenessColor = (pct: number) =>
    pct >= 80 ? "#22c55e" : pct >= 50 ? "#f59e0b" : "#ef4444";

  const moduleData = report
    ? Object.values(report.modules).map((m) => ({
        name: `M${m.module_id}`,
        fullName: m.module_name.replace("Module ", "M").split(":")[0],
        completeness: m.completeness_percentage,
        present: m.present_count,
        partial: m.partial_count,
        missing: m.missing_count,
      }))
    : [];

  const filteredGaps = report?.priority_gaps.filter(
    (g) => activeGapFilter === "ALL" || g.status === activeGapFilter
  ) || [];

  return (
    <div className="space-y-6">
      {/* Input Panel */}
      <div className="rounded-xl border border-white/10 bg-white/5 backdrop-blur p-4 space-y-4">
        <h2 className="text-sm font-semibold text-white">CTD Dossier Input</h2>

        {/* Mode selector */}
        <div className="flex gap-2">
          {(["text", "json", "pdf"] as const).map((m) => (
            <button
              key={m}
              id={`input-mode-${m}`}
              onClick={() => setInputMode(m)}
              className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                inputMode === m ? "bg-indigo-600 text-white" : "bg-white/10 text-white/60 hover:bg-white/20"
              }`}
            >
              {m === "text" ? "Text Outline" : m === "json" ? "JSON Payload" : "PDF Upload"}
            </button>
          ))}
        </div>

        {inputMode === "text" && (
          <textarea
            id="ctd-text-input"
            value={textInput}
            onChange={(e) => setTextInput(e.target.value)}
            rows={8}
            className="w-full px-4 py-3 rounded-lg bg-black/30 border border-white/20 text-white/80 text-xs font-mono focus:outline-none focus:border-indigo-400 resize-y"
            placeholder="Paste CTD table of contents here…"
          />
        )}

        {inputMode === "json" && (
          <textarea
            id="ctd-json-input"
            value={jsonInput}
            onChange={(e) => setJsonInput(e.target.value)}
            rows={8}
            className="w-full px-4 py-3 rounded-lg bg-black/30 border border-white/20 text-white/80 text-xs font-mono focus:outline-none focus:border-indigo-400 resize-y"
            placeholder='{"submission_title": "...", "sections": [...]}'
          />
        )}

        {inputMode === "pdf" && (
          <div className="flex items-center gap-4">
            <label
              htmlFor="ctd-pdf-input"
              className="cursor-pointer px-6 py-3 rounded-lg border-2 border-dashed border-white/20 text-white/60 text-sm hover:border-indigo-400 hover:text-white/80 transition text-center"
            >
              {pdfFile ? `✓ ${pdfFile.name}` : "Click to select CTD PDF"}
              <input
                id="ctd-pdf-input"
                type="file"
                accept=".pdf"
                onChange={(e) => setPdfFile(e.target.files?.[0] || null)}
                className="hidden"
              />
            </label>
          </div>
        )}

        <button
          id="btn-run-ctd-check"
          onClick={runCheck}
          disabled={loading || !backendOnline}
          className="w-full py-3 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm transition disabled:opacity-50 flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <span className="animate-spin">⚙</span> Analyzing with Gemini 2.5 Flash…
            </>
          ) : (
            "▶ Run ICH M4 Readiness Check"
          )}
        </button>

        {!backendOnline && (
          <p className="text-xs text-amber-400/80 text-center">
            Backend API is offline. Start with: <code className="bg-white/10 px-1 rounded">uvicorn app.main:app --reload</code>
          </p>
        )}
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-red-500/20 border border-red-500/30 text-red-300 text-sm">
          ⚠ {error}
        </div>
      )}

      {/* Report */}
      {report && (
        <div className="space-y-6 animate-in fade-in duration-500">
          {/* Overall Score */}
          <div className="rounded-xl border border-white/10 bg-white/5 backdrop-blur p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-lg font-bold text-white">{report.submission_title}</h2>
                {report.drug_name && <p className="text-sm text-white/50">{report.drug_name}</p>}
              </div>
              <div
                className="text-5xl font-black"
                style={{ color: completenessColor(report.overall_completeness) }}
              >
                {report.overall_completeness.toFixed(1)}%
              </div>
            </div>
            <ProgressBar pct={report.overall_completeness} color={completenessColor(report.overall_completeness)} />
            <div className="grid grid-cols-4 gap-3 mt-4">
              {[
                { label: "PRESENT", val: report.present_total, color: "#22c55e" },
                { label: "PARTIAL", val: report.partial_total, color: "#f59e0b" },
                { label: "MISSING", val: report.missing_total, color: "#ef4444" },
                { label: "CRITICAL GAPS", val: report.critical_gaps_count, color: "#dc2626" },
              ].map(({ label, val, color }) => (
                <div key={label} className="rounded-lg p-3 bg-white/5 border border-white/10 text-center">
                  <div className="text-2xl font-bold" style={{ color }}>{val}</div>
                  <div className="text-xs text-white/40 mt-1">{label}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Module Chart */}
          <div className="rounded-xl border border-white/10 bg-white/5 backdrop-blur p-4">
            <h3 className="text-sm font-semibold text-white mb-4">Module-wise Completeness (Modules 1–5)</h3>
            <div className="h-52">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={moduleData} margin={{ top: 0, right: 10, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                  <XAxis dataKey="name" tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 12 }} />
                  <YAxis domain={[0, 100]} tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{ background: "#1e1b4b", border: "1px solid rgba(255,255,255,0.2)", borderRadius: 8 }}
                    labelStyle={{ color: "#fff" }}
                    formatter={(val: number, name: string) => [`${val}${name === "completeness" ? "%" : ""}`, name]}
                  />
                  <Bar dataKey="present" name="Present" fill="#22c55e" stackId="a" radius={[0, 0, 0, 0]} />
                  <Bar dataKey="partial" name="Partial" fill="#f59e0b" stackId="a" />
                  <Bar dataKey="missing" name="Missing" fill="#ef4444" stackId="a" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            {/* Per-module row */}
            <div className="grid grid-cols-5 gap-2 mt-4">
              {moduleData.map((m) => (
                <div key={m.name} className="rounded-lg p-2 bg-white/5 border border-white/10">
                  <div className="text-xs text-white/40 mb-1">{m.name}</div>
                  <div
                    className="text-lg font-bold"
                    style={{ color: completenessColor(m.completeness) }}
                  >
                    {m.completeness.toFixed(0)}%
                  </div>
                  <ProgressBar pct={m.completeness} color={completenessColor(m.completeness)} />
                </div>
              ))}
            </div>
          </div>

          {/* Priority Gaps */}
          <div className="rounded-xl border border-white/10 bg-white/5 backdrop-blur">
            <div className="px-4 py-3 border-b border-white/10 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-white">
                Priority Gaps ({report.priority_gaps.length})
              </h3>
              <div className="flex gap-2">
                {["ALL", "MISSING", "PARTIAL"].map((f) => (
                  <button
                    key={f}
                    id={`gap-filter-${f}`}
                    onClick={() => setActiveGapFilter(f)}
                    className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                      activeGapFilter === f ? "bg-indigo-600 text-white" : "bg-white/10 text-white/60 hover:bg-white/20"
                    }`}
                  >
                    {f}
                  </button>
                ))}
              </div>
            </div>
            <div className="divide-y divide-white/5">
              {filteredGaps.slice(0, 15).map((g, i) => (
                <div key={i} className="px-4 py-3 hover:bg-white/5 transition">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-mono text-blue-300">{g.section_id}</span>
                        <span className="text-sm text-white truncate">{g.title}</span>
                        <Badge label={g.status} />
                        <Badge label={g.criticality} />
                      </div>
                      <p className="text-xs text-white/40 mt-1">{g.module_name}</p>
                      {g.action_item && (
                        <p className="text-xs text-amber-300/70 mt-1 leading-relaxed">{g.action_item}</p>
                      )}
                    </div>
                    <div className="text-right shrink-0">
                      <div className="text-xs text-white/40">{(g.match_evidence.confidence_score * 100).toFixed(0)}% conf</div>
                    </div>
                  </div>
                </div>
              ))}
              {filteredGaps.length === 0 && (
                <div className="px-4 py-6 text-center text-white/40 text-sm">No gaps in this category</div>
              )}
            </div>
          </div>

          {/* Recommendations */}
          {report.recommended_actions.length > 0 && (
            <div className="rounded-xl border border-white/10 bg-white/5 backdrop-blur p-4">
              <h3 className="text-sm font-semibold text-white mb-3">AI-Grounded Recommendations</h3>
              <ul className="space-y-2">
                {report.recommended_actions.map((a, i) => (
                  <li key={i} className="flex gap-2 text-xs text-white/70 leading-relaxed">
                    <span className="text-indigo-400 shrink-0">→</span>
                    <span>{a}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Limitations */}
          <div className="rounded-xl border border-white/10 bg-white/5 backdrop-blur p-4">
            <h3 className="text-xs font-semibold text-white/40 uppercase tracking-wider mb-2">Assessment Limitations</h3>
            <ul className="space-y-1">
              {report.limitations.map((l, i) => (
                <li key={i} className="text-xs text-white/30 leading-relaxed">• {l}</li>
              ))}
            </ul>
            <p className="text-xs text-white/20 mt-2">Evaluated: {new Date(report.timestamp).toLocaleString()}</p>
          </div>
        </div>
      )}
    </div>
  );
}
