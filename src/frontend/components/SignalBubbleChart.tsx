import React from "react";
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { StatusBadge } from "./StatusBadge";

export interface BubbleChartPoint {
  id: number;
  drug: string;
  event: string;
  prr: number;
  cases: number;
  chi2: number;
  status: string;
}

interface SignalBubbleChartProps {
  data: BubbleChartPoint[];
}

/**
 * PRR-vs-case-count disproportionality scatter chart, shared between the
 * Dashboard and Signal Detection Workspace views (previously duplicated
 * verbatim in both places).
 */
export const SignalBubbleChart: React.FC<SignalBubbleChartProps> = ({ data }) => {
  return (
    <div className="h-80 w-full pt-2">
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 15, right: 30, bottom: 20, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis
            type="number"
            dataKey="prr"
            name="PRR"
            unit="x"
            stroke="#64748b"
            tick={{ fontSize: 11, fill: "#64748b" }}
            label={{
              value: "Proportional Reporting Ratio (PRR) →",
              position: "insideBottom",
              offset: -12,
              fontSize: 11,
              fill: "#475569",
            }}
          />
          <YAxis
            type="number"
            dataKey="cases"
            name="Cases"
            stroke="#64748b"
            tick={{ fontSize: 11, fill: "#64748b" }}
            label={{
              value: "Case Count (a)",
              angle: -90,
              position: "insideLeft",
              fontSize: 11,
              fill: "#475569",
            }}
          />
          <ZAxis range={[60, 280]} />
          <Tooltip
            cursor={{ strokeDasharray: "3 3" }}
            content={({ active, payload }) => {
              if (active && payload && payload.length) {
                const point = payload[0].payload;
                return (
                  <div className="p-3 bg-white border border-slate-300 rounded shadow-md text-xs space-y-1">
                    <div className="font-bold text-slate-900 border-b border-slate-100 pb-1">
                      {point.drug} — {point.event}
                    </div>
                    <div className="text-rose-600 font-mono font-bold">
                      PRR: {point.prr}x
                    </div>
                    <div className="text-slate-600 font-mono">
                      Case Count ($a$): {point.cases} reports
                    </div>
                    <div className="text-blue-700 font-mono">
                      Chi-Square ($\chi^2$): {point.chi2}
                    </div>
                    <div className="pt-1">
                      <StatusBadge label={point.status} size="sm" />
                    </div>
                  </div>
                );
              }
              return null;
            }}
          />
          <ReferenceLine
            x={2.0}
            stroke="#ef4444"
            strokeDasharray="4 4"
            label={{
              value: "Critical Threshold (PRR = 2.0)",
              fill: "#dc2626",
              fontSize: 11,
              position: "top",
            }}
          />
          <Scatter name="Safety Signals" data={data}>
            {data.map((entry, index) => {
              const fillColor =
                entry.status === "SIGNAL"
                  ? "#dc2626"
                  : entry.status === "WEAK_SIGNAL"
                  ? "#f59e0b"
                  : "#94a3b8";
              return <Cell key={`cell-${index}`} fill={fillColor} fillOpacity={0.8} />;
            })}
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
};
