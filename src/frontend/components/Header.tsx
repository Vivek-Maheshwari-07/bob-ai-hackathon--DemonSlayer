import React from "react";
import { NavPage } from "./Sidebar";

interface HeaderProps {
  currentPage: NavPage;
  onOpenMobileMenu: () => void;
  backendOnline: boolean | null;
  onToggleCopilot: () => void;
  copilotOpen: boolean;
}

const PAGE_NAMES: Record<NavPage, string> = {
  dashboard: "Signal Detection & PV Analytics",
  signals: "Adverse Event Signal Detection Workspace",
  historical: "Historical Longitudinal Backtest (M3)",
  readiness: "Dossier Submission Readiness Checker (M4)",
  reports: "Reports & Regulatory Dossier Exports",
  about: "System Architecture & M1-M5 Pipeline",
};

export const Header: React.FC<HeaderProps> = ({
  currentPage,
  onOpenMobileMenu,
  backendOnline,
  onToggleCopilot,
  copilotOpen,
}) => {
  return (
    <header className="sticky top-0 z-30 h-16 border-b border-slate-200 bg-white px-4 lg:px-6 flex items-center justify-between shadow-xs">
      {/* Left Title, Breadcrumbs & Search */}
      <div className="flex items-center gap-4 flex-1 max-w-xl">
        <button
          onClick={onOpenMobileMenu}
          className="lg:hidden p-1.5 rounded text-slate-500 hover:text-slate-900 hover:bg-slate-100"
          aria-label="Open sidebar menu"
        >
          ☰
        </button>

        <div className="hidden sm:flex items-center gap-2 text-xs">
          <span className="text-slate-500 font-semibold">PharmSignals</span>
          <span className="text-slate-300">/</span>
          <span className="font-bold text-slate-900 truncate">
            {PAGE_NAMES[currentPage]}
          </span>
        </div>

        {/* Search Field */}
        <div className="relative flex-1 max-w-xs hidden md:block">
          <input
            type="text"
            placeholder="Search drug, reaction or CTD section..."
            className="w-full pl-7 pr-3 py-1.5 rounded bg-slate-50 border border-slate-200 text-xs text-slate-900 placeholder-slate-400 focus:bg-white focus:border-blue-500 outline-none transition"
          />
          <span className="absolute left-2.5 top-2 text-xs text-slate-400">🔍</span>
        </div>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-3">
        {/* Real-Time System Status Indicator */}
        <div className="flex items-center gap-2 px-2.5 py-1.5 rounded border border-slate-200 bg-slate-50 text-xs shadow-xs">
          <span
            className={`w-2 h-2 rounded-full ${
              backendOnline === null
                ? "bg-slate-400 animate-pulse"
                : backendOnline
                ? "bg-emerald-500"
                : "bg-rose-500"
            }`}
          />
          <span className="text-slate-700 font-semibold text-[11px]">
            {backendOnline === null
              ? "Checking API..."
              : backendOnline
              ? "Real-Time Data Connected"
              : "Backend Offline"}
          </span>
        </div>

        {/* User Role Badge */}
        <div className="hidden lg:flex items-center gap-2 pl-2 border-l border-slate-200">
          <div className="w-7 h-7 rounded-full bg-slate-100 border border-slate-300 flex items-center justify-center text-xs font-bold text-slate-700">
            PV
          </div>
          <div className="text-left text-[11px] leading-tight">
            <div className="font-bold text-slate-900">Safety Lead</div>
            <div className="text-slate-500 font-medium">Pharmacovigilance</div>
          </div>
        </div>

        {/* IBM Bob AI Copilot Trigger */}
        <button
          id="btn-header-copilot"
          onClick={onToggleCopilot}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-semibold transition border shadow-xs ${
            copilotOpen
              ? "bg-blue-700 text-white border-blue-700"
              : "bg-blue-50 text-blue-700 border-blue-200 hover:bg-blue-100"
          }`}
        >
          <span>🤖</span>
          <span className="hidden sm:inline">IBM Bob Copilot</span>
        </button>
      </div>
    </header>
  );
};
