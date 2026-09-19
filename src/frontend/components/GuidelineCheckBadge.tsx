import React, { useState } from "react";

interface RequirementPresent {
  requirement: string;
  evidence: string;
}

interface GuidelineCheckEvidence {
  requirements_present?: RequirementPresent[];
  requirements_absent?: string[];
  citation?: string;
  reasoning?: string;
}

interface GuidelineCheckBadgeProps {
  verdict: string | null;
  evidence: GuidelineCheckEvidence | null;
}

const VERDICT_STYLES: Record<string, string> = {
  SUBSTANTIVE: "bg-emerald-50 text-emerald-700 border-emerald-200",
  GENERIC: "bg-amber-50 text-amber-700 border-amber-200",
  INSUFFICIENT: "bg-rose-50 text-rose-700 border-rose-200",
  EMPTY: "bg-rose-100 text-rose-800 border-rose-300",
};

/**
 * Guideline-grounded content check badge, shown next to a section's Tier 1
 * status. This is the consolidated content-verification tier: it compares
 * the section's real text against the actual ICH guideline requirement
 * excerpt for that section via Claude Haiku. Renders "N/A" when the check
 * didn't run for this section (no guideline excerpt sourced yet, the
 * section didn't pass the substance gate, or ANTHROPIC_API_KEY is
 * unavailable) — never the same as a bad verdict.
 */
export const GuidelineCheckBadge: React.FC<GuidelineCheckBadgeProps> = ({ verdict, evidence }) => {
  const [expanded, setExpanded] = useState(false);

  if (!verdict) {
    return <span className="text-[10px] text-slate-400 font-medium">N/A</span>;
  }

  const colorCls = VERDICT_STYLES[verdict] || "bg-slate-100 text-slate-600 border-slate-200";
  const present = evidence?.requirements_present || [];
  const absent = evidence?.requirements_absent || [];

  return (
    <div className="relative inline-block">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        title="Guideline-grounded check against the real ICH requirement text for this section"
        className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider cursor-pointer ${colorCls}`}
      >
        {verdict}
      </button>
      {expanded && (
        <div className="absolute z-20 mt-1 w-80 rounded-md border border-slate-200 bg-white p-2.5 shadow-lg text-left">
          <div className="text-[10px] font-bold uppercase tracking-wide text-slate-500 mb-1.5">
            Guideline Comparison
          </div>
          {evidence?.citation && (
            <div className="text-[11px] text-slate-600 mb-1.5">
              <span className="font-semibold">Compared against:</span> {evidence.citation}
            </div>
          )}
          {evidence?.reasoning && (
            <p className="text-[11px] text-slate-700 mb-1.5">{evidence.reasoning}</p>
          )}
          {present.length > 0 && (
            <div className="text-[11px] mb-1.5">
              <span className="font-semibold text-emerald-700">Present:</span>
              <ul className="list-disc list-inside text-slate-700 mt-0.5 space-y-0.5">
                {present.map((p, i) => (
                  <li key={i}>
                    {p.requirement}
                    {p.evidence && (
                      <div className="pl-3 border-l-2 border-slate-200 text-slate-500 italic">
                        "{p.evidence}"
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {absent.length > 0 && (
            <div className="text-[11px]">
              <span className="font-semibold text-rose-700">Absent:</span>
              <ul className="list-disc list-inside text-slate-700 mt-0.5">
                {absent.map((a, i) => (
                  <li key={i}>{a}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
