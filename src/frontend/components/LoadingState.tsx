import React from "react";

interface LoadingStateProps {
  message?: string;
  description?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  message = "Processing analysis...",
  description = "Communicating with backend analytics engine",
}) => {
  return (
    <div className="flex flex-col items-center justify-center p-12 rounded-xl border border-slate-200 bg-white text-center shadow-xs">
      <div className="relative flex items-center justify-center">
        <div className="w-10 h-10 border-3 border-blue-100 border-t-blue-600 rounded-full animate-spin" />
        <div className="absolute w-3 h-3 bg-blue-600/20 rounded-full animate-ping" />
      </div>
      <div className="mt-4 text-sm font-bold text-slate-800">{message}</div>
      <div className="mt-1 text-xs text-slate-500 max-w-sm font-medium">{description}</div>
    </div>
  );
};
