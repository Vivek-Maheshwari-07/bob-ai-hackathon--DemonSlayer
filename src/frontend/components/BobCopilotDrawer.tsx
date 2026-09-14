import React, { useState, useEffect } from "react";
import { askBobCopilot, fetchCopilotSuggestions } from "../lib/api";

interface BobCopilotDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  backendOnline: boolean | null;
}

interface CopilotMessage {
  sender: "user" | "bob";
  text: string;
  sourceContext?: string[];
  suggestedFollowups?: string[];
  modelUsed?: string;
}

export const BobCopilotDrawer: React.FC<BobCopilotDrawerProps> = ({
  isOpen,
  onClose,
  backendOnline,
}) => {
  const [messages, setMessages] = useState<CopilotMessage[]>([
    {
      sender: "bob",
      text: "Hello! I am **IBM Bob**, your pharmacovigilance and CTD regulatory readiness copilot. How can I assist you with safety signal analysis or submission audits today?",
    },
  ]);
  const [inputQuery, setInputQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);

  useEffect(() => {
    fetchCopilotSuggestions().then((res) => {
      if (res && res.length > 0) setSuggestions(res);
    });
  }, []);

  const handleSend = async (textToSend?: string) => {
    const q = (textToSend || inputQuery).trim();
    if (!q) return;

    setInputQuery("");
    setMessages((prev) => [...prev, { sender: "user", text: q }]);
    setLoading(true);

    try {
      const res = await askBobCopilot(q);
      setMessages((prev) => [
        ...prev,
        {
          sender: "bob",
          text: res.answer,
          sourceContext: res.source_context,
          suggestedFollowups: res.suggested_followups,
          modelUsed: res.model_used,
        },
      ]);
    } catch (e: unknown) {
      setMessages((prev) => [
        ...prev,
        {
          sender: "bob",
          text: `⚠ Error communicating with Bob Copilot: ${
            e instanceof Error ? e.message : "Unknown error"
          }`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-y-0 right-0 w-full sm:w-[480px] z-50 bg-white border-l border-slate-200 shadow-2xl flex flex-col animate-in slide-in-from-right duration-200">
      {/* Drawer Header */}
      <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white font-bold text-xs shadow-xs">
            BOB
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-900">IBM Bob AI Copilot</h2>
            <p className="text-[10px] text-slate-500 font-medium">Safety Signal & ICH M4 Specialist</p>
          </div>
        </div>

        <button
          onClick={onClose}
          className="w-7 h-7 rounded-lg bg-slate-200 hover:bg-slate-300 text-slate-700 text-xs flex items-center justify-center transition"
          aria-label="Close copilot"
        >
          ✕
        </button>
      </div>

      {/* Suggested Quick Chips */}
      {suggestions.length > 0 && (
        <div className="p-2.5 border-b border-slate-200 bg-slate-50/50 overflow-x-auto flex gap-1.5">
          {suggestions.slice(0, 3).map((s, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(s)}
              className="shrink-0 px-2.5 py-1 rounded-md text-[10px] bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100 font-medium transition text-left truncate max-w-[220px]"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Message History */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3.5 bg-slate-50/30">
        {messages.map((m, idx) => (
          <div
            key={idx}
            className={`flex flex-col ${
              m.sender === "user" ? "items-end" : "items-start"
            }`}
          >
            <div
              className={`max-w-[90%] p-3.5 rounded-xl text-xs leading-relaxed ${
                m.sender === "user"
                  ? "bg-blue-600 text-white rounded-tr-none shadow-xs"
                  : "bg-white text-slate-800 rounded-tl-none border border-slate-200 shadow-xs"
              }`}
            >
              <div className="whitespace-pre-wrap">{m.text}</div>

              {m.modelUsed && (
                <div className="text-[9px] text-slate-400 mt-2 font-mono">
                  Engine: {m.modelUsed}
                </div>
              )}
            </div>

            {/* Suggested Followups */}
            {m.suggestedFollowups && m.suggestedFollowups.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1 max-w-[90%]">
                {m.suggestedFollowups.map((f, fIdx) => (
                  <button
                    key={fIdx}
                    onClick={() => handleSend(f)}
                    className="px-2 py-0.5 rounded text-[10px] bg-white hover:bg-slate-100 text-blue-700 border border-slate-200 shadow-xs transition text-left font-medium"
                  >
                    → {f}
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="flex items-center gap-2 text-xs text-blue-700 p-3 bg-blue-50 rounded-xl border border-blue-200 animate-pulse font-medium">
            <span>⚙</span> Bob is analyzing safety & regulatory context…
          </div>
        )}
      </div>

      {/* Query Input */}
      <div className="p-3 border-t border-slate-200 bg-white">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex gap-2"
        >
          <input
            type="text"
            placeholder={
              backendOnline
                ? "Ask Bob about safety signals or CTD readiness..."
                : "Backend offline..."
            }
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            disabled={loading || !backendOnline}
            className="flex-1 px-3.5 py-2 rounded-lg bg-slate-50 border border-slate-300 text-slate-900 text-xs placeholder-slate-400 focus:border-blue-500 focus:bg-white outline-none transition"
          />
          <button
            type="submit"
            disabled={loading || !inputQuery.trim() || !backendOnline}
            className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs transition disabled:opacity-50 shadow-xs"
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
};
