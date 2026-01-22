"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import {
  Task,
  TaskAction,
  ActionProposal,
  ActionStatus,
  ActionType,
} from "@/types";
import ActionProposalCard from "./ActionProposalCard";
import ActionHistoryList from "./ActionHistoryList";
import ActionModal from "./ActionModal";

interface TaskActionsProps {
  taskId: string;
  task: Task;
}

export default function TaskActions({ taskId, task }: TaskActionsProps) {
  const queryClient = useQueryClient();
  const [showProposals, setShowProposals] = useState(false);
  const [selectedAction, setSelectedAction] = useState<TaskAction | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Fetch task actions
  const { data: actions = [], isLoading: actionsLoading } = useQuery({
    queryKey: ["task-actions", taskId],
    queryFn: () => apiClient.getTaskActions(taskId),
  });

  // Propose actions mutation
  const proposeMutation = useMutation({
    mutationFn: () =>
      apiClient.proposeActions(taskId, {
        task_title: task.title,
        task_description: task.description,
        task_metadata: {
          priority: task.priority,
          due_date: task.due_date,
          status: task.status,
        },
      }),
    onSuccess: (proposals) => {
      setShowProposals(true);
    },
  });

  // Create action mutation
  const createMutation = useMutation({
    mutationFn: (proposal: ActionProposal) =>
      apiClient.createAction(taskId, {
        action_type: proposal.action_type,
        parameters: proposal.parameters,
        reasoning: proposal.reasoning,
        confidence: proposal.confidence,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["task-actions", taskId] });
      proposeMutation.reset();
      setShowProposals(false);
    },
  });

  const handleProposeActions = () => {
    proposeMutation.mutate();
  };

  const handleAcceptProposal = (proposal: ActionProposal) => {
    createMutation.mutate(proposal);
  };

  const handleActionClick = (action: TaskAction) => {
    setSelectedAction(action);
    setIsModalOpen(true);
  };

  const handleModalClose = () => {
    setIsModalOpen(false);
    setSelectedAction(null);
  };

  const getActionTypeLabel = (type: ActionType): string => {
    const labels: Record<ActionType, string> = {
      [ActionType.SEND_EMAIL]: "📧 Send Email",
      [ActionType.FETCH_WEB_INFO]: "🌐 Fetch Web Info",
      [ActionType.SEARCH_WEB]: "🔍 Search Web",
      [ActionType.SET_REMINDER]: "⏰ Set Reminder",
      [ActionType.CALCULATE]: "🧮 Calculate",
      [ActionType.CREATE_CALENDAR_EVENT]: "📅 Calendar Event",
    };
    return labels[type] || type;
  };

  const proposedActions = actions.filter(
    (a) => a.status === ActionStatus.PROPOSED
  );
  const otherActions = actions.filter(
    (a) => a.status !== ActionStatus.PROPOSED
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">Task Actions</h2>
        <button
          onClick={handleProposeActions}
          disabled={proposeMutation.isPending}
          className="px-4 py-2 bg-purple-500 text-white rounded hover:bg-purple-600 disabled:opacity-50"
        >
          {proposeMutation.isPending ? "Analyzing..." : "🤖 Get AI Suggestions"}
        </button>
      </div>

      {/* Error State */}
      {proposeMutation.isError && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          Error getting suggestions: {proposeMutation.error.message}
        </div>
      )}

      {/* Proposals */}
      {showProposals && proposeMutation.data && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-xl font-semibold">AI Suggestions</h3>
            <button
              onClick={() => {
                setShowProposals(false);
                proposeMutation.reset();
              }}
              className="text-gray-500 hover:text-gray-700"
            >
              ✕
            </button>
          </div>

          {proposeMutation.data.length === 0 ? (
            <p className="text-gray-500">
              No actions suggested for this task.
            </p>
          ) : (
            <div className="space-y-4">
              {proposeMutation.data.map((proposal, index) => (
                <ActionProposalCard
                  key={index}
                  proposal={proposal}
                  onAccept={() => handleAcceptProposal(proposal)}
                  isAccepting={createMutation.isPending}
                  getActionTypeLabel={getActionTypeLabel}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Proposed Actions (Pending Approval) */}
      {proposedActions.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-xl font-semibold mb-4">
            Pending Approval ({proposedActions.length})
          </h3>
          <div className="space-y-3">
            {proposedActions.map((action) => (
              <div
                key={action.action_id}
                onClick={() => handleActionClick(action)}
                className="p-4 border border-yellow-200 bg-yellow-50 rounded cursor-pointer hover:bg-yellow-100 transition-colors"
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="font-semibold text-lg">
                      {getActionTypeLabel(action.action_type)}
                    </div>
                    <div className="text-sm text-gray-600 mt-1">
                      {action.reasoning}
                    </div>
                    <div className="text-xs text-gray-500 mt-2">
                      Confidence: {(action.confidence * 100).toFixed(0)}%
                    </div>
                  </div>
                  <span className="px-3 py-1 bg-yellow-200 text-yellow-800 rounded-full text-sm font-semibold">
                    Pending
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Action History */}
      {actionsLoading ? (
        <div className="text-center py-8 text-gray-500">
          Loading actions...
        </div>
      ) : otherActions.length > 0 ? (
        <ActionHistoryList
          actions={otherActions}
          onActionClick={handleActionClick}
          getActionTypeLabel={getActionTypeLabel}
        />
      ) : (
        !proposedActions.length &&
        !showProposals && (
          <div className="bg-gray-50 rounded-lg p-8 text-center">
            <p className="text-gray-500 mb-4">
              No actions yet. Click &quot;Get AI Suggestions&quot; to let AI
              propose helpful actions for this task.
            </p>
          </div>
        )
      )}

      {/* Action Modal */}
      {selectedAction && (
        <ActionModal
          isOpen={isModalOpen}
          onClose={handleModalClose}
          action={selectedAction}
          taskId={taskId}
          getActionTypeLabel={getActionTypeLabel}
        />
      )}
    </div>
  );
}
