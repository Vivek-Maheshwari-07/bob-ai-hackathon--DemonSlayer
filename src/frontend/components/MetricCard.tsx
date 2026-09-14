import React from "react";

interface MetricCardProps {
  label: string;
  value: string | number;
  subtext?: string;
  badge?: string;
  trend?: string;
  color?: string;
  icon?: React.ReactNode;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  subtext,
  badge,
  trend,
  color = "#1d4ed8",
  icon,
}) => {
  return (
    <div className="relative overflow-hidden rounded-xl border border-slate-200 bg-white p-5 shadow-xs hover:border-slate-300 transition duration-150">
      <div className="flex items-start justify-between">
        <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">{label}</div>
        {icon && <div className="text-slate-400">{icon}</div>}
      </div>

      <div className="mt-3 flex items-baseline gap-2">
        <div
          className="text-2xl lg:text-3xl font-bold font-mono tracking-tight"
          style={{ color }}
        >
          {value}
        </div>
        {badge && (
          <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
            {badge}
          </span>
        )}
      </div>

      {subtext && <div className="mt-2 text-xs text-slate-500 font-medium">{subtext}</div>}
      {trend && <div className="mt-1 text-xs text-emerald-600 font-semibold">{trend}</div>}
    </div>
  );
};
