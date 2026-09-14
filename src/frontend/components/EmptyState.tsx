import React from "react";

interface EmptyStateProps {
  icon?: string;
  title: string;
  description: string;
  actionText?: string;
  onAction?: () => void;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon = "📊",
  title,
  description,
  actionText,
  onAction,
}) => {
  return (
    <div className="flex flex-col items-center justify-center p-12 rounded-xl border border-dashed border-slate-300 bg-slate-50/50 text-center">
      <div className="text-3xl mb-3">{icon}</div>
      <div className="text-sm font-bold text-slate-800">{title}</div>
      <div className="mt-1 text-xs text-slate-500 max-w-sm font-medium">{description}</div>
      {actionText && onAction && (
        <button
          onClick={onAction}
          className="mt-4 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold transition shadow-xs"
        >
          {actionText}
        </button>
      )}
    </div>
  );
};
