"use client";

import { TaskAction, ActionStatus, ActionType } from "@/types";

interface ActionHistoryListProps {
  actions: TaskAction[];
  onActionClick: (action: TaskAction) => void;
  getActionTypeLabel: (type: ActionType) => string;
}

export default function ActionHistoryList({
  actions,
  onActionClick,
  getActionTypeLabel,
}: ActionHistoryListProps) {
  const getStatusColor = (status: ActionStatus) => {
    switch (status) {
      case ActionStatus.APPROVED:
        return "bg-blue-100 text-blue-800";
      case ActionStatus.EXECUTING:
        return "bg-purple-100 text-purple-800";
      case ActionStatus.COMPLETED:
        return "bg-green-100 text-green-800";
      case ActionStatus.FAILED:
        return "bg-red-100 text-red-800";
      case ActionStatus.CANCELLED:
        return "bg-gray-100 text-gray-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  const getStatusIcon = (status: ActionStatus) => {
    switch (status) {
      case ActionStatus.APPROVED:
        return "✓";
      case ActionStatus.EXECUTING:
        return "⟳";
      case ActionStatus.COMPLETED:
        return "✓";
      case ActionStatus.FAILED:
        return "✕";
      case ActionStatus.CANCELLED:
        return "⊘";
      default:
        return "•";
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-xl font-semibold mb-4">
        Action History ({actions.length})
      </h3>
      <div className="space-y-3">
        {actions.map((action) => (
          <div
            key={action.action_id}
            onClick={() => onActionClick(action)}
            className="p-4 border border-gray-200 rounded cursor-pointer hover:bg-gray-50 transition-colors"
          >
            <div className="flex justify-between items-start">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <span className="font-semibold">
                    {getActionTypeLabel(action.action_type)}
                  </span>
                  <span
                    className={`px-2 py-1 rounded-full text-xs font-semibold ${getStatusColor(
                      action.status
                    )}`}
                  >
                    {getStatusIcon(action.status)} {action.status}
                  </span>
                </div>
                <div className="text-sm text-gray-600">{action.reasoning}</div>
                <div className="text-xs text-gray-500 mt-2">
                  Created: {new Date(action.created_at).toLocaleString()}
                  {action.completed_at && (
                    <>
                      {" • "}
                      Completed:{" "}
                      {new Date(action.completed_at).toLocaleString()}
                    </>
                  )}
                </div>
              </div>
            </div>

            {/* Result Preview */}
            {action.result && (
              <div className="mt-3 p-2 bg-gray-50 rounded text-xs">
                <div className="font-semibold text-gray-500 mb-1">Result:</div>
                <pre className="text-gray-700 whitespace-pre-wrap overflow-x-auto">
                  {JSON.stringify(action.result, null, 2)}
                </pre>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
