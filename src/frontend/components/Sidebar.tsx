import React from "react";

export type NavPage =
  | "dashboard"
  | "signals"
  | "historical"
  | "readiness"
  | "reports"
  | "about";

interface SidebarProps {
  currentPage: NavPage;
  onSelectPage: (page: NavPage) => void;
  isOpen: boolean;
  onCloseMobile: () => void;
}

const NAV_ITEMS: Array<{
  id: NavPage;
  label: string;
  icon: string;
  badge?: string;
}> = [
  { id: "dashboard", label: "Dashboard", icon: "📊" },
  { id: "signals", label: "Signal Detection", icon: "🔬", badge: "M1-M2" },
  { id: "historical", label: "Historical Analysis", icon: "📈", badge: "M3" },
  { id: "readiness", label: "Submission Readiness", icon: "📋", badge: "M4" },
  { id: "reports", label: "Reports & Export", icon: "📑" },
  { id: "about", label: "System Architecture", icon: "ℹ️" },
];

export const Sidebar: React.FC<SidebarProps> = ({
  currentPage,
  onSelectPage,
  isOpen,
  onCloseMobile,
}) => {
  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-900/30 backdrop-blur-xs lg:hidden"
          onClick={onCloseMobile}
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed top-0 bottom-0 left-0 z-50 w-64 border-r border-slate-200 bg-white flex flex-col transition-transform duration-200 ease-in-out lg:translate-x-0 ${
          isOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Brand Header */}
        <div className="h-16 px-5 border-b border-slate-200 flex items-center justify-between bg-white">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded bg-blue-700 flex items-center justify-center font-bold text-white text-xs tracking-wider shadow-xs">
              PS
            </div>
            <div>
              <div className="text-sm font-bold tracking-tight text-slate-900 flex items-center gap-1">
                PharmSignals
              </div>
              <div className="text-[10px] text-slate-500 font-medium">
                Regulatory Compliance Hub
              </div>
            </div>
          </div>

          <button
            onClick={onCloseMobile}
            className="lg:hidden p-1.5 rounded text-slate-500 hover:text-slate-800 hover:bg-slate-100"
            aria-label="Close sidebar menu"
          >
            ✕
          </button>
        </div>

        {/* Workflows Subtitle */}
        <div className="px-4 pt-4 pb-1">
          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
            Workflows & Modules
          </div>
        </div>

        {/* Navigation Menu */}
        <nav className="flex-1 px-3 py-2 space-y-1 overflow-y-auto">
          {NAV_ITEMS.map((item) => {
            const isActive = currentPage === item.id;
            return (
              <button
                key={item.id}
                id={`nav-${item.id}`}
                onClick={() => {
                  onSelectPage(item.id);
                  onCloseMobile();
                }}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded text-xs font-semibold transition duration-150 ${
                  isActive
                    ? "bg-blue-50 text-blue-700 border border-blue-200 shadow-xs"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-50 border border-transparent"
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <span className="text-sm opacity-80">{item.icon}</span>
                  <span>{item.label}</span>
                </div>

                {item.badge && (
                  <span
                    className={`text-[9px] px-1.5 py-0.5 rounded font-mono font-semibold ${
                      isActive
                        ? "bg-blue-100 text-blue-800"
                        : "bg-slate-100 text-slate-600"
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Footer info */}
        <div className="p-3.5 border-t border-slate-200 bg-slate-50/70">
          <div className="rounded p-2.5 bg-white border border-slate-200 space-y-1 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-blue-700 uppercase tracking-wider">
                IBM Bobathon 2026
              </span>
              <span className="text-[9px] px-1.5 py-0.2 rounded bg-blue-50 text-blue-700 font-semibold border border-blue-100">
                P2
              </span>
            </div>
            <p className="text-[11px] font-semibold text-slate-800">Team Demon Slayer</p>
            <p className="text-[10px] text-slate-500 font-mono">FAERS (M1-M3) · ICH M4 (M4)</p>
          </div>
        </div>
      </aside>
    </>
  );
};
