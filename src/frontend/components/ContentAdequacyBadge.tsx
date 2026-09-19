import React, { useState } from "react";

interface CheckpointResult {
  id: string;
  question: string;
  answer: string;
  quote: string | null;
}

interface ContentAdequacyBadgeProps {
  score: number | null;
  checkpoints: CheckpointResult[] | null;
}

/**
 * Tier 2 content-adequacy badge shown next to a section's Tier 1 status.
 * Renders "N/A" when Tier 2 didn't run for this section (no checkpoints
 * defined, or Gemini unavailable) — that is never the same as a low score.
 */
export const ContentAdequacyBadge: React.FC<ContentAdequacyBadgeProps> = ({
  score,
  checkpoints,
}) => {
  const [expanded, setExpanded] = useState(false);

  if (score === null || score === undefined) {
    return <span className="text-[10px] text-slate-400 font-medium">N/A</span>;
  }

  const pct = Math.round(score * 100);
  const colorCls =
    pct >= 80
      ? "bg-emerald-50 text-emerald-700 border-emerald-200"
      : pct >= 40
      ? "bg-amber-50 text-amber-700 border-amber-200"
      : "bg-rose-50 text-rose-700 border-rose-200";

  const failedCheckpoints = (checkpoints || []).filter((c) => c.answer !== "YES");

  return (
    <div className="relative inline-block">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        title="Tier 2: grounded content-adequacy check against ICH checkpoint questions"
        className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider cursor-pointer ${colorCls}`}
      >
        {pct}%
        {failedCheckpoints.length > 0 && (
          <span className="text-[9px] font-semibold">({failedCheckpoints.length} gaps)</span>
        )}
      </button>
      {expanded && checkpoints && checkpoints.length > 0 && (
        <div className="absolute z-20 mt-1 w-72 rounded-md border border-slate-200 bg-white p-2.5 shadow-lg text-left">
          <div className="text-[10px] font-bold uppercase tracking-wide text-slate-500 mb-1.5">
            Checkpoint Verification
          </div>
          <ul className="space-y-1.5 max-h-56 overflow-y-auto">
            {checkpoints.map((c) => (
              <li key={c.id} className="text-[11px] leading-snug">
                <span
                  className={`font-bold mr-1 ${
                    c.answer === "YES"
                      ? "text-emerald-600"
                      : c.answer === "NO"
                      ? "text-rose-600"
                      : "text-amber-600"
                  }`}
                >
                  [{c.answer}]
                </span>
                <span className="text-slate-700">{c.question}</span>
                {c.quote && (
                  <div className="mt-0.5 pl-3 border-l-2 border-slate-200 text-slate-500 italic">
                    "{c.quote}"
                  </div>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
