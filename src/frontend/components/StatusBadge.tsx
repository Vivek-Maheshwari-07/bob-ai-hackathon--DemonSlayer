import React from "react";

interface StatusBadgeProps {
  label: string;
  className?: string;
  size?: "sm" | "md";
}

const BADGE_STYLES: Record<string, string> = {
  SIGNAL: "bg-rose-50 text-rose-700 border-rose-200 font-bold",
  WEAK_SIGNAL: "bg-amber-50 text-amber-700 border-amber-200 font-semibold",
  NOISE: "bg-slate-100 text-slate-600 border-slate-200",
  PRESENT: "bg-emerald-50 text-emerald-700 border-emerald-200 font-semibold",
  PARTIAL: "bg-amber-50 text-amber-700 border-amber-200 font-semibold",
  MISSING: "bg-rose-50 text-rose-700 border-rose-200 font-bold",
  CRITICAL: "bg-rose-100 text-rose-800 border-rose-300 font-bold",
  MAJOR: "bg-orange-50 text-orange-700 border-orange-200 font-semibold",
  STANDARD: "bg-blue-50 text-blue-700 border-blue-200 font-medium",
  EARLY_DETECTION: "bg-emerald-50 text-emerald-700 border-emerald-200 font-bold",
  DATA_UNAVAILABLE_PRE_WITHDRAWAL: "bg-purple-50 text-purple-700 border-purple-200",
  COMPLETE: "bg-emerald-50 text-emerald-700 border-emerald-200 font-semibold",
  READY: "bg-blue-50 text-blue-700 border-blue-200 font-semibold",
  NOT_RUN: "bg-slate-100 text-slate-500 border-slate-200",
};

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  label,
  className = "",
  size = "md",
}) => {
  const norm = (label || "").toUpperCase().trim();
  const style = BADGE_STYLES[norm] || "bg-slate-100 text-slate-700 border-slate-200";
  const sizeCls = size === "sm" ? "px-2 py-0.5 text-[10px]" : "px-2.5 py-0.5 text-xs";

  return (
    <span
      className={`inline-flex items-center rounded-full border font-medium uppercase tracking-wider ${sizeCls} ${style} ${className}`}
    >
      {label.replace(/_/g, " ")}
    </span>
  );
};
