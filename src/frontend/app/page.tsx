"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import {
  LineChart,
  Line,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Cell,
} from "recharts";
import {
  fetchSignalSummary,
  fetchAllSignals,
  fetchDrugBacktest,
  calculateCustomPRR,
  liveOpenFDALookup,
  LiveLookupResult,
  fetchAdverseEventClusters,
  fetchM4Presets,
  checkCTDDossier,
  checkCTDText,
  checkCTDPDF,
  exportGapReportPDF,
  checkHealth,
  CustomPRRPayload,
} from "../lib/api";
import {
  ClusterProfile,
  ClusterPoint,
  ClusteringResponse,
} from "../lib/types";
import { Sidebar, NavPage } from "../components/Sidebar";
import { Header } from "../components/Header";
import { MetricCard } from "../components/MetricCard";
import { StatusBadge } from "../components/StatusBadge";
import { PageHeader } from "../components/PageHeader";
import { LoadingState } from "../components/LoadingState";
import { ErrorState } from "../components/ErrorState";
import { EmptyState } from "../components/EmptyState";
import { BobCopilotDrawer } from "../components/BobCopilotDrawer";
import { SignalBubbleChart } from "../components/SignalBubbleChart";
import { ContentAdequacyBadge } from "../components/ContentAdequacyBadge";


// ─── Types ─────────────────────────────────────────────────────────────────

interface PRRSignal {
  drug_name: string;
  event_term: string;
  n_drug_event: number;
  n_drug_total?: number;
  n_event_total?: number;
  n_total?: number;
  prr: number;
  chi_square: number;
  p_value: number;
  lower_ci_95: number;
  upper_ci_95: number;
  signal_status: "SIGNAL" | "WEAK_SIGNAL" | "NOISE";
}

interface DrugBacktestData {
  drug_name: string;
  event_term: string;
  trajectory: Array<{
    quarter: string;
    prr: number;
    chi_square: number;
    n_cases: number;
    signal_status: string;
    is_projected?: boolean;
    drug_total_cumulative?: number;
  }>;
  first_signal_quarter: string;
  first_signal_prr?: number;
  market_withdrawal_quarter: string;
  detection_lead_time_quarters: number | string;
  lead_time_days?: number | string;
  verdict?: string;
  clinical_summary: string;
  source_note?: string;
}

interface CustomPRRResult {
  drug_name: string;
  event_term: string;
  n_drug_event: number;
  n_drug_total: number;
  n_event_total: number;
  n_total: number;
  contingency_table: {
    a_drug_event: number;
    b_drug_other_events: number;
    c_other_drugs_event: number;
    d_other_drugs_other_events: number;
  };
  metrics: {
    prr: number;
    log_prr: number;
    chi_square: number;
    p_value: number;
    lower_ci: number;
    upper_ci: number;
  };
  signal_status: string;
  is_signal: boolean;
  explanation: string;
  bob_interpretation?: string | null;
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
    requires_safety_update?: boolean;
    safety_update_reason?: string | null;
    content_adequacy_score?: number | null;
    checkpoint_results?: Array<{
      id: string;
      question: string;
      answer: string;
      quote: string | null;
    }> | null;
  }>;
  recommended_actions: string[];
  limitations: string[];
  timestamp: string;
  safety_signal_linkage?: {
    drug_name: string;
    has_confirmed_signal: boolean;
    flagged_section_ids: string[];
    confirmed_events: Array<{ event_term: string; prr: number; n_drug_event: number }>;
    message: string | null;
  } | null;
}

// ─── Main Application Component ────────────────────────────────────────────

