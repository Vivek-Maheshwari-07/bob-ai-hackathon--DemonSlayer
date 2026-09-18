/**
 * API client for Drug Safety Signal Detector & CTD Readiness Checker backend.
 * Connects to FastAPI backend at NEXT_PUBLIC_API_BASE_URL.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";

// ─── Module M1/M2/M3: Signal Detection & Digital Twin ───────────────────────

export async function fetchSignalSummary() {
  const res = await fetch(`${API_BASE}/signals/summary`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to fetch signal summary" }));
    throw new Error(err.detail || "Failed to fetch signal summary");
  }
  return res.json();
}

export async function fetchAllSignals(signalsOnly = false, drug?: string, statusFilter?: string) {
  const params = new URLSearchParams();
  if (signalsOnly) params.append("signals_only", "true");
  if (drug) params.append("drug", drug);
  if (statusFilter && statusFilter !== "ALL") params.append("status_filter", statusFilter);

  const url = `${API_BASE}/signals/?${params.toString()}`;
  const res = await fetch(url);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to fetch signals" }));
    throw new Error(err.detail || "Failed to fetch signals");
  }
  return res.json();
}

export async function fetchDrugBacktest(drugName: string) {
  const res = await fetch(`${API_BASE}/signals/backtest/${encodeURIComponent(drugName)}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `Failed to fetch backtest for ${drugName}` }));
    throw new Error(err.detail || `Failed to fetch backtest for ${drugName}`);
  }
  return res.json();
}

export interface CustomPRRPayload {
  drug_name?: string;
  event_term?: string;
  a?: number;
  b?: number;
  c?: number;
  d?: number;
  a_drug_event?: number;
  b_drug_other_events?: number;
  c_other_drugs_event?: number;
  d_other_drugs_other_events?: number;
  n_drug_event?: number;
  n_drug_total?: number;
  n_event_total?: number;
  n_total?: number;
  prr_threshold?: number;
  chi_square_threshold?: number;
  min_cases?: number;
}

export async function calculateCustomPRR(payload: CustomPRRPayload) {
  const res = await fetch(`${API_BASE}/signals/calculate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Calculation failed" }));
    throw new Error(err.detail || "Failed to calculate custom PRR");
  }
  return res.json();
}

export interface LiveLookupResult {
  drug_name: string;
  event_term: string | null;
  source: string;
  queried_at: string;
  success: boolean;
  error?: string | null;
  n_drug_total?: number;
  n_event_total?: number;
  n_drug_event?: number;
  n_total?: number;
  contingency_table?: Record<string, number>;
  metrics?: {
    prr: number;
    log_prr: number;
    chi_square: number;
    p_value: number;
    lower_ci: number;
    upper_ci: number;
  };
  signal_status?: string;
  is_signal?: boolean;
  explanation?: string;
}

export async function liveOpenFDALookup(drugName: string, eventTerm?: string): Promise<LiveLookupResult> {
  const res = await fetch(`${API_BASE}/signals/live-lookup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ drug_name: drugName, event_term: eventTerm || undefined }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Live lookup failed" }));
    throw new Error(err.detail || "Failed to run live openFDA lookup");
  }
  return res.json();
}

export async function fetchAdverseEventClusters(nClusters = 4, drug?: string, forceRefresh = false) {
  const params = new URLSearchParams();
  params.append("n_clusters", String(nClusters));
  if (drug && drug !== "ALL") params.append("drug", drug);
  if (forceRefresh) params.append("force_refresh", "true");

  const url = `${API_BASE}/signals/clusters?${params.toString()}`;
  const res = await fetch(url);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Clustering failed" }));
    throw new Error(err.detail || "Failed to fetch adverse event clusters");
  }
  return res.json();
}


// ─── Module M4: CTD Readiness Checker ──────────────────────────────────────

export interface M4Preset {
  id: string;
  title: string;
  description: string;
  outline: {
    submission_title: string;
    drug_name: string;
    target_region: string;
    sections: any[];
  };
}

export async function fetchM4Presets(): Promise<{ presets: M4Preset[] }> {
  const res = await fetch(`${API_BASE}/m4/presets`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to fetch CTD presets" }));
    throw new Error(err.detail || "Failed to fetch CTD presets");
  }
  // Backend returns a raw dict keyed by preset id (e.g. { "VIOXX_NDA_21042": {...} }),
  // not a { presets: [...] } envelope — normalize it here so every call site can
  // work with a plain array of { id, title, description, outline }.
  const raw: Record<string, any> = await res.json();
  const presets: M4Preset[] = Object.entries(raw).map(([id, preset]) => ({
    id,
    title: preset.submission_title || id,
    description: `${preset.drug_name || "Unknown drug"} — ${preset.target_region || "Global / ICH"}`,
    outline: preset,
  }));
  return { presets };
}

export async function checkCTDDossier(payload: object, enableReasoning = true) {
  const res = await fetch(`${API_BASE}/m4/check?enable_reasoning=${enableReasoning}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(err.detail || "Failed to check CTD dossier");
  }
  return res.json();
}

export async function checkCTDText(text: string, submissionTitle?: string) {
  const params = new URLSearchParams();
  if (submissionTitle) params.append("submission_title", submissionTitle);
  const url = `${API_BASE}/m4/quick-check-text${params.toString() ? `?${params.toString()}` : ""}`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "text/plain" },
    body: text,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(err.detail || "Failed to check text dossier");
  }
  return res.json();
}

export async function exportGapReportPDF(report: object): Promise<Blob> {
  const res = await fetch(`${API_BASE}/m4/export-pdf`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(report),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "PDF export failed" }));
    throw new Error(err.detail || "Failed to export gap report PDF");
  }
  return res.blob();
}

const MAX_PDF_UPLOAD_BYTES = 25 * 1024 * 1024; // 25 MB

export async function checkCTDPDF(file: File, submissionTitle?: string, enableReasoning = true) {
  const looksLikePdf = file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
  if (!looksLikePdf) {
    throw new Error(`"${file.name}" doesn't look like a PDF file. Please upload a .pdf dossier.`);
  }
  if (file.size > MAX_PDF_UPLOAD_BYTES) {
    throw new Error(
      `"${file.name}" is ${(file.size / (1024 * 1024)).toFixed(1)} MB, which exceeds the ${MAX_PDF_UPLOAD_BYTES / (1024 * 1024)} MB upload limit.`
    );
  }

  const formData = new FormData();
  formData.append("file", file);
  if (submissionTitle) formData.append("submission_title", submissionTitle);
  formData.append("enable_reasoning", String(enableReasoning));

  const res = await fetch(`${API_BASE}/m4/check-pdf`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(err.detail || "Failed to check PDF dossier");
  }
  return res.json();
}

// ─── IBM Bob AI Copilot ───────────────────────────────────────────────────

export async function askBobCopilot(query: string, contextType = "general") {
  const res = await fetch(`${API_BASE}/copilot/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, context_type: contextType }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Copilot error" }));
    throw new Error(err.detail || "Failed to query IBM Bob Copilot");
  }
  return res.json();
}

export async function fetchCopilotSuggestions(): Promise<string[]> {
  try {
    const res = await fetch(`${API_BASE}/copilot/suggestions`);
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

// ─── Health & Connectivity ────────────────────────────────────────────────

export async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`);
    return res.ok;
  } catch {
    return false;
  }
}
