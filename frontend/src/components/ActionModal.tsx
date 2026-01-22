"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import { TaskAction, ActionStatus, ActionType } from "@/types";

interface ActionModalProps {
  isOpen: boolean;
  onClose: () => void;
  action: TaskAction;
  taskId: string;
  getActionTypeLabel: (type: ActionType) => string;
}

export default function ActionModal({
  isOpen,
  onClose,
  action,
  taskId,
  getActionTypeLabel,
}: ActionModalProps) {
  const queryClient = useQueryClient();
  const [dryRun, setDryRun] = useState(true);
  const [executionResult, setExecutionResult] = useState<any>(null);

  // Approve mutation
  const approveMutation = useMutation({
    mutationFn: () => apiClient.approveAction(action.action_id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["task-actions", taskId] });
      onClose();
    },
  });

  // Execute mutation
  const executeMutation = useMutation({
    mutationFn: (isDryRun: boolean) =>
      apiClient.executeAction(action.action_id, { dry_run: isDryRun }),
    onSuccess: (result) => {
      setExecutionResult(result);
      if (!dryRun) {
        queryClient.invalidateQueries({ queryKey: ["task-actions", taskId] });
      }
    },
  });

  // Cancel mutation
  const cancelMutation = useMutation({
    mutationFn: () => apiClient.cancelAction(action.action_id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["task-actions", taskId] });
      onClose();
    },
  });

  // Rollback mutation
  const rollbackMutation = useMutation({
    mutationFn: () => apiClient.rollbackAction(action.action_id),
    onSuccess: (result) => {
      setExecutionResult(result);
      queryClient.invalidateQueries({ queryKey: ["task-actions", taskId] });
    },
  });

  if (!isOpen) return null;

  const getStatusColor = (status: ActionStatus) => {
    switch (status) {
      case ActionStatus.PROPOSED:
        return "bg-yellow-100 text-yellow-800";
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

  const canApprove = action.status === ActionStatus.PROPOSED;
  const canExecute =
    action.status === ActionStatus.APPROVED ||
    action.status === ActionStatus.FAILED;
  const canCancel =
    action.status === ActionStatus.PROPOSED ||
    action.status === ActionStatus.APPROVED;
  const canRollback = action.status === ActionStatus.COMPLETED;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-3xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-gray-200 p-6">
          <div className="flex justify-between items-start">
            <div>
              <h2 className="text-2xl font-bold">
                {getActionTypeLabel(action.action_type)}
              </h2>
              <span
                className={`inline-block mt-2 px-3 py-1 rounded-full text-sm font-semibold ${getStatusColor(
                  action.status
                )}`}
              >
                {action.status}
              </span>
            </div>
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700 text-2xl"
            >
              ×
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Reasoning */}
          <div>
            <h3 className="font-semibold text-lg mb-2">Reasoning</h3>
            <p className="text-gray-700">{action.reasoning}</p>
            <p className="text-sm text-gray-500 mt-1">
              Confidence: {(action.confidence * 100).toFixed(0)}%
            </p>
          </div>

          {/* Parameters */}
          <div>
            <h3 className="font-semibold text-lg mb-2">Parameters</h3>
            <div className="bg-gray-50 rounded p-4">
              <pre className="text-sm overflow-x-auto">
                {JSON.stringify(action.parameters, null, 2)}
              </pre>
            </div>
          </div>

          {/* Result */}
          {action.result && (
            <div>
              <h3 className="font-semibold text-lg mb-2">Result</h3>
              <div className="bg-gray-50 rounded p-4">
                <pre className="text-sm overflow-x-auto">
                  {JSON.stringify(action.result, null, 2)}
                </pre>
              </div>
            </div>
          )}

          {/* Execution Result (from this session) */}
          {executionResult && (
            <div>
              <h3 className="font-semibold text-lg mb-2">
                {dryRun ? "Dry Run Result" : "Execution Result"}
              </h3>
              <div
                className={`rounded p-4 ${
                  executionResult.success
                    ? "bg-green-50 border border-green-200"
                    : "bg-red-50 border border-red-200"
                }`}
              >
                {executionResult.success ? (
                  <>
                    <div className="text-green-700 font-semibold mb-2">
                      ✓ Success
                    </div>
                    {executionResult.data && (
                      <pre className="text-sm overflow-x-auto text-green-900">
                        {JSON.stringify(executionResult.data, null, 2)}
                      </pre>
                    )}
                  </>
                ) : (
                  <>
                    <div className="text-red-700 font-semibold mb-2">
                      ✕ Failed
                    </div>
                    <p className="text-red-900">{executionResult.error}</p>
                  </>
                )}
              </div>
            </div>
          )}

          {/* Timestamps */}
          <div className="text-sm text-gray-500 space-y-1">
            <div>Created: {new Date(action.created_at).toLocaleString()}</div>
            {action.approved_at && (
              <div>
                Approved: {new Date(action.approved_at).toLocaleString()}
              </div>
            )}
            {action.executed_at && (
              <div>
                Executed: {new Date(action.executed_at).toLocaleString()}
              </div>
            )}
            {action.completed_at && (
              <div>
                Completed: {new Date(action.completed_at).toLocaleString()}
              </div>
            )}
          </div>

          {/* Error Messages */}
          {approveMutation.isError && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
              Error approving action: {approveMutation.error.message}
            </div>
          )}
          {executeMutation.isError && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
              Error executing action: {executeMutation.error.message}
            </div>
          )}
          {cancelMutation.isError && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
              Error cancelling action: {cancelMutation.error.message}
            </div>
          )}
          {rollbackMutation.isError && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
              Error rolling back action: {rollbackMutation.error.message}
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="sticky bottom-0 bg-white border-t border-gray-200 p-6 space-y-4">
          {/* Dry Run Toggle (for execution) */}
          {canExecute && (
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="dry-run"
                checked={dryRun}
                onChange={(e) => setDryRun(e.target.checked)}
                className="w-4 h-4"
              />
              <label htmlFor="dry-run" className="text-sm text-gray-700">
                Dry run (simulate without making actual changes)
              </label>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-2">
            {canApprove && (
              <button
                onClick={() => approveMutation.mutate()}
                disabled={approveMutation.isPending}
                className="flex-1 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
              >
                {approveMutation.isPending ? "Approving..." : "✓ Approve"}
              </button>
            )}

            {canExecute && (
              <button
                onClick={() => executeMutation.mutate(dryRun)}
                disabled={executeMutation.isPending}
                className="flex-1 px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-50"
              >
                {executeMutation.isPending
                  ? "Executing..."
                  : dryRun
                  ? "🔍 Dry Run"
                  : "▶ Execute"}
              </button>
            )}

            {canCancel && (
              <button
                onClick={() => cancelMutation.mutate()}
                disabled={cancelMutation.isPending}
                className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 disabled:opacity-50"
              >
                {cancelMutation.isPending ? "Cancelling..." : "✕ Cancel"}
              </button>
            )}

            {canRollback && (
              <button
                onClick={() => rollbackMutation.mutate()}
                disabled={rollbackMutation.isPending}
                className="px-4 py-2 bg-orange-500 text-white rounded hover:bg-orange-600 disabled:opacity-50"
              >
                {rollbackMutation.isPending ? "Rolling back..." : "↶ Rollback"}
              </button>
            )}

            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