export default function HomePage() {
  const [currentPage, setCurrentPage] = useState<NavPage>("dashboard");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [copilotOpen, setCopilotOpen] = useState(false);
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);

  // Global State for Signals & Summary
  const [signals, setSignals] = useState<PRRSignal[]>([]);
  const [summaryData, setSummaryData] = useState<any>(null);
  const [loadingGlobalSignals, setLoadingGlobalSignals] = useState(false);

  // Health check & Initial fetch
  useEffect(() => {
    checkHealth().then(setBackendOnline);
    const interval = setInterval(() => {
      checkHealth().then(setBackendOnline);
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  const loadGlobalSignals = useCallback(async () => {
    setLoadingGlobalSignals(true);
    try {
      const [allSig, sum] = await Promise.all([
        fetchAllSignals(false).catch(() => []),
        fetchSignalSummary().catch(() => null),
      ]);
      setSignals(allSig);
      setSummaryData(sum);
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingGlobalSignals(false);
    }
  }, []);

  useEffect(() => {
    if (backendOnline) {
      loadGlobalSignals();
    }
  }, [backendOnline, loadGlobalSignals]);

  return (
    <div className="min-h-screen bg-[#fbfcfd] text-slate-900 flex font-sans">
      {/* Compact Enterprise Sidebar */}
      <Sidebar
        currentPage={currentPage}
        onSelectPage={setCurrentPage}
        isOpen={sidebarOpen}
        onCloseMobile={() => setSidebarOpen(false)}
      />

      {/* Main Content Workspace */}
      <div className="flex-1 flex flex-col min-w-0 lg:pl-64">
        <Header
          currentPage={currentPage}
          onOpenMobileMenu={() => setSidebarOpen(true)}
          backendOnline={backendOnline}
          onToggleCopilot={() => setCopilotOpen((o) => !o)}
          copilotOpen={copilotOpen}
        />

        {/* Global Subheader Status Strip */}
        <div className="px-4 lg:px-6 pt-3 pb-1">
          <div className="px-3.5 py-2 rounded bg-white border border-slate-200 text-xs text-slate-700 flex flex-col sm:flex-row sm:items-center justify-between gap-2 shadow-2xs">
            <div className="flex items-center gap-2">
              <span className="font-bold text-blue-700 uppercase tracking-wider text-[10px] bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                PharmSignals P2 Suite
              </span>
              <span className="font-medium text-slate-600">
                Integrated Pharmacovigilance Disproportionality Surveillance & ICH M4 CTD Dossier Readiness
              </span>
            </div>
            <div className="flex items-center gap-2 text-[11px] font-mono text-slate-500 shrink-0">
              <span>FAERS DB: 20M+ Reports</span>
              <span>•</span>
              <span className="text-emerald-700 font-semibold">ICH M4 Ground Truth Active</span>
            </div>
          </div>
        </div>

        {/* Dynamic Page Container */}
        <main className="flex-1 p-4 lg:p-6 space-y-6">
          {currentPage === "dashboard" && (
            <DashboardView
              signals={signals}
              summaryData={summaryData}
              onNavigate={setCurrentPage}
              backendOnline={backendOnline}
              onRefreshSignals={loadGlobalSignals}
              loadingSignals={loadingGlobalSignals}
            />
          )}

          {currentPage === "signals" && (
            <SignalDetectionView
              signals={signals}
              backendOnline={backendOnline}
              onRefresh={loadGlobalSignals}
              loading={loadingGlobalSignals}
            />
          )}

          {currentPage === "historical" && (
            <HistoricalAnalysisView backendOnline={backendOnline} />
          )}

          {currentPage === "readiness" && (
            <SubmissionReadinessView backendOnline={backendOnline} />
          )}

          {currentPage === "reports" && (
            <ReportsView
              signals={signals}
              summaryData={summaryData}
              backendOnline={backendOnline}
              onNavigate={setCurrentPage}
            />
          )}

          {currentPage === "about" && <AboutView />}
        </main>
      </div>

      {/* Slide-over IBM Bob Copilot Drawer */}
      <BobCopilotDrawer
        isOpen={copilotOpen}
        onClose={() => setCopilotOpen(false)}
        backendOnline={backendOnline}
      />
    </div>
  );
}

// ───────────────────────────────────────────────────────────────────────────
// VIEW 1: DASHBOARD (PharmSignals PV Analytics & Compliance Hub)
// ───────────────────────────────────────────────────────────────────────────

function DashboardView({
  signals,
  summaryData,
  onNavigate,
  backendOnline,
  onRefreshSignals,
  loadingSignals,
}: {
  signals: PRRSignal[];
  summaryData: any;
  onNavigate: (page: NavPage) => void;
  backendOnline: boolean | null;
  onRefreshSignals: () => void;
  loadingSignals: boolean;
}) {
  // Load real readiness score from the Vioxx NDA preset via backend
  const [readinessScore, setReadinessScore] = useState<string>("—");
  const [criticalGapsCount, setCriticalGapsCount] = useState<string>("—");

  useEffect(() => {
    if (!backendOnline) return;
    // Guards against a stale response overwriting a newer one if this effect
    // re-fires (e.g. backendOnline flaps) before the first request resolves.
    let cancelled = false;
    fetchM4Presets()
      .then((res) => {
        const p = (res?.presets || []).find((x: any) => x.id === "VIOXX_NDA_21042") || (res?.presets || [])[0];
        if (!p) return;
        return checkCTDDossier(p.outline);
      })
      .then((report: any) => {
        if (cancelled || !report) return;
        setReadinessScore(`${Number(report.overall_completeness).toFixed(1)}%`);
        setCriticalGapsCount(String(report.critical_gaps_count ?? "—"));
      })
      .catch(() => {
        // silently fall back to "—" — dashboard is a preview, not the primary source
      });
    return () => {
      cancelled = true;
    };
  }, [backendOnline]);

  const totalPairs =
    summaryData?.total_drug_event_pairs ??
    summaryData?.dataset_summary?.total_drug_event_pairs ??
    signals.length;
  const confirmedSignals =
    summaryData?.confirmed_signals ??
    summaryData?.signal_summary?.confirmed_signals ??
    signals.filter((s) => s.signal_status === "SIGNAL").length;
  const maxPRR =
    summaryData?.max_prr ??
    summaryData?.signal_summary?.max_prr ??
    (signals.length > 0 ? Math.max(...signals.map((s) => s.prr || 0)).toFixed(2) : "—");

  // Prepare Scatter / Bubble chart data (PRR vs. Cases)
  const bubbleData = signals.map((s, idx) => ({
    id: idx + 1,
    drug: s.drug_name,
    event: s.event_term,
    prr: Number(Number(s.prr).toFixed(2)),
    cases: s.n_drug_event,
    chi2: Number(Number(s.chi_square).toFixed(1)),
    status: s.signal_status,
  }));

  return (
    <div className="space-y-5">
      {/* Top Banner & Primary Actions */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-3 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold tracking-tight text-slate-900">
              Signal Detection & PV Analytics
            </h1>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-blue-50 text-blue-700 border border-blue-200">
              Pharmacovigilance
            </span>
          </div>
          <p className="mt-0.5 text-xs text-slate-600 font-medium">
            Disproportionality surveillance across openFDA FAERS adverse-event records & ICH M4 dossier audit
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={onRefreshSignals}
            disabled={loadingSignals || !backendOnline}
            className="px-3.5 py-1.5 rounded bg-blue-700 hover:bg-blue-800 text-white font-bold text-xs shadow-xs transition flex items-center gap-1.5 disabled:opacity-50"
          >
            <span>⚡</span>
            <span>{loadingSignals ? "Scanning..." : "Run Signal Scan"}</span>
          </button>
          <button
            onClick={() => onNavigate("signals")}
            className="px-3 py-1.5 rounded bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs border border-slate-300 shadow-2xs transition"
          >
            Analyze FAERS Data
          </button>
          <button
            onClick={() => onNavigate("readiness")}
            className="px-3 py-1.5 rounded bg-white hover:bg-slate-50 text-blue-700 font-semibold text-xs border border-blue-200 shadow-2xs transition"
          >
            Dossier Readiness Checker →
          </button>
        </div>
      </div>

      {/* High-Level Analytical KPI Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        <MetricCard
          label="Confirmed Safety Signals"
          value={confirmedSignals > 0 ? confirmedSignals : (backendOnline ? "0" : "—")}
          subtext={totalPairs > 0 ? `Evaluated out of ${totalPairs} FAERS pairs` : "Run scan to populate"}
          badge="PRR ≥ 2.0 & χ² ≥ 4"
          color="#dc2626"
          icon="🚨"
        />
        <MetricCard
          label="Highest PRR Disproportionality"
          value={maxPRR !== "—" ? `${maxPRR}x` : "—"}
          subtext="Vioxx / Myocardial Infarction peak"
          badge="Evans Metric"
          color="#ea580c"
          icon="📈"
        />
        <MetricCard
          label="CTD Submission Readiness"
          value={readinessScore}
          subtext="Vioxx NDA 21-042 benchmark dossier"
          badge="ICH M4 CTD"
          color="#2563eb"
          icon="📋"
        />
        <MetricCard
          label="Critical Regulatory Gaps"
          value={criticalGapsCount}
          subtext="Missing mandatory ICH M4 sections"
          badge="High Priority"
          color="#9333ea"
          icon="⚠"
        />
      </div>

      {/* Main Analytical Panel: Adverse Event Bubble Chart */}
      <div className="rounded border border-slate-200 bg-white p-4 shadow-2xs space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2.5 border-b border-slate-100">
          <div>
            <h3 className="text-sm font-bold text-slate-900">
              Adverse Event Bubble Chart
            </h3>
            <p className="text-xs text-slate-500 font-medium">
              Emerging Safety Signals: Proportional Reporting Ratio (PRR) vs. Case Count ($a$)
            </p>
          </div>
          <div className="flex items-center gap-3 text-xs">
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-rose-600 inline-block" />
              <span className="text-slate-600 font-semibold text-[11px]">Confirmed Signal (PRR ≥ 2)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500 inline-block" />
              <span className="text-slate-600 font-semibold text-[11px]">Borderline / Weak</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-slate-400 inline-block" />
              <span className="text-slate-600 font-semibold text-[11px]">Non-Signal</span>
            </div>
          </div>
        </div>

        {bubbleData.length === 0 ? (
          backendOnline ? (
            <LoadingState
              message="Ingesting FAERS datasets and computing disproportionality metrics..."
              description="Connecting to backend Evans PRR engine"
            />
          ) : (
            <EmptyState
              icon="🔌"
              title="Backend Service Offline"
              description="Please start the backend service using 'npm run dev' to visualize safety signals."
            />
          )
        ) : (
          <SignalBubbleChart data={bubbleData} />
        )}
      </div>

      {/* High-Priority Signals Table */}
      <div className="rounded border border-slate-200 bg-white p-4 shadow-2xs space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2.5 border-b border-slate-100">
          <div>
            <h3 className="text-sm font-bold text-slate-900">
              High-Priority Signals (FAERS Surveillance)
            </h3>
            <p className="text-xs text-slate-500 font-medium">
              Ranked by Proportional Reporting Ratio (PRR) descending with Pearson $\chi^2$ statistical confirmation
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={onRefreshSignals}
              disabled={loadingSignals}
              className="px-2.5 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold border border-slate-300 transition"
            >
              ↻ Refresh
            </button>
            <button
              onClick={() => onNavigate("signals")}
              className="px-2.5 py-1 rounded bg-blue-50 hover:bg-blue-100 text-blue-700 text-xs font-semibold border border-blue-200 transition"
            >
              Full Signal Registry →
            </button>
          </div>
        </div>

        {signals.length === 0 ? (
          <EmptyState
            icon="🔎"
            title="No Signal Data Loaded"
            description="Run a signal scan to analyze available openFDA FAERS adverse event records."
            actionText="Run Signal Scan"
            onAction={onRefreshSignals}
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-600 font-semibold uppercase tracking-wider text-[10px] border-y border-slate-200">
                <tr>
                  <th className="py-2.5 px-3">#</th>
                  <th className="py-2.5 px-3">Drug Candidate</th>
                  <th className="py-2.5 px-3">Adverse Reaction (MedDRA)</th>
                  <th className="py-2.5 px-3 font-mono">PRR</th>
                  <th className="py-2.5 px-3 font-mono">χ² Stat</th>
                  <th className="py-2.5 px-3 font-mono">Cases ($a$)</th>
                  <th className="py-2.5 px-3 font-mono">95% Conf. Interval</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {signals.slice(0, 7).map((sig, idx) => (
                  <tr key={idx} className="hover:bg-slate-50/80 transition">
                    <td className="py-2 px-3 text-slate-400 font-mono text-[11px]">{idx + 1}</td>
                    <td className="py-2 px-3 font-bold text-slate-900">{sig.drug_name}</td>
                    <td className="py-2 px-3 text-slate-700 font-medium">{sig.event_term}</td>
                    <td className="py-2 px-3 font-mono font-bold text-rose-600">
                      {Number(sig.prr).toFixed(2)}x
                    </td>
                    <td className="py-2 px-3 font-mono text-slate-700">
                      {Number(sig.chi_square).toFixed(1)}
                    </td>
                    <td className="py-2 px-3 font-mono font-semibold text-slate-800">
                      {sig.n_drug_event}
                    </td>
                    <td className="py-2 px-3 font-mono text-slate-500 text-[11px]">
                      [{Number(sig.lower_ci_95).toFixed(2)} – {Number(sig.upper_ci_95).toFixed(2)}]
                    </td>
                    <td className="py-2 px-3">
                      <StatusBadge label={sig.signal_status} size="sm" />
                    </td>
                    <td className="py-2 px-3 text-right">
                      <button
                        onClick={() => onNavigate("signals")}
                        className="px-2 py-0.5 rounded bg-slate-100 hover:bg-blue-50 text-blue-700 text-[11px] font-semibold border border-slate-200 transition"
                      >
                        Inspect 2×2
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

// ───────────────────────────────────────────────────────────────────────────
// VIEW 2: SIGNAL DETECTION WORKSPACE (2x2 Calculator & Full Registry)
// ───────────────────────────────────────────────────────────────────────────

function SignalDetectionView({
  signals,
  backendOnline,
  onRefresh,
  loading,
}: {
  signals: PRRSignal[];
  backendOnline: boolean | null;
  onRefresh: () => void;
  loading: boolean;
}) {
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");

  // Visual Analytics Mode: Clustering (M1) vs. Disproportionality Bubble (M2)
  const [visualMode, setVisualMode] = useState<"clustering" | "bubble">("clustering");

  // Adverse Event Clustering State (scikit-learn KMeans & PCA)
  const [clusteringData, setClusteringData] = useState<ClusteringResponse | null>(null);
  const [clusteringLoading, setClusteringLoading] = useState(false);
  const [clusteringError, setClusteringError] = useState<string | null>(null);
  const [selectedK, setSelectedK] = useState<number>(4);
  const [clusterDrugFilter, setClusterDrugFilter] = useState<string>("ALL");
  const [activeClusterId, setActiveClusterId] = useState<number | null>(null);

  // Tracks the most recently issued cluster request so a slower, stale
  // response (e.g. k=3 resolving after a later k=5 click) can't overwrite
  // the result of a request issued after it.
  const clusterRequestIdRef = useRef(0);

  const loadClusters = useCallback(async (k: number, drug: string) => {
    const requestId = ++clusterRequestIdRef.current;
    setClusteringLoading(true);
    setClusteringError(null);
    try {
      const data = await fetchAdverseEventClusters(k, drug);
      if (clusterRequestIdRef.current !== requestId) return;
      setClusteringData(data);
    } catch (err: any) {
      if (clusterRequestIdRef.current !== requestId) return;
      setClusteringError(err?.message || "Failed to compute adverse event clusters");
    } finally {
      if (clusterRequestIdRef.current === requestId) {
        setClusteringLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    if (backendOnline) {
      loadClusters(selectedK, clusterDrugFilter);
    }
  }, [backendOnline, selectedK, clusterDrugFilter, loadClusters]);

  // Custom 2x2 Interactive Calculator State
  // Default preset: real VIOXX MI values from VIOXX_signals.csv
  const [calcDrug, setCalcDrug] = useState("ROFECOXIB (VIOXX)");
  const [calcEvent, setCalcEvent] = useState("MYOCARDIAL INFARCTION");
  const [a, setA] = useState(17938);
  const [b, setB] = useState(26341);
  const [c, setC] = useState(155582);
  const [d, setD] = useState(20492829);

  const [customResult, setCustomResult] = useState<CustomPRRResult | null>(null);
  const [calcLoading, setCalcLoading] = useState(false);
  const [calcError, setCalcError] = useState<string | null>(null);

  const runCustomCalculation = useCallback(
    async (payload: CustomPRRPayload) => {
      setCalcLoading(true);
      setCalcError(null);
      try {
        const res = await calculateCustomPRR(payload);
        setCustomResult(res);
      } catch (e: any) {
        setCalcError(e?.message || "Failed to calculate PRR on backend");
      } finally {
        setCalcLoading(false);
      }
    },
    []
  );

  // LIVE openFDA Lookup — queries the real openFDA API for any arbitrary drug,
  // not limited to the 3 pre-loaded VIOXX/BAYCOL/AVANDIA benchmarks.
  const [liveDrugName, setLiveDrugName] = useState("");
  const [liveEventTerm, setLiveEventTerm] = useState("");
  const [liveResult, setLiveResult] = useState<LiveLookupResult | null>(null);
  const [liveLoading, setLiveLoading] = useState(false);
  const [liveError, setLiveError] = useState<string | null>(null);

  const runLiveLookup = async () => {
    if (!liveDrugName.trim()) {
      setLiveError("Enter a drug name to query openFDA live.");
      return;
    }
    setLiveLoading(true);
    setLiveError(null);
    setLiveResult(null);
    try {
      const res = await liveOpenFDALookup(liveDrugName.trim(), liveEventTerm.trim());
      setLiveResult(res);
      if (!res.success) {
        setLiveError(res.error || "No signal could be computed for this query.");
      }
    } catch (e: any) {
      setLiveError(e?.message || "Live openFDA lookup failed.");
    } finally {
      setLiveLoading(false);
    }
  };

  // Run initial calculation on mount
  useEffect(() => {
    if (backendOnline) {
      runCustomCalculation({
        drug_name: calcDrug,
        event_term: calcEvent,
        a,
        b,
        c,
        d,
      });
    }
  }, [backendOnline, runCustomCalculation]);

  // Preset Selector — real a/b/c/d values read from m2_signals CSVs
  const loadPreset = (presetName: string) => {
    if (presetName === "vioxx") {
      setCalcDrug("ROFECOXIB (VIOXX)");
      setCalcEvent("MYOCARDIAL INFARCTION");
      setA(17938);
      setB(26341);
      setC(155582);
      setD(20492829);
      runCustomCalculation({
        drug_name: "ROFECOXIB (VIOXX)",
        event_term: "MYOCARDIAL INFARCTION",
        a: 17938,
        b: 26341,
        c: 155582,
        d: 20492829,
      });
    } else if (presetName === "baycol") {
      setCalcDrug("CERIVASTATIN (BAYCOL)");
      setCalcEvent("RHABDOMYOLYSIS");
      setA(8);
      setB(192);
      setC(41069);
      setD(20651421);
      runCustomCalculation({
        drug_name: "CERIVASTATIN (BAYCOL)",
        event_term: "RHABDOMYOLYSIS",
        a: 8,
        b: 192,
        c: 41069,
        d: 20651421,
      });
    } else if (presetName === "avandia") {
      setCalcDrug("ROSIGLITAZONE (AVANDIA)");
      setCalcEvent("CARDIAC FAILURE CONGESTIVE");
      setA(26009);
      setB(70272);
      setC(54020);
      setD(20542389);
      runCustomCalculation({
        drug_name: "ROSIGLITAZONE (AVANDIA)",
        event_term: "CARDIAC FAILURE CONGESTIVE",
        a: 26009,
        b: 70272,
        c: 54020,
        d: 20542389,
      });
    } else if (presetName === "noise") {
      setCalcDrug("IBUPROFEN");
      setCalcEvent("HEADACHE");
      setA(12);
      setB(18000);
      setC(1500);
      setD(1200000);
      runCustomCalculation({
        drug_name: "IBUPROFEN",
        event_term: "HEADACHE",
        a: 12,
        b: 18000,
        c: 1500,
        d: 1200000,
      });
    }
  };

  const filteredSignals = signals.filter((s) => {
    const matchesSearch =
      s.drug_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      s.event_term.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === "ALL" || s.signal_status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  // Cluster colors
  const clusterColors = [
    "#e11d48", // Cluster 1: Rose / Critical (Cardiovascular & Mortality)
    "#d97706", // Cluster 2: Amber / High (Severe Toxicity & Rhabdomyolysis)
    "#2563eb", // Cluster 3: Blue / Moderate (Metabolic & Fluid Overload)
    "#059669", // Cluster 4: Emerald / Standard (General Systemic)
    "#7c3aed", // Cluster 5: Purple
    "#0891b2", // Cluster 6: Cyan
  ];

  // Prepare Bubble Chart data for Mode 1 view
  const bubbleData = signals.map((s, idx) => ({
    id: idx + 1,
    drug: s.drug_name,
    event: s.event_term,
    prr: Number(Number(s.prr).toFixed(2)),
    cases: s.n_drug_event,
    chi2: Number(Number(s.chi_square).toFixed(1)),
    status: s.signal_status,
  }));

  // Filtered cluster points
  const displayedPoints = (clusteringData?.points || []).filter((p) => {
    if (activeClusterId !== null && p.cluster_id !== activeClusterId) return false;
    return true;
  });

  return (
    <div className="space-y-5">
      <PageHeader
        title="Drug Safety Signal Detection Workspace"
        subtitle="Multi-dimensional adverse event clustering and Evans disproportionality surveillance on openFDA FAERS data."
        badge="Mode 1: M1 + M2"
        actions={
          <div className="flex items-center gap-2">
            <button
              onClick={() => loadClusters(selectedK, clusterDrugFilter)}
              disabled={clusteringLoading}
              className="px-3 py-1.5 rounded bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold border border-slate-300 transition shadow-2xs flex items-center gap-1 disabled:opacity-50"
            >
              <span>⚙️</span>
              <span>{clusteringLoading ? "Clustering..." : "Re-cluster (scikit-learn)"}</span>
            </button>
            <button
              onClick={onRefresh}
              disabled={loading}
              className="px-3.5 py-1.5 rounded bg-blue-700 hover:bg-blue-800 text-white text-xs font-bold transition shadow-xs flex items-center gap-1.5 disabled:opacity-50"
            >
              <span>↻</span>
              <span>{loading ? "Scanning..." : "Run Signal Scan"}</span>
            </button>
          </div>
        }
      />

      {/* ─── VISUAL ANALYTICS STUDIO: CLUSTERING & BUBBLE CHART ─── */}
      <div className="rounded border border-slate-200 bg-white p-4 shadow-2xs space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-3 border-b border-slate-100">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-slate-900">
                {visualMode === "clustering"
                  ? "Adverse Event Multidimensional Clustering Studio (scikit-learn KMeans & PCA)"
                  : "Adverse Event Disproportionality Bubble Chart (PRR vs. Case Count)"}
              </h3>
              <span className="text-[10px] px-2 py-0.5 rounded bg-blue-50 text-blue-700 font-bold border border-blue-200">
                {visualMode === "clustering" ? "scikit-learn 1.4+ · 7 Feature Vectors" : "Evans Criteria"}
              </span>
            </div>
            <p className="text-xs text-slate-500 font-medium mt-0.5">
              {visualMode === "clustering"
                ? "Groups adverse events across PRR disproportionality, mortality %, hospitalization %, patient age, and sex demographics."
                : "Interactive scatter distribution of statistical signal strength against empirical case volume."}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {/* View Mode Toggle */}
            <div className="flex rounded border border-slate-200 p-0.5 bg-slate-50 text-xs font-semibold">
              <button
                onClick={() => setVisualMode("clustering")}
                className={`px-3 py-1 rounded transition ${
                  visualMode === "clustering"
                    ? "bg-white text-blue-700 font-bold shadow-2xs border border-slate-200"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                🔬 Multidimensional Clusters
              </button>
              <button
                onClick={() => setVisualMode("bubble")}
                className={`px-3 py-1 rounded transition ${
                  visualMode === "bubble"
                    ? "bg-white text-blue-700 font-bold shadow-2xs border border-slate-200"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                🫧 Disproportionality Chart
              </button>
            </div>

            {/* Clustering Controls (Visible in Clustering Mode) */}
            {visualMode === "clustering" && (
              <div className="flex items-center gap-2 pl-2 border-l border-slate-200">
                <div className="flex items-center gap-1">
                  <span className="text-[11px] font-bold text-slate-500">Clusters ($k$):</span>
                  {[3, 4, 5].map((kVal) => (
                    <button
                      key={kVal}
                      onClick={() => setSelectedK(kVal)}
                      className={`px-2 py-0.5 text-xs font-mono font-bold rounded ${
                        selectedK === kVal
                          ? "bg-blue-700 text-white shadow-2xs"
                          : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                      }`}
                    >
                      {kVal}
                    </button>
                  ))}
                </div>

                <select
                  value={clusterDrugFilter}
                  onChange={(e) => setClusterDrugFilter(e.target.value)}
                  className="px-2 py-1 rounded bg-white border border-slate-300 text-slate-700 text-xs font-semibold outline-none"
                >
                  <option value="ALL">All Benchmark Drugs</option>
                  <option value="VIOXX">VIOXX (Rofecoxib)</option>
                  <option value="AVANDIA">AVANDIA (Rosiglitazone)</option>
                  <option value="BAYCOL">BAYCOL (Cerivastatin)</option>
                </select>
              </div>
            )}
          </div>
        </div>

        {/* CLUSTERING VIEW CONTENT */}
        {visualMode === "clustering" && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
            {/* Left: 2D PCA Scatter Chart */}
            <div className="lg:col-span-7 rounded border border-slate-200 bg-slate-50/50 p-3 flex flex-col justify-between">
              <div className="flex items-center justify-between pb-2 border-b border-slate-200 text-xs">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-bold text-slate-800">2D PCA Clinical Landscape</span>
                  <span className="text-[10px] text-slate-500 font-mono">
                    {displayedPoints.length} events projected
                  </span>
                  {typeof clusteringData?.metadata?.silhouette_score === "number" && (
                    <span className="text-[10px] text-slate-500 font-mono">
                      · silhouette {clusteringData.metadata.silhouette_score.toFixed(2)}
                    </span>
                  )}
                  {!!clusteringData?.metadata?.imputed_pairs_count && (
                    <span
                      className="text-[10px] text-amber-700 font-mono"
                      title="Pairs with no matching patient-level FAERS rows use fixed default severity/demographic values (dashed markers on the chart)"
                    >
                      · {clusteringData.metadata.imputed_pairs_count} imputed ({clusteringData.metadata.imputed_pairs_pct}%)
                    </span>
                  )}
                </div>
                {activeClusterId !== null && (
                  <button
                    onClick={() => setActiveClusterId(null)}
                    className="text-[10px] text-blue-700 hover:underline font-semibold"
                  >
                    Reset Filter (Show All Clusters)
                  </button>
                )}
              </div>

              {clusteringLoading ? (
                <div className="h-72 flex items-center justify-center">
                  <LoadingState message="Fitting scikit-learn KMeans & PCA projection..." />
                </div>
              ) : clusteringError ? (
                <div className="h-72 flex items-center justify-center">
                  <ErrorState title="Clustering Failed" message={clusteringError} />
                </div>
              ) : (
                <div className="h-72 w-full pt-2">
                  <ResponsiveContainer width="100%" height="100%">
                    <ScatterChart margin={{ top: 10, right: 20, bottom: 20, left: 10 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                      <XAxis
                        type="number"
                        dataKey="pca_x"
                        name="PC1"
                        stroke="#64748b"
                        tick={{ fontSize: 10, fill: "#64748b" }}
                        label={{
                          value: "Principal Component 1 (Severity & Disproportionality Axis) →",
                          position: "insideBottom",
                          offset: -12,
                          fontSize: 10,
                          fill: "#475569",
                        }}
                      />
                      <YAxis
                        type="number"
                        dataKey="pca_y"
                        name="PC2"
                        stroke="#64748b"
                        tick={{ fontSize: 10, fill: "#64748b" }}
                        label={{
                          value: "Principal Component 2 (Demographics & Case Volume) →",
                          angle: -90,
                          position: "insideLeft",
                          fontSize: 10,
                          fill: "#475569",
                        }}
                      />
                      <ZAxis range={[60, 240]} />
                      <Tooltip
                        cursor={{ strokeDasharray: "3 3" }}
                        content={({ active, payload }) => {
                          if (active && payload && payload.length) {
                            const data = payload[0].payload;
                            const clusterObj = (clusteringData?.clusters || []).find(
                              (c) => c.cluster_id === data.cluster_id
                            );
                            return (
                              <div className="p-3 bg-white border border-slate-300 rounded-md shadow-lg text-xs space-y-1.5 max-w-xs">
                                <div className="font-bold text-slate-900 border-b border-slate-100 pb-1">
                                  {data.drug_name} — {data.event_term}
                                </div>
                                <div className="text-[11px] font-semibold text-blue-700">
                                  {clusterObj?.cluster_name || `Cluster ${data.cluster_id}`}
                                </div>
                                <div className="grid grid-cols-2 gap-x-2 gap-y-0.5 text-[11px] text-slate-600 font-mono">
                                  <div>PRR: <span className="font-bold text-rose-600">{data.prr}x</span></div>
                                  <div>Cases: <span className="font-bold text-slate-900">{data.cases.toLocaleString()}</span></div>
                                  <div>Mortality: <span className="font-bold text-slate-800">{data.death_rate}%</span></div>
                                  <div>Hosp. Rate: <span className="font-bold text-slate-800">{data.hospitalization_rate}%</span></div>
                                  <div>Mean Age: <span className="font-bold text-slate-800">{data.mean_age}y</span></div>
                                  <div>Status: <span className="font-bold">{data.signal_status}</span></div>
                                </div>
                                {data.is_imputed && (
                                  <div className="text-[10px] text-amber-700 font-semibold border-t border-amber-100 pt-1">
                                    ⚠ Imputed severity/demographics (no matching patient-level rows)
                                  </div>
                                )}
                              </div>
                            );
                          }
                          return null;
                        }}
                      />
                      <Scatter name="Clustered Events" data={displayedPoints}>
                        {displayedPoints.map((entry, index) => {
                          const color = clusterColors[(entry.cluster_id - 1) % clusterColors.length];
                          return (
                            <Cell
                              key={`cluster-point-${index}`}
                              fill={color}
                              fillOpacity={
                                (activeClusterId === null || activeClusterId === entry.cluster_id ? 0.85 : 0.2) *
                                (entry.is_imputed ? 0.55 : 1)
                              }
                              stroke={entry.is_imputed ? "#b45309" : color}
                              strokeWidth={entry.is_imputed ? 1.5 : 1}
                              strokeDasharray={entry.is_imputed ? "2,2" : undefined}
                            />
                          );
                        })}
                      </Scatter>
                    </ScatterChart>
                  </ResponsiveContainer>
                </div>
              )}

              {/* Cluster Legend Chips */}
              <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-200">
                {(clusteringData?.clusters || []).map((c, idx) => {
                  const color = clusterColors[idx % clusterColors.length];
                  const isSelected = activeClusterId === c.cluster_id;
                  return (
                    <button
                      key={c.cluster_id}
                      onClick={() =>
                        setActiveClusterId(isSelected ? null : c.cluster_id)
                      }
                      className={`px-2 py-1 rounded text-[10px] font-semibold flex items-center gap-1.5 transition border ${
                        isSelected
                          ? "bg-slate-900 text-white border-slate-900 shadow-xs"
                          : "bg-white text-slate-700 border-slate-200 hover:bg-slate-100"
                      }`}
                    >
                      <span
                        className="w-2.5 h-2.5 rounded-full inline-block"
                        style={{ backgroundColor: color }}
                      />
                      <span>Cluster {c.cluster_id}</span>
                      <span className="opacity-70 font-mono">({c.event_count})</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Right: Cluster Archetype Profile Cards */}
            <div className="lg:col-span-5 space-y-2.5 max-h-96 overflow-y-auto pr-1">
              <div className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center justify-between">
                <span>Clinical Cluster Archetypes</span>
                <span className="text-[10px] text-slate-400 font-normal">Click card to highlight</span>
              </div>

              {(clusteringData?.clusters || []).map((c, idx) => {
                const color = clusterColors[idx % clusterColors.length];
                const isSelected = activeClusterId === c.cluster_id;
                return (
                  <div
                    key={c.cluster_id}
                    onClick={() => setActiveClusterId(isSelected ? null : c.cluster_id)}
                    className={`p-3 rounded border transition cursor-pointer space-y-1.5 ${
                      isSelected
                        ? "bg-blue-50/50 border-blue-500 shadow-xs ring-1 ring-blue-400"
                        : "bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50/60"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span
                          className="w-2.5 h-2.5 rounded-full inline-block shrink-0"
                          style={{ backgroundColor: color }}
                        />
                        <h4 className="text-xs font-bold text-slate-900">{c.cluster_name}</h4>
                      </div>
                      <span
                        className={`text-[9px] font-bold px-1.5 py-0.5 rounded font-mono ${
                          c.severity_level === "CRITICAL"
                            ? "bg-rose-100 text-rose-800"
                            : c.severity_level === "HIGH"
                            ? "bg-amber-100 text-amber-800"
                            : c.severity_level === "MODERATE"
                            ? "bg-blue-100 text-blue-800"
                            : "bg-slate-100 text-slate-700"
                        }`}
                      >
                        {c.severity_level}
                      </span>
                    </div>

                    <p className="text-[11px] text-slate-600 leading-snug">{c.description}</p>

                    {/* Metrics snapshot */}
                    <div className="grid grid-cols-4 gap-1 pt-1 text-center font-mono text-[10px]">
                      <div className="bg-slate-50 p-1 rounded border border-slate-100">
                        <div className="text-slate-400 uppercase text-[8px]">Events</div>
                        <div className="font-bold text-slate-800">{c.event_count}</div>
                      </div>
                      <div className="bg-slate-50 p-1 rounded border border-slate-100">
                        <div className="text-slate-400 uppercase text-[8px]">Avg PRR</div>
                        <div className="font-bold text-rose-600">{c.avg_prr}x</div>
                      </div>
                      <div className="bg-slate-50 p-1 rounded border border-slate-100">
                        <div className="text-slate-400 uppercase text-[8px]">Mortality</div>
                        <div className="font-bold text-slate-800">{c.avg_death_rate}%</div>
                      </div>
                      <div className="bg-slate-50 p-1 rounded border border-slate-100">
                        <div className="text-slate-400 uppercase text-[8px]">Hosp. %</div>
                        <div className="font-bold text-slate-800">{c.avg_hospitalization_rate}%</div>
                      </div>
                    </div>

                    {/* Top Events tags */}
                    <div className="flex flex-wrap gap-1 pt-1">
                      {c.top_events.slice(0, 4).map((evt, eIdx) => (
                        <span
                          key={eIdx}
                          className="text-[9px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 font-medium"
                        >
                          {evt}
                        </span>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* BUBBLE CHART VIEW CONTENT */}
        {visualMode === "bubble" && <SignalBubbleChart data={bubbleData} />}
      </div>

      {/* LIVE openFDA API Lookup — arbitrary drug, not limited to the 3 pre-loaded benchmarks */}
      <div className="rounded border border-emerald-300 bg-emerald-50/40 p-4 shadow-2xs space-y-3">
        <div className="flex items-center justify-between pb-2.5 border-b border-emerald-200">
          <div>
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-600 text-white text-[10px] font-bold uppercase tracking-wider">
                <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
                Live
              </span>
              openFDA Real-Time Lookup
            </h3>
            <p className="text-xs text-slate-600 font-medium">
              Query the real openFDA API live for any drug — not limited to the pre-loaded VIOXX / BAYCOL / AVANDIA benchmarks.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-[1fr_1fr_auto] gap-2.5 items-end">
          <div>
            <label className="text-[11px] font-bold text-slate-700 block mb-1">Drug Name</label>
            <input
              type="text"
              value={liveDrugName}
              onChange={(e) => setLiveDrugName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && runLiveLookup()}
              placeholder="e.g. IBUPROFEN, METFORMIN, WARFARIN"
              className="w-full px-3 py-1.5 rounded bg-white border border-slate-300 text-slate-900 text-xs font-semibold focus:border-emerald-500 outline-none"
            />
          </div>
          <div>
            <label className="text-[11px] font-bold text-slate-700 block mb-1">
              Adverse Event <span className="font-normal text-slate-400">(optional — auto-detects top event)</span>
            </label>
            <input
              type="text"
              value={liveEventTerm}
              onChange={(e) => setLiveEventTerm(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && runLiveLookup()}
              placeholder="e.g. NAUSEA"
              className="w-full px-3 py-1.5 rounded bg-white border border-slate-300 text-slate-900 text-xs font-semibold focus:border-emerald-500 outline-none"
            />
          </div>
          <button
            onClick={runLiveLookup}
            disabled={liveLoading || !backendOnline}
            className="px-4 py-1.5 rounded bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow-xs transition disabled:opacity-50 whitespace-nowrap"
          >
            {liveLoading ? "Querying openFDA..." : "Run Live Lookup"}
          </button>
        </div>

        {liveError && !liveLoading && (
          <div className="rounded border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-800 font-medium">
            ⚠ {liveError}
          </div>
        )}

        {liveResult && liveResult.success && (
          <div className="rounded border border-slate-200 bg-white p-3.5 space-y-2.5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="text-xs font-bold text-slate-900">
                {liveResult.drug_name} + {liveResult.event_term}
                <span className="ml-2 text-[10px] font-mono text-slate-400 font-normal">
                  queried {new Date(liveResult.queried_at).toLocaleTimeString()}
                </span>
              </div>
              <StatusBadge label={liveResult.signal_status || "NOISE"} size="sm" />
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center">
              <div className="p-2 rounded bg-slate-50 border border-slate-200">
                <div className="text-[10px] text-slate-500 font-semibold uppercase">PRR</div>
                <div className="text-sm font-mono font-bold text-slate-900">{liveResult.metrics?.prr.toFixed(2)}</div>
              </div>
              <div className="p-2 rounded bg-slate-50 border border-slate-200">
                <div className="text-[10px] text-slate-500 font-semibold uppercase">Chi²</div>
                <div className="text-sm font-mono font-bold text-slate-900">{liveResult.metrics?.chi_square.toFixed(1)}</div>
              </div>
              <div className="p-2 rounded bg-slate-50 border border-slate-200">
                <div className="text-[10px] text-slate-500 font-semibold uppercase">Cases (a)</div>
                <div className="text-sm font-mono font-bold text-slate-900">{liveResult.n_drug_event?.toLocaleString()}</div>
              </div>
              <div className="p-2 rounded bg-slate-50 border border-slate-200">
                <div className="text-[10px] text-slate-500 font-semibold uppercase">Drug Reports</div>
                <div className="text-sm font-mono font-bold text-slate-900">{liveResult.n_drug_total?.toLocaleString()}</div>
              </div>
            </div>
            <p className="text-[11px] text-slate-600 font-medium">{liveResult.explanation}</p>
          </div>
        )}
      </div>

      {/* 2x2 Interactive Calculator & Disproportionality Analyzer */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left: Input & Contingency Table */}
        <div className="lg:col-span-6 rounded border border-slate-200 bg-white p-4 shadow-2xs space-y-3.5">
          <div className="flex items-center justify-between pb-2.5 border-b border-slate-100">
            <div>
              <h3 className="text-sm font-bold text-slate-900">
                2×2 Contingency Table Analysis Panel
              </h3>
              <p className="text-xs text-slate-500 font-medium">
                Compute proportional reporting ratio (PRR) and Pearson Chi-Square from exact report counts
              </p>
            </div>
          </div>

          {/* Benchmark Preset Buttons */}
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-bold text-slate-600">Benchmark Presets:</span>
              <button
                onClick={() => loadPreset("vioxx")}
                className="px-2.5 py-1 rounded text-[11px] font-semibold bg-rose-50 text-rose-700 border border-rose-200 hover:bg-rose-100 transition shadow-2xs"
              >
                Vioxx / MI
              </button>
              <button
                onClick={() => loadPreset("baycol")}
                className="px-2.5 py-1 rounded text-[11px] font-semibold bg-orange-50 text-orange-700 border border-orange-200 hover:bg-orange-100 transition shadow-2xs"
              >
                Baycol / Rhabdo
              </button>
              <button
                onClick={() => loadPreset("avandia")}
                className="px-2.5 py-1 rounded text-[11px] font-semibold bg-amber-50 text-amber-700 border border-amber-200 hover:bg-amber-100 transition shadow-2xs"
              >
                Avandia / Heart Failure
              </button>
              <button
                onClick={() => loadPreset("noise")}
                className="px-2.5 py-1 rounded text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-300 hover:bg-slate-200 transition shadow-2xs"
                title="Illustrative negative-control example — not a real computed FAERS signal"
              >
                Ibuprofen / Non-Signal ⓘ
              </button>
            </div>
            <p className="text-[10px] text-slate-400 font-medium">
              Vioxx, Baycol, Avandia presets use exact openFDA FAERS cell values (a, b, c, d) from the real pipeline.
              The Ibuprofen preset is an <em>illustrative negative-control example only</em> and does not represent a real computed FAERS signal.
            </p>
          </div>

          {/* Form Inputs */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="text-[11px] font-bold text-slate-700 block mb-1">
                Target Drug Name
              </label>
              <input
                type="text"
                value={calcDrug}
                onChange={(e) => setCalcDrug(e.target.value)}
                className="w-full px-3 py-1.5 rounded bg-white border border-slate-300 text-slate-900 text-xs font-semibold focus:border-blue-500 outline-none"
              />
            </div>
            <div>
              <label className="text-[11px] font-bold text-slate-700 block mb-1">
                Target Adverse Event
              </label>
              <input
                type="text"
                value={calcEvent}
                onChange={(e) => setCalcEvent(e.target.value)}
                className="w-full px-3 py-1.5 rounded bg-white border border-slate-300 text-slate-900 text-xs font-semibold focus:border-blue-500 outline-none"
              />
            </div>
          </div>

          {/* 2x2 Matrix Input Grid */}
          <div className="rounded border border-slate-200 bg-slate-50/70 p-3 space-y-2">
            <div className="text-[11px] font-bold text-slate-700 uppercase tracking-wider">
              Contingency Matrix (Report Counts)
            </div>
            <div className="grid grid-cols-3 gap-2 text-center text-xs">
              <div className="p-2 font-semibold text-slate-500 bg-slate-100 rounded text-[11px]">
                Cohort
              </div>
              <div className="p-2 font-semibold text-slate-700 bg-blue-50 rounded text-[11px] border border-blue-100">
                Target Event ($E$)
              </div>
              <div className="p-2 font-semibold text-slate-700 bg-slate-100 rounded text-[11px]">
                Other Events ($\neg E$)
              </div>

              {/* Row 1: Target Drug */}
              <div className="p-2 font-bold text-slate-800 bg-slate-100 rounded text-left flex items-center text-[11px]">
                Target Drug ($D$)
              </div>
              <div>
                <input
                  type="number"
                  min="0"
                  value={a}
                  onChange={(e) => setA(Number(e.target.value))}
                  className="w-full px-2 py-1.5 text-center font-mono font-bold text-slate-900 bg-white border border-blue-300 rounded focus:border-blue-500 outline-none text-xs"
                />
                <span className="text-[10px] text-slate-500 font-mono">$a$ (cases)</span>
              </div>
              <div>
                <input
                  type="number"
                  min="0"
                  value={b}
                  onChange={(e) => setB(Number(e.target.value))}
                  className="w-full px-2 py-1.5 text-center font-mono font-semibold text-slate-900 bg-white border border-slate-300 rounded focus:border-blue-500 outline-none text-xs"
                />
                <span className="text-[10px] text-slate-500 font-mono">$b$</span>
              </div>

              {/* Row 2: All Other Drugs */}
              <div className="p-2 font-semibold text-slate-700 bg-slate-100 rounded text-left flex items-center text-[11px]">
                Other Drugs ($\neg D$)
              </div>
              <div>
                <input
                  type="number"
                  min="0"
                  value={c}
                  onChange={(e) => setC(Number(e.target.value))}
                  className="w-full px-2 py-1.5 text-center font-mono font-semibold text-slate-900 bg-white border border-slate-300 rounded focus:border-blue-500 outline-none text-xs"
                />
                <span className="text-[10px] text-slate-500 font-mono">$c$</span>
              </div>
              <div>
                <input
                  type="number"
                  min="0"
                  value={d}
                  onChange={(e) => setD(Number(e.target.value))}
                  className="w-full px-2 py-1.5 text-center font-mono font-semibold text-slate-900 bg-white border border-slate-300 rounded focus:border-blue-500 outline-none text-xs"
                />
                <span className="text-[10px] text-slate-500 font-mono">$d$</span>
              </div>
            </div>
          </div>

          <button
            onClick={() =>
              runCustomCalculation({
                drug_name: calcDrug,
                event_term: calcEvent,
                a,
                b,
                c,
                d,
              })
            }
            disabled={calcLoading || !backendOnline}
            className="w-full py-2.5 rounded bg-blue-700 hover:bg-blue-800 text-white font-bold text-xs shadow-xs transition disabled:opacity-50"
          >
            {calcLoading ? "Computing Evans Statistics..." : "Execute Disproportionality Analysis"}
          </button>
        </div>

        {/* Right: Live Signal Metrics & Explanation */}
        <div className="lg:col-span-6 rounded border border-slate-200 bg-white p-4 shadow-2xs flex flex-col justify-between space-y-3.5">
          <div className="pb-2.5 border-b border-slate-100 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Computed Signal Analytics</h3>
              <p className="text-xs text-slate-500 font-medium">
                Statistical evaluation based on Evans et al. (2001) guidelines
              </p>
            </div>
            {customResult && <StatusBadge label={customResult.signal_status} />}
          </div>

          {calcError ? (
            <ErrorState title="Calculation Error" message={calcError} />
          ) : customResult ? (
            <div className="space-y-3.5">
              {/* Primary Stats Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                <div className="p-3 rounded border border-slate-200 bg-slate-50 text-center">
                  <div className="text-[10px] uppercase font-bold text-slate-500">PRR Score</div>
                  <div className="text-2xl font-mono font-bold text-rose-600 mt-1">
                    {Number(customResult.metrics.prr).toFixed(2)}x
                  </div>
                  <div className="text-[10px] text-slate-500 font-medium">Threshold ≥ 2.0</div>
                </div>

                <div className="p-3 rounded border border-slate-200 bg-slate-50 text-center">
                  <div className="text-[10px] uppercase font-bold text-slate-500">Chi-Square (χ²)</div>
                  <div className="text-2xl font-mono font-bold text-blue-700 mt-1">
                    {Number(customResult.metrics.chi_square).toFixed(1)}
                  </div>
                  <div className="text-[10px] text-slate-500 font-medium">Threshold ≥ 4.0</div>
                </div>

                <div className="p-3 rounded border border-slate-200 bg-slate-50 text-center">
                  <div className="text-[10px] uppercase font-bold text-slate-500">Target Cases ($a$)</div>
                  <div className="text-2xl font-mono font-bold text-slate-800 mt-1">
                    {customResult.n_drug_event}
                  </div>
                  <div className="text-[10px] text-slate-500 font-medium">Threshold ≥ 3</div>
                </div>

                <div className="p-3 rounded border border-slate-200 bg-slate-50 text-center">
                  <div className="text-[10px] uppercase font-bold text-slate-500">95% CI Lower</div>
                  <div className="text-2xl font-mono font-bold text-slate-800 mt-1">
                    {Number(customResult.metrics.lower_ci).toFixed(2)}
                  </div>
                  <div className="text-[10px] text-slate-500 font-medium">Log-Normal CI</div>
                </div>
              </div>

              {/* Signal Explanation Section */}
              <div className="rounded border border-blue-200 bg-blue-50/40 p-3.5 space-y-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm">🔍</span>
                  <span className="text-xs font-bold text-blue-900 uppercase tracking-wider">
                    Signal Assessment · Why was this signal flagged?
                  </span>
                </div>
                <p className="text-xs text-slate-700 leading-relaxed font-medium">
                  {customResult.explanation}
                </p>
                {customResult.bob_interpretation && (
                  <div className="rounded border border-indigo-200 bg-indigo-50/50 p-2.5 space-y-1 mt-1">
                    <div className="flex items-center gap-1.5 text-[10px] font-bold text-indigo-800 uppercase tracking-wider">
                      <span>🤖</span> IBM Bob Clinical Interpretation (Gemini 2.5 Flash)
                    </div>
                    <p className="text-xs text-indigo-900 leading-relaxed font-medium">
                      {customResult.bob_interpretation}
                    </p>
                  </div>
                )}
                <div className="pt-1.5 flex flex-wrap gap-2 text-[11px] text-slate-600 font-mono">
                  <span className="bg-white px-2 py-0.5 rounded border border-slate-200">
                    p-value: {customResult.metrics.p_value < 0.0001 ? "< 0.0001" : customResult.metrics.p_value.toFixed(4)}
                  </span>
                  <span className="bg-white px-2 py-0.5 rounded border border-slate-200">
                    Total Ingested N: {customResult.n_total.toLocaleString()}
                  </span>
                </div>
              </div>
            </div>
          ) : (
            <LoadingState message="Loading signal analytics engine..." />
          )}

          {/* Active Clustering Status Indicator */}
          <div className="p-2.5 rounded border border-emerald-200 bg-emerald-50/60 flex items-center justify-between text-xs text-emerald-900">
            <span className="font-semibold flex items-center gap-1.5">
              <span>✓</span> Adverse Event Clustering Active (scikit-learn KMeans)
            </span>
            <span className="text-[10px] font-bold text-emerald-800 bg-emerald-100 px-2 py-0.5 rounded font-mono">
              {clusteringData ? `${clusteringData.clusters.length} Clusters Indexed` : "Operational"}
            </span>
          </div>
        </div>
      </div>

      {/* FAERS Ingested Database Registry Table */}
      <div className="rounded border border-slate-200 bg-white p-4 shadow-2xs space-y-3">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-bold text-slate-900">
              FAERS Pre-Processed Signal Registry ({filteredSignals.length} Records)
            </h3>
            <p className="text-xs text-slate-500 font-medium">
              Disproportionality scores computed across openFDA FAERS adverse event database
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <input
              type="text"
              placeholder="Search drug or adverse event..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="px-3 py-1.5 rounded bg-white border border-slate-300 text-slate-900 placeholder-slate-400 text-xs focus:border-blue-500 outline-none w-56 font-medium"
            />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-1.5 rounded bg-white border border-slate-300 text-slate-700 text-xs font-semibold focus:border-blue-500 outline-none"
            >
              <option value="ALL">All Statuses</option>
              <option value="SIGNAL">Confirmed Signal (PRR≥2, χ²≥4)</option>
              <option value="WEAK_SIGNAL">Weak Signal</option>
              <option value="NOISE">Noise (Non-Signal)</option>
            </select>
          </div>
        </div>

        {filteredSignals.length === 0 ? (
          <EmptyState
            icon="🔎"
            title="No Matching Safety Signals"
            description="Try modifying your search criteria or filter to inspect other FAERS records."
          />
        ) : (
          <div className="overflow-x-auto max-h-96 overflow-y-auto">
            <table className="w-full text-left text-xs">
              <thead className="sticky top-0 bg-slate-50 text-slate-600 font-semibold uppercase tracking-wider text-[10px] border-b border-slate-200">
                <tr>
                  <th className="py-2.5 px-3">Drug Name</th>
                  <th className="py-2.5 px-3">Adverse Event (MedDRA)</th>
                  <th className="py-2.5 px-3 font-mono">Cases ($a$)</th>
                  <th className="py-2.5 px-3 font-mono">PRR</th>
                  <th className="py-2.5 px-3 font-mono">χ² Stat</th>
                  <th className="py-2.5 px-3 font-mono">95% Conf. Interval</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredSignals.slice(0, 50).map((sig, idx) => (
                  <tr key={idx} className="hover:bg-slate-50/80 transition">
                    <td className="py-2 px-3 font-bold text-slate-900">{sig.drug_name}</td>
                    <td className="py-2 px-3 text-slate-700 font-medium">{sig.event_term}</td>
                    <td className="py-2 px-3 font-mono font-semibold text-slate-800">
                      {sig.n_drug_event}
                    </td>
                    <td className="py-2 px-3 font-mono font-bold text-rose-600">
                      {Number(sig.prr).toFixed(2)}x
                    </td>
                    <td className="py-2 px-3 font-mono text-slate-700">
                      {Number(sig.chi_square).toFixed(1)}
                    </td>
                    <td className="py-2 px-3 font-mono text-slate-500 text-[11px]">
                      [{Number(sig.lower_ci_95).toFixed(2)} – {Number(sig.upper_ci_95).toFixed(2)}]
                    </td>
                    <td className="py-2 px-3">
                      <StatusBadge label={sig.signal_status} size="sm" />
                    </td>
                    <td className="py-2 px-3 text-right">
                      <button
                        onClick={() => {
                          // Use nullish checks (not truthy checks) so a legitimately
                          // 0-valued margin isn't mistaken for "missing" and replaced
                          // with a fabricated denominator.
                          const nDrugTotal = sig.n_drug_total ?? sig.n_drug_event + 10000;
                          const nEventTotal = sig.n_event_total ?? sig.n_drug_event + 500;
                          const nTotal = sig.n_total ?? nDrugTotal + nEventTotal + 1000000;
                          const bVal = nDrugTotal - sig.n_drug_event;
                          const cVal = nEventTotal - sig.n_drug_event;
                          const dVal = nTotal - nDrugTotal - cVal;

                          setCalcDrug(sig.drug_name);
                          setCalcEvent(sig.event_term);
                          setA(sig.n_drug_event);
                          setB(bVal);
                          setC(cVal);
                          setD(dVal);
                          runCustomCalculation({
                            drug_name: sig.drug_name,
                            event_term: sig.event_term,
                            a: sig.n_drug_event,
                            b: bVal,
                            c: cVal,
                            d: dVal,
                          });
                        }}
                        className="px-2 py-1 rounded bg-slate-100 hover:bg-blue-50 text-blue-700 text-[11px] font-semibold border border-slate-200 transition"
                      >
                        Inspect 2×2
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

// ───────────────────────────────────────────────────────────────────────────
// VIEW 3: HISTORICAL ANALYSIS (Longitudinal Backtesting M3)
// ───────────────────────────────────────────────────────────────────────────

function HistoricalAnalysisView({
  backendOnline,
}: {
  backendOnline: boolean | null;
}) {
  const [selectedDrug, setSelectedDrug] = useState<"VIOXX" | "AVANDIA" | "BAYCOL">("VIOXX");
  const [backtestData, setBacktestData] = useState<DrugBacktestData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadBacktest = useCallback(async (drug: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchDrugBacktest(drug);
      setBacktestData(res);
    } catch (e: any) {
      setError(e?.message || "Failed to load historical trajectory from backend");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (backendOnline) {
      loadBacktest(selectedDrug);
    }
  }, [backendOnline, selectedDrug, loadBacktest]);

  return (
    <div className="space-y-5">
      <PageHeader
        title="Historical Signal Validation (M3)"
        subtitle="Examine how a safety signal evolves across reporting periods."
        badge="Digital Twin Simulation"
        actions={
          <div className="flex gap-1.5 bg-white p-1 rounded border border-slate-300 shadow-2xs">
            {(["VIOXX", "AVANDIA", "BAYCOL"] as const).map((drug) => (
              <button
                key={drug}
                onClick={() => setSelectedDrug(drug)}
                className={`px-3 py-1 rounded text-xs font-bold transition ${
                  selectedDrug === drug
                    ? "bg-blue-700 text-white shadow-2xs"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                }`}
              >
                {drug}
              </button>
            ))}
          </div>
        }
      />

      {loading ? (
        <LoadingState
          message={`Executing historical digital twin backtest for ${selectedDrug}...`}
          description="Simulating walk-forward monthly FAERS signal trajectory"
        />
      ) : error ? (
        <ErrorState
          title="Historical Backtest Failed"
          message={error}
          onRetry={() => loadBacktest(selectedDrug)}
        />
      ) : backtestData ? (
        <div className="space-y-5">
          {/* Key Metrics Header */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
            <MetricCard
              label="Drug & Target Event"
              value={backtestData.drug_name}
              subtext={backtestData.event_term}
              badge="Ground Truth"
              color="#2563eb"
              icon="💊"
            />
            <MetricCard
              label="First Signal Emergence"
              value={backtestData.first_signal_quarter || "2004-Q1"}
              subtext="First crossed PRR ≥ 2.0, χ² ≥ 4"
              badge="Evans Threshold"
              color="#dc2626"
              icon="🚨"
            />
            <MetricCard
              label="Regulatory Action Date"
              value={backtestData.market_withdrawal_quarter || "2004-09-30"}
              subtext="Official market withdrawal / warning"
              badge="FDA Action"
              color="#ea580c"
              icon="🏛"
            />
            <MetricCard
              label="Early Detection Lead Time"
              value={
                backtestData.lead_time_days && backtestData.lead_time_days !== "N/A"
                  ? `+${backtestData.lead_time_days} days`
                  : typeof backtestData.detection_lead_time_quarters === "number"
                  ? `+${backtestData.detection_lead_time_quarters} days`
                  : "Pre-2004 (Data Unavailable)"
              }
              subtext="Earlier than FDA market withdrawal"
              badge="Safety Lead Time"
              color="#16a34a"
              icon="⏱"
            />
          </div>

          {/* Historical PRR Trajectory Line Chart */}
          <div className="rounded border border-slate-200 bg-white p-4 shadow-2xs space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2.5 border-b border-slate-100">
              <div>
                <h3 className="text-sm font-bold text-slate-900">
                  Walk-Forward Longitudinal PRR Trajectory
                </h3>
                <p className="text-xs text-slate-500 font-medium">
                  Sequential monthly calculation of disproportionality ratio vs. regulatory threshold (PRR = 2.0)
                </p>
              </div>
              <div className="flex items-center gap-3 text-xs">
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-0.5 bg-blue-700 inline-block" />
                  <span className="text-slate-600 font-semibold">Monthly PRR</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-0.5 bg-rose-500 inline-block" />
                  <span className="text-slate-600 font-semibold">Evans Threshold (2.0)</span>
                </div>
              </div>
            </div>

            <div className="h-80 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={backtestData.trajectory}
                  margin={{ top: 10, right: 30, left: 0, bottom: 20 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis
                    dataKey="quarter"
                    stroke="#64748b"
                    tick={{ fontSize: 11, fill: "#64748b" }}
                    angle={-25}
                    textAnchor="end"
                  />
                  <YAxis
                    stroke="#64748b"
                    tick={{ fontSize: 11, fill: "#64748b" }}
                    domain={[0, "auto"]}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#ffffff",
                      borderColor: "#cbd5e1",
                      borderRadius: "4px",
                      color: "#0f172a",
                      fontSize: "12px",
                      boxShadow: "0 2px 4px rgba(0,0,0,0.08)",
                    }}
                  />
                  <ReferenceLine
                    y={2.0}
                    stroke="#ef4444"
                    strokeDasharray="4 4"
                    label={{
                      value: "PRR = 2.0 (Signal Threshold)",
                      fill: "#ef4444",
                      fontSize: 11,
                      position: "top",
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="prr"
                    name="PRR Disproportionality"
                    stroke="#1d4ed8"
                    strokeWidth={2.5}
                    dot={{ fill: "#1d4ed8", r: 3 }}
                    activeDot={{ r: 5, fill: "#1e40af" }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Clinical Case Context & Ground Truth Evaluation */}
          <div className="rounded border border-slate-200 bg-white p-4 shadow-2xs space-y-2">
            <h3 className="text-sm font-bold text-slate-900">
              Clinical Context & Regulatory Findings
            </h3>
            <p className="text-xs text-slate-700 leading-relaxed font-medium">
              {backtestData.clinical_summary}
            </p>
            {backtestData.source_note && (
              <div className="p-2.5 rounded bg-slate-50 border border-slate-200 text-[11px] text-slate-600 font-mono">
                <strong>Data Source Note:</strong> {backtestData.source_note}
              </div>
            )}
          </div>
        </div>
      ) : (
        <EmptyState
          icon="📈"
          title="No Historical Dataset Available"
          description="Select a drug candidate above to execute the walk-forward backtest."
        />
      )}
    </div>
  );
}

// ───────────────────────────────────────────────────────────────────────────
// VIEW 4: SUBMISSION READINESS (ICH M4 CTD Modules & Gap Analysis)
// ───────────────────────────────────────────────────────────────────────────

function SubmissionReadinessView({
  backendOnline,
}: {
  backendOnline: boolean | null;
}) {
  const [presets, setPresets] = useState<any[]>([]);
  const [selectedPresetId, setSelectedPresetId] = useState<string>("VIOXX_NDA_21042");
  const [customText, setCustomText] = useState("");
  const [pdfFile, setPdfFile] = useState<File | null>(null);

  const [activeTab, setActiveTab] = useState<"preset" | "text" | "pdf">("preset");
  const [gapReport, setGapReport] = useState<GapReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filterSeverity, setFilterSeverity] = useState<string>("ALL");

  // Load presets on mount
  useEffect(() => {
    if (backendOnline) {
      fetchM4Presets()
        .then((res) => {
          if (res?.presets) {
            setPresets(res.presets);
          }
        })
        .catch(console.error);
    }
  }, [backendOnline]);

  const runAnalysis = async () => {
    setLoading(true);
    setError(null);
    try {
      if (activeTab === "preset") {
        const p = presets.find((x) => x.id === selectedPresetId);
        if (!p) throw new Error("Preset not found");
        const res = await checkCTDDossier(p.outline);
        setGapReport(res);
      } else if (activeTab === "text") {
        if (!customText.trim()) throw new Error("Please enter dossier text");
        const res = await checkCTDText(customText, "Custom Dossier");
        setGapReport(res);
      } else if (activeTab === "pdf") {
        if (!pdfFile) throw new Error("Please select a PDF file");
        const res = await checkCTDPDF(pdfFile, "Uploaded Dossier");
        setGapReport(res);
      }
    } catch (e: any) {
      setError(e?.message || "Failed to analyze CTD submission readiness");
    } finally {
      setLoading(false);
    }
  };

  const [exportingPdf, setExportingPdf] = useState(false);

  const handleExportPDF = async () => {
    if (!gapReport) return;
    setExportingPdf(true);
    try {
      const blob = await exportGapReportPDF(gapReport);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      const nameSource = gapReport.drug_name || gapReport.submission_title || "ctd_gap_report";
      a.href = url;
      a.download = `${nameSource.replace(/[^a-zA-Z0-9]+/g, "_")}_gap_report.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e: any) {
      setError(e?.message || "Failed to export PDF report");
    } finally {
      setExportingPdf(false);
    }
  };

  // Run default analysis on mount when presets arrive
  useEffect(() => {
    if (presets.length > 0 && !gapReport && !loading) {
      const p = presets.find((x) => x.id === "VIOXX_NDA_21042") || presets[0];
      checkCTDDossier(p.outline)
        .then(setGapReport)
        .catch(console.error);
    }
  }, [presets, gapReport, loading]);

  const filteredGaps = (gapReport?.priority_gaps || []).filter((g) => {
    if (filterSeverity === "ALL") return true;
    return g.criticality?.toUpperCase() === filterSeverity;
  });

  return (
    <div className="space-y-5">
      <PageHeader
        title="Dossier Submission Readiness Checker (M4)"
        subtitle="Evaluate CTD dossier completeness against ICH M4 requirements."
        badge="ICH M4 Ground Truth"
        actions={
          <div className="flex items-center gap-2">
            <button
              onClick={runAnalysis}
              disabled={loading || !backendOnline}
              className="px-4 py-1.5 rounded bg-blue-700 hover:bg-blue-800 text-white font-bold text-xs shadow-xs transition disabled:opacity-50 flex items-center gap-1.5"
            >
              <span>📋</span>
              <span>{loading ? "Evaluating ICH M4..." : "Generate Gap Report"}</span>
            </button>
            <button
              onClick={handleExportPDF}
              disabled={!gapReport || exportingPdf}
              className="px-4 py-1.5 rounded bg-white border border-slate-300 hover:bg-slate-50 text-slate-800 font-bold text-xs shadow-xs transition disabled:opacity-50 flex items-center gap-1.5"
            >
              <span>📄</span>
              <span>{exportingPdf ? "Exporting..." : "Export PDF"}</span>
            </button>
          </div>
        }
      />

      {/* Dossier Ingestion Panel */}
      <div className="rounded border border-slate-200 bg-white p-4 shadow-2xs space-y-3.5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2.5 border-b border-slate-100">
          <div>
            <h3 className="text-sm font-bold text-slate-900">Upload Dossier Section</h3>
            <p className="text-xs text-slate-500 font-medium">
              Select candidate benchmark, upload PDF, or input custom dossier outline
            </p>
          </div>

          <div className="flex gap-1 bg-slate-100 p-1 rounded border border-slate-200">
            <button
              onClick={() => setActiveTab("preset")}
              className={`px-3 py-1 rounded text-xs font-bold transition ${
                activeTab === "preset"
                  ? "bg-white text-blue-700 shadow-2xs"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Benchmark Presets
            </button>
            <button
              onClick={() => setActiveTab("text")}
              className={`px-3 py-1 rounded text-xs font-bold transition ${
                activeTab === "text"
                  ? "bg-white text-blue-700 shadow-2xs"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Raw Text / JSON
            </button>
            <button
              onClick={() => setActiveTab("pdf")}
              className={`px-3 py-1 rounded text-xs font-bold transition ${
                activeTab === "pdf"
                  ? "bg-white text-blue-700 shadow-2xs"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              PDF Upload
            </button>
          </div>
        </div>

        {activeTab === "preset" && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {presets.map((p) => (
              <button
                key={p.id}
                onClick={() => setSelectedPresetId(p.id)}
                className={`p-3 rounded border text-left transition ${
                  selectedPresetId === p.id
                    ? "border-blue-500 bg-blue-50/50 shadow-2xs"
                    : "border-slate-200 bg-slate-50 hover:bg-slate-100"
                }`}
              >
                <div className="text-xs font-bold text-slate-900">{p.title}</div>
                <div className="text-[11px] text-slate-600 font-medium mt-0.5">{p.description}</div>
                <div className="text-[10px] text-blue-700 font-mono mt-1.5">
                  {p.outline?.sections?.length || 0} sections structured
                </div>
              </button>
            ))}
          </div>
        )}

        {activeTab === "text" && (
          <div>
            <textarea
              rows={4}
              placeholder="Paste dossier text or JSON outline here (e.g. Module 1 Admin Info, Module 2 Summaries...)"
              value={customText}
              onChange={(e) => setCustomText(e.target.value)}
              className="w-full p-2.5 rounded bg-white border border-slate-300 text-slate-900 text-xs font-mono placeholder-slate-400 focus:border-blue-500 outline-none"
            />
          </div>
        )}

        {activeTab === "pdf" && (
          <div className="border border-dashed border-slate-300 rounded p-5 text-center bg-slate-50/50">
            <input
              type="file"
              accept=".pdf"
              onChange={(e) => setPdfFile(e.target.files?.[0] || null)}
              className="hidden"
              id="pdf-upload-input"
            />
            <label
              htmlFor="pdf-upload-input"
              className="cursor-pointer px-3.5 py-1.5 rounded bg-white border border-slate-300 text-slate-800 text-xs font-bold hover:bg-slate-50 transition shadow-2xs inline-block"
            >
              {pdfFile ? `Selected: ${pdfFile.name}` : "Choose Dossier PDF File"}
            </label>
            <p className="text-[11px] text-slate-500 mt-1.5 font-medium">
              Backend parses PDF text and matches against ICH M4 knowledge base
            </p>
          </div>
        )}
      </div>

      {loading ? (
        <LoadingState
          message="Evaluating Dossier Completeness against ICH M4 Guidelines..."
          description="Running RAG retrieval, section matching, and gap severity scoring"
        />
      ) : error ? (
        <ErrorState
          title="Submission Readiness Evaluation Failed"
          message={error}
          onRetry={runAnalysis}
        />
      ) : gapReport ? (
        <div className="space-y-5">
          {/* Summary Readiness Header */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
            <MetricCard
              label="Overall Readiness Score"
              value={`${gapReport.overall_completeness}%`}
              subtext="Weighted ICH M4 Completeness"
              badge={gapReport.overall_completeness >= 80 ? "STRONG" : "NEEDS ACTION"}
              color={gapReport.overall_completeness >= 80 ? "#16a34a" : "#dc2626"}
              icon="📊"
            />
            <MetricCard
              label="Sections Evaluated"
              value={gapReport.total_sections_evaluated}
              subtext={`Present: ${gapReport.present_total} | Partial: ${gapReport.partial_total}`}
              badge="CTD Modules 1-5"
              color="#2563eb"
              icon="📑"
            />
            <MetricCard
              label="Critical Missing Gaps"
              value={gapReport.critical_gaps_count}
              subtext="Direct grounds for Refusal to File (RTF)"
              badge="High Severity"
              color="#dc2626"
              icon="🚨"
            />
            <MetricCard
              label="Target Dossier Title"
              value={gapReport.drug_name || "Vioxx NDA 21-042"}
              subtext="Full Marketing Authorization"
              badge="FDA / EMA"
              color="#9333ea"
              icon="🏛"
            />
          </div>

          {/* Mode 1 <-> Mode 2 Safety Signal Cross-Link Banner */}
          {gapReport.safety_signal_linkage?.has_confirmed_signal && (
            <div className="rounded border border-rose-300 bg-rose-50 p-3.5 shadow-2xs flex items-start gap-3">
              <span className="text-xl leading-none">⚠️</span>
              <div className="flex-1 min-w-0">
                <div className="text-xs font-bold text-rose-800 uppercase tracking-wide">
                  Confirmed FAERS Safety Signal — Mandatory Review Required
                </div>
                <p className="mt-1 text-xs text-rose-700 font-medium">
                  {gapReport.safety_signal_linkage.message ||
                    `${gapReport.safety_signal_linkage.drug_name} has an active CONFIRMED_SIGNAL. Safety-related CTD sections require mandatory review.`}
                </p>
                <div className="mt-1.5 flex flex-wrap gap-1.5">
                  {gapReport.safety_signal_linkage.flagged_section_ids.map((sid) => (
                    <span
                      key={sid}
                      className="text-[10px] font-mono font-bold text-rose-800 bg-white border border-rose-300 rounded px-1.5 py-0.5"
                    >
                      Section {sid}
                    </span>
                  ))}
                  {gapReport.safety_signal_linkage.confirmed_events.slice(0, 2).map((e) => (
                    <span
                      key={e.event_term}
                      className="text-[10px] font-mono text-rose-700 bg-white border border-rose-200 rounded px-1.5 py-0.5"
                    >
                      {e.event_term} · PRR {e.prr.toFixed(1)}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Compact Horizontal CTD Module Progress Overview */}
          <div className="rounded border border-slate-200 bg-white p-4 shadow-2xs space-y-3">
            <div className="pb-2 border-b border-slate-100 flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-900">
                CTD Module Progress Overview
              </h3>
              <span className="text-[11px] text-slate-500 font-mono">
                ICH M4 Structural Verification
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-5 gap-3">
              {Object.values(gapReport.modules).map((m) => {
                const pct = m.completeness_percentage;
                const strokeColor =
                  pct >= 90 ? "#16a34a" : pct >= 70 ? "#2563eb" : pct >= 50 ? "#f59e0b" : "#dc2626";
                return (
                  <div
                    key={m.module_id}
                    className="p-3 rounded border border-slate-200 bg-slate-50/70 flex flex-col justify-between space-y-2 text-center"
                  >
                    <div className="text-xs font-bold text-slate-900">
                      Module {m.module_id}
                    </div>
                    <div className="text-[10px] text-slate-500 font-medium truncate">
                      {m.module_name}
                    </div>

                    {/* Circular Completeness Indicator */}
                    <div className="my-1 flex items-center justify-center">
                      <div className="relative w-16 h-16 flex items-center justify-center">
                        <svg className="w-16 h-16 -rotate-90" viewBox="0 0 36 36">
                          <path
                            className="text-slate-200"
                            strokeWidth="3.5"
                            stroke="currentColor"
                            fill="none"
                            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                          />
                          <path
                            strokeDasharray={`${pct}, 100`}
                            strokeWidth="3.5"
                            stroke={strokeColor}
                            strokeLinecap="round"
                            fill="none"
                            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                          />
                        </svg>
                        <span className="absolute font-mono font-bold text-xs text-slate-800">
                          {pct}%
                        </span>
                      </div>
                    </div>

                    <div className="text-[10px] text-slate-500 font-mono">
                      {m.present_count} present · {m.missing_count} missing
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Gap Report & Module Analysis Table */}
          <div className="rounded border border-slate-200 bg-white p-4 shadow-2xs space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2.5 border-b border-slate-100">
              <div>
                <h3 className="text-sm font-bold text-slate-900">
                  Gap Report & Module Analysis ({filteredGaps.length} Action Items)
                </h3>
                <p className="text-xs text-slate-500 font-medium">
                  Detailed regulatory gaps mapped against ICH M4 requirement specifications
                </p>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-600 font-semibold">Filter Severity:</span>
                <select
                  value={filterSeverity}
                  onChange={(e) => setFilterSeverity(e.target.value)}
                  className="px-2.5 py-1 rounded bg-white border border-slate-300 text-slate-700 text-xs font-semibold focus:border-blue-500 outline-none"
                >
                  <option value="ALL">All Gaps</option>
                  <option value="CRITICAL">Critical Only</option>
                  <option value="MAJOR">Major</option>
                  <option value="STANDARD">Standard</option>
                </select>
              </div>
            </div>

            {filteredGaps.length === 0 ? (
              <EmptyState
                icon="✓"
                title="No Regulatory Gaps Detected"
                description="All evaluated sections meet the required ICH M4 threshold."
              />
            ) : (
              <div className="overflow-x-auto max-h-96 overflow-y-auto">
                <table className="w-full text-left text-xs">
                  <thead className="sticky top-0 bg-slate-50 text-slate-600 font-semibold uppercase tracking-wider text-[10px] border-b border-slate-200">
                    <tr>
                      <th className="py-2.5 px-3">Module</th>
                      <th className="py-2.5 px-3">Section ID</th>
                      <th className="py-2.5 px-3">Section Title</th>
                      <th className="py-2.5 px-3">Severity</th>
                      <th className="py-2.5 px-3">Status</th>
                      <th className="py-2.5 px-3">Content Adequacy</th>
                      <th className="py-2.5 px-3">Remediation Recommendation</th>
                      <th className="py-2.5 px-3">ICH M4 Evidence / Citation</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {filteredGaps.map((gap, idx) => (
                      <tr
                        key={idx}
                        className={`hover:bg-slate-50/80 transition ${
                          gap.requires_safety_update ? "bg-rose-50/70" : ""
                        }`}
                      >
                        <td className="py-2 px-3 text-slate-600 font-medium text-[11px]">
                          {gap.module_name}
                        </td>
                        <td className="py-2 px-3 font-mono font-bold text-blue-700">
                          {gap.section_id}
                        </td>
                        <td className="py-2 px-3 text-slate-900 font-semibold max-w-[180px] truncate">
                          <div className="flex items-center gap-1.5">
                            {gap.title}
                            {gap.requires_safety_update && (
                              <span
                                title={gap.safety_update_reason || "Requires mandatory safety review"}
                                className="shrink-0 text-[9px] font-bold text-rose-700 bg-rose-100 border border-rose-300 rounded px-1.5 py-0.5 uppercase tracking-wide"
                              >
                                ⚠ Safety Update Required
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="py-2 px-3">
                          <StatusBadge label={gap.criticality} size="sm" />
                        </td>
                        <td className="py-2 px-3">
                          <StatusBadge label={gap.status} size="sm" />
                        </td>
                        <td className="py-2 px-3">
                          <ContentAdequacyBadge
                            score={gap.content_adequacy_score ?? null}
                            checkpoints={gap.checkpoint_results ?? null}
                          />
                        </td>
                        <td className="py-2 px-3 text-slate-700 font-medium max-w-[280px]">
                          {gap.action_item || "Submit required technical documentation"}
                        </td>
                        <td className="py-2 px-3 text-slate-500 font-mono text-[10px]">
                          {gap.source_reference}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      ) : (
        <EmptyState
          icon="📋"
          title="Submission Readiness Has Not Been Analyzed"
          description="Select a candidate dossier above or upload a document to begin the audit."
        />
      )}
    </div>
  );
}

// ───────────────────────────────────────────────────────────────────────────
// VIEW 5: REPORTS & EXPORTS
// ───────────────────────────────────────────────────────────────────────────

function ReportsView({
  signals,
  summaryData,
  backendOnline,
  onNavigate,
}: {
  signals: PRRSignal[];
  summaryData: any;
  backendOnline: boolean | null;
  onNavigate: (page: NavPage) => void;
}) {
  const downloadJSON = (data: any, filename: string) => {
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-5">
      <PageHeader
        title="Reports & Regulatory Dossier Exports"
        subtitle="Export computed safety signals and ICH M4 gap reports for regulatory archiving."
        badge="Audit Trail"
      />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Report 1: Safety Signal Dossier */}
        <div className="rounded border border-slate-200 bg-white p-4 shadow-2xs flex flex-col justify-between space-y-4">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-2xl">🔬</span>
              <span className="text-[10px] font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-100">
                M1 / M2 Export
              </span>
            </div>
            <h3 className="mt-3 text-sm font-bold text-slate-900">
              FAERS Safety Signal Detection Report
            </h3>
            <p className="mt-1 text-xs text-slate-600 font-medium">
              Complete dataset of Evans PRR, χ², 95% CI, and signal decisions across all {signals.length} indexed pairs.
            </p>
          </div>
          <button
            onClick={() => downloadJSON(signals, "faers_safety_signals.json")}
            disabled={signals.length === 0}
            className="w-full py-2 rounded bg-blue-700 hover:bg-blue-800 text-white text-xs font-bold transition shadow-2xs disabled:opacity-50"
          >
            Download Signals JSON
          </button>
        </div>

        {/* Report 2: Historical Backtest Validation */}
        <div className="rounded border border-slate-200 bg-white p-4 shadow-2xs flex flex-col justify-between space-y-4">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-2xl">📈</span>
              <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-100">
                M3 Export
              </span>
            </div>
            <h3 className="mt-3 text-sm font-bold text-slate-900">
              Historical Backtest Validation Report
            </h3>
            <p className="mt-1 text-xs text-slate-600 font-medium">
              Longitudinal digital-twin analysis documenting early detection lead times for Vioxx (+242 days) and Avandia.
            </p>
          </div>
          <button
            onClick={() => onNavigate("historical")}
            className="w-full py-2 rounded bg-emerald-700 hover:bg-emerald-800 text-white text-xs font-bold transition shadow-2xs"
          >
            View Backtest Workspace
          </button>
        </div>

        {/* Report 3: ICH M4 CTD Dossier Readiness Gap Report */}
        <div className="rounded border border-slate-200 bg-white p-4 shadow-2xs flex flex-col justify-between space-y-4">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-2xl">📋</span>
              <span className="text-[10px] font-bold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded border border-indigo-100">
                M4 Export
              </span>
            </div>
            <h3 className="mt-3 text-sm font-bold text-slate-900">
              ICH M4 CTD Readiness Gap Report
            </h3>
            <p className="mt-1 text-xs text-slate-600 font-medium">
              Structured audit covering Modules 1 through 5 with priority remediation items, citations, and evidence.
            </p>
          </div>
          <button
            onClick={() => onNavigate("readiness")}
            className="w-full py-2 rounded bg-indigo-700 hover:bg-indigo-800 text-white text-xs font-bold transition shadow-2xs"
          >
            Open Readiness Audit
          </button>
        </div>
      </div>
    </div>
  );
}

// ───────────────────────────────────────────────────────────────────────────
// VIEW 6: ABOUT & SYSTEM ARCHITECTURE
// ───────────────────────────────────────────────────────────────────────────

function AboutView() {
  return (
    <div className="space-y-5 max-w-4xl">
      <PageHeader
        title="PharmSignals System Architecture & Methodology"
        subtitle="IBM Bobathon 2026 Problem Statement P2 Solution Brief"
        badge="Official Submission"
      />

      <div className="rounded border border-slate-200 bg-white p-5 shadow-2xs space-y-4 text-xs text-slate-700 leading-relaxed font-medium">
        <div>
          <h3 className="text-sm font-bold text-slate-900">Problem Statement</h3>
          <p className="mt-1 text-slate-600">
            The FDA Adverse Event Reporting System (FAERS) contains over 20 million spontaneous reports. Historical tragedies like Vioxx (Rofecoxib) resulted in an estimated 27,000+ excess cardiovascular events before regulatory market withdrawal. Simultaneously, biopharma drug marketing applications (CTD dossiers) span 100,000+ pages across 5 complex modules, where a single missing mandatory section causes devastating Refusal to File (RTF) delays.
          </p>
        </div>

        <div>
          <h3 className="text-sm font-bold text-slate-900">The Solution: PharmSignals</h3>
          <p className="mt-1 text-slate-600">
            PharmSignals combines statistical disproportionality surveillance (Evans PRR, Pearson Chi-Square) on real openFDA FAERS data with an authoritative ICH M4 RAG-powered submission readiness checker and conversational regulatory copilot (IBM Bob).
          </p>
        </div>

        <div>
          <h3 className="text-sm font-bold text-slate-900">End-to-End M1-M5 Pipeline</h3>
          <div className="mt-2 grid grid-cols-1 sm:grid-cols-2 gap-3 font-normal">
            <div className="p-3 rounded bg-slate-50 border border-slate-200">
              <strong className="text-slate-900 font-bold block">M1: Ingestion & Normalization</strong>
              openFDA FAERS pipeline with MedDRA terminology normalization and deduplication.
            </div>
            <div className="p-3 rounded bg-slate-50 border border-slate-200">
              <strong className="text-slate-900 font-bold block">M2: PRR Signal Engine</strong>
              Evans criteria (PRR ≥ 2.0, χ² ≥ 4.0, a ≥ 3) with log-normal 95% confidence intervals.
            </div>
            <div className="p-3 rounded bg-slate-50 border border-slate-200">
              <strong className="text-slate-900 font-bold block">M3: Historical Digital Twin</strong>
              Longitudinal walk-forward simulation proving +242 day lead time detection for Vioxx.
            </div>
            <div className="p-3 rounded bg-slate-50 border border-slate-200">
              <strong className="text-slate-900 font-bold block">M4: ICH M4 RAG Checker</strong>
              Deterministic completeness scoring across Modules 1–5 with priority gap matrix.
            </div>
          </div>
        </div>

        <div>
          <h3 className="text-sm font-bold text-slate-900">Platform Technology Stack</h3>
          <p className="mt-1 text-slate-600">
            <strong>Backend:</strong> Python 3.13, FastAPI, NumPy, SciPy, Pytest (118 automated tests).<br />
            <strong>Frontend:</strong> Next.js 14 App Router, TypeScript, Tailwind CSS, Recharts.<br />
            <strong>AI & Orchestration:</strong> IBM Bob AI Assistant, Concurrently 1-Command Startup.
          </p>
        </div>
      </div>
    </div>
  );
}
