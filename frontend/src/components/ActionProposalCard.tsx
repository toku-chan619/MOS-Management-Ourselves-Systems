"use client";

import { ActionProposal, ActionType } from "@/types";

interface ActionProposalCardProps {
  proposal: ActionProposal;
  onAccept: () => void;
  isAccepting: boolean;
  getActionTypeLabel: (type: ActionType) => string;
}

export default function ActionProposalCard({
  proposal,
  onAccept,
  isAccepting,
  getActionTypeLabel,
}: ActionProposalCardProps) {
  const confidencePercent = (proposal.confidence * 100).toFixed(0);
  const confidenceColor =
    proposal.confidence >= 0.7
      ? "text-green-600"
      : proposal.confidence >= 0.5
      ? "text-yellow-600"
      : "text-orange-600";

  return (
    <div className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
      <div className="flex justify-between items-start mb-3">
        <div className="flex-1">
          <h4 className="font-semibold text-lg">
            {getActionTypeLabel(proposal.action_type)}
          </h4>
          <p className="text-sm text-gray-600 mt-1">{proposal.reasoning}</p>
        </div>
        <span className={`text-sm font-semibold ${confidenceColor}`}>
          {confidencePercent}% confident
        </span>
      </div>

      {/* Parameters Preview */}
      <div className="bg-gray-50 rounded p-3 mb-3">
        <div className="text-xs font-semibold text-gray-500 uppercase mb-2">
          Parameters
        </div>
        <div className="space-y-1">
          {Object.entries(proposal.parameters).map(([key, value]) => (
            <div key={key} className="text-sm">
              <span className="font-medium text-gray-700">{key}:</span>{" "}
              <span className="text-gray-600">
                {typeof value === "object"
                  ? JSON.stringify(value)
                  : String(value)}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-2">
        <button
          onClick={onAccept}
          disabled={isAccepting}
          className="flex-1 px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-50"
        >
          {isAccepting ? "Creating..." : "✓ Accept"}
        </button>
        <button
          disabled={isAccepting}
          className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 disabled:opacity-50"
        >
          ✕ Decline
        </button>
      </div>
    </div>
  );
}
