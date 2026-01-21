"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import { TaskDraft, DraftStatus } from "@/types";
import { format } from "date-fns";
import { ja } from "date-fns/locale";
import { Check, X, Loader2, FileText } from "lucide-react";

export default function DraftsPage() {
  const queryClient = useQueryClient();

  const { data: draftsData, isLoading } = useQuery({
    queryKey: ["drafts"],
    queryFn: () => apiClient.getDrafts({ status: "pending", page: 1, page_size: 50 }),
  });

  const acceptMutation = useMutation({
    mutationFn: (draftId: number) => apiClient.acceptDraft(draftId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["drafts"] });
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
  });

  const rejectMutation = useMutation({
    mutationFn: (draftId: number) => apiClient.rejectDraft(draftId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["drafts"] });
    },
  });

  const drafts = draftsData?.items || [];
  const pendingDrafts = drafts.filter((d) => d.status === DraftStatus.PENDING);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <h2 className="text-xl font-semibold text-gray-900">Draft</h2>
        <p className="text-sm text-gray-500 mt-1">
          {pendingDrafts.length}件のタスク案が承認待ちです
        </p>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-6 py-6">
        {pendingDrafts.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <FileText className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">承認待ちのDraftはありません</p>
              <p className="text-sm text-gray-400 mt-2">
                チャットでタスクを入力すると、ここに表示されます
              </p>
            </div>
          </div>
        ) : (
          <div className="max-w-4xl mx-auto space-y-4">
            {pendingDrafts.map((draft) => (
              <div
                key={draft.draft_id}
                className="bg-white border border-gray-200 rounded-lg p-6 hover:shadow-lg transition-shadow"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0 mr-4">
                    <h3 className="text-lg font-semibold text-gray-900">
                      {draft.title}
                    </h3>

                    {draft.description && (
                      <p className="text-gray-600 mt-2">{draft.description}</p>
                    )}

                    <div className="flex flex-wrap gap-3 mt-4">
                      {draft.priority && (
                        <span className="text-sm text-gray-600">
                          優先度: <span className="font-medium">{draft.priority}</span>
                        </span>
                      )}

                      {draft.due_date && (
                        <span className="text-sm text-gray-600">
                          期限:{" "}
                          <span className="font-medium">
                            {format(new Date(draft.due_date), "M月d日", {
                              locale: ja,
                            })}
                          </span>
                        </span>
                      )}

                      {draft.parent_task_id && (
                        <span className="text-sm text-gray-600">
                          親タスクID: {draft.parent_task_id}
                        </span>
                      )}
                    </div>

                    <p className="text-xs text-gray-400 mt-3">
                      作成:{" "}
                      {format(new Date(draft.created_at), "M月d日 HH:mm", {
                        locale: ja,
                      })}
                    </p>
                  </div>

                  <div className="flex gap-2">
                    <button
                      onClick={() => acceptMutation.mutate(draft.draft_id)}
                      disabled={
                        acceptMutation.isPending || rejectMutation.isPending
                      }
                      className="p-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
                      title="承認"
                    >
                      {acceptMutation.isPending ? (
                        <Loader2 className="w-5 h-5 animate-spin" />
                      ) : (
                        <Check className="w-5 h-5" />
                      )}
                    </button>
                    <button
                      onClick={() => rejectMutation.mutate(draft.draft_id)}
                      disabled={
                        acceptMutation.isPending || rejectMutation.isPending
                      }
                      className="p-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
                      title="拒否"
                    >
                      {rejectMutation.isPending ? (
                        <Loader2 className="w-5 h-5 animate-spin" />
                      ) : (
                        <X className="w-5 h-5" />
                      )}
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
