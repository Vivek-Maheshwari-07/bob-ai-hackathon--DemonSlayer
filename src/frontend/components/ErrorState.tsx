import React from "react";

interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = "Analysis Encountered An Issue",
  message,
  onRetry,
}) => {
  return (
    <div className="flex flex-col items-center justify-center p-8 rounded-xl border border-rose-200 bg-rose-50/60 text-center shadow-xs">
      <div className="w-10 h-10 rounded-full bg-rose-100 flex items-center justify-center text-rose-600 text-lg font-bold border border-rose-200">
        ⚠
      </div>
      <div className="mt-3 text-sm font-bold text-rose-900">{title}</div>
      <div className="mt-1 text-xs text-rose-700 max-w-md font-medium">{message}</div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-4 px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold transition shadow-xs"
        >
          ↻ Retry Request
        </button>
      )}
    </div>
  );
};
