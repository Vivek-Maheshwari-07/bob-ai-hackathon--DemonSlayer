import React, { useState } from "react";

interface AuthenticityEvidence {
  missing_data_points?: string[];
  candidate_citation?: string | null;
  exemplar_citations?: string[];
  source_citations?: string[];
  reasoning?: string;
}

interface AuthenticityBadgeProps {
  verdict: string | null;
  evidence: AuthenticityEvidence | null;
}

const VERDICT_STYLES: Record<string, string> = {
  SUBSTANTIVE: "bg-emerald-50 text-emerald-700 border-emerald-200",
  GENERIC: "bg-amber-50 text-amber-700 border-amber-200",
  INSUFFICIENT: "bg-rose-50 text-rose-700 border-rose-200",
};

/**
 * Tier 3 content-authenticity badge shown next to Tier 2's Content Adequacy
 * badge. Renders "N/A" when Tier 3 didn't run for this section (no real
 * exemplars sourced yet for this section_id, the section didn't pass the
 * substance gate, or Gemini was unavailable) — never the same as a bad
 * verdict.
 */
export const AuthenticityBadge: React.FC<AuthenticityBadgeProps> = ({ verdict, evidence }) => {
  const [expanded, setExpanded] = useState(false);

  if (!verdict) {
    return <span className="text-[10px] text-slate-400 font-medium">N/A</span>;
  }

  const colorCls = VERDICT_STYLES[verdict] || "bg-slate-100 text-slate-600 border-slate-200";
  const missingPoints = evidence?.missing_data_points || [];
  const citations = evidence?.source_citations || evidence?.exemplar_citations || [];

  return (
    <div className="relative inline-block">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        title="Tier 3: grounded authenticity check against real regulatory-document exemplars"
        className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider cursor-pointer ${colorCls}`}
      >
        {verdict}
      </button>
      {expanded && (
        <div className="absolute z-20 mt-1 w-80 rounded-md border border-slate-200 bg-white p-2.5 shadow-lg text-left">
          <div className="text-[10px] font-bold uppercase tracking-wide text-slate-500 mb-1.5">
            Authenticity Comparison
          </div>
          {citations.length > 0 && (
            <div className="text-[11px] text-slate-600 mb-1.5">
              <span className="font-semibold">Compared against:</span>{" "}
              {citations.join("; ")}
            </div>
          )}
          {evidence?.reasoning && (
            <p className="text-[11px] text-slate-700 mb-1.5">{evidence.reasoning}</p>
          )}
          {missingPoints.length > 0 && (
            <div className="text-[11px]">
              <span className="font-semibold text-rose-700">Missing data points:</span>
              <ul className="list-disc list-inside text-slate-700 mt-0.5">
                {missingPoints.map((point, i) => (
                  <li key={i}>{point}</li>
                ))}
              </ul>
            </div>
          )}
          {evidence?.candidate_citation && (
            <div className="mt-1.5 pl-3 border-l-2 border-slate-200 text-slate-500 italic text-[11px]">
              Candidate: "{evidence.candidate_citation}"
            </div>
          )}
        </div>
      )}
    </div>
  );
};
