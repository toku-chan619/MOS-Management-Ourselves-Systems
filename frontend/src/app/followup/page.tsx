"use client";

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import { Loader2, Clock, Sun, Sunset, Moon } from "lucide-react";
import { format } from "date-fns";
import { ja } from "date-fns/locale";
import { FollowupPeriod } from "@/types";

const periodIcons = {
  [FollowupPeriod.MORNING]: Sun,
  [FollowupPeriod.NOON]: Sunset,
  [FollowupPeriod.EVENING]: Moon,
};

const periodColors = {
  [FollowupPeriod.MORNING]: "text-yellow-500",
  [FollowupPeriod.NOON]: "text-orange-500",
  [FollowupPeriod.EVENING]: "text-indigo-500",
};

const periodLabels = {
  [FollowupPeriod.MORNING]: "朝",
  [FollowupPeriod.NOON]: "昼",
  [FollowupPeriod.EVENING]: "夕",
};

export default function FollowupPage() {
  const { data: followupsData, isLoading } = useQuery({
    queryKey: ["followups"],
    queryFn: () => apiClient.getFollowups({ page: 1, page_size: 30 }),
  });

  const followups = followupsData?.items || [];

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
        <h2 className="text-xl font-semibold text-gray-900">フォローアップ</h2>
        <p className="text-sm text-gray-500 mt-1">
          朝・昼・夕の定期的なタスク要約
        </p>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-6 py-6">
        {followups.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <Clock className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">フォローアップはありません</p>
              <p className="text-sm text-gray-400 mt-2">
                定期的なフォローアップがここに表示されます
              </p>
            </div>
          </div>
        ) : (
          <div className="max-w-4xl mx-auto space-y-4">
            {followups.map((followup) => {
              const PeriodIcon = periodIcons[followup.period];
              const iconColor = periodColors[followup.period];
              const periodLabel = periodLabels[followup.period];

              return (
                <div
                  key={followup.run_id}
                  className="bg-white border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow"
                >
                  <div className="flex items-start gap-4">
                    <div className={`${iconColor} flex-shrink-0 mt-1`}>
                      <PeriodIcon className="w-6 h-6" />
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="font-semibold text-gray-900">
                          {periodLabel}のフォローアップ
                        </h3>
                        <span className="text-sm text-gray-500">
                          {format(
                            new Date(followup.created_at),
                            "M月d日 HH:mm",
                            { locale: ja }
                          )}
                        </span>
                      </div>

                      {followup.summary ? (
                        <div className="prose prose-sm max-w-none">
                          <p className="text-gray-700 whitespace-pre-wrap">
                            {followup.summary}
                          </p>
                        </div>
                      ) : (
                        <p className="text-sm text-gray-400 italic">
                          要約はまだ生成されていません
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
