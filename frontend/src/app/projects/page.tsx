"use client";

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import { Loader2, FolderKanban, Plus } from "lucide-react";
import { format } from "date-fns";
import { ja } from "date-fns/locale";

export default function ProjectsPage() {
  const { data: projectsData, isLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: () => apiClient.getProjects({ page: 1, page_size: 50 }),
  });

  const projects = projectsData?.items || [];

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
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">プロジェクト</h2>
          <p className="text-sm text-gray-500 mt-1">
            {projects.length}件のプロジェクト
          </p>
        </div>
        <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2">
          <Plus className="w-4 h-4" />
          新規プロジェクト
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-6 py-6">
        {projects.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <FolderKanban className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">プロジェクトはありません</p>
              <p className="text-sm text-gray-400 mt-2">
                プロジェクトを作成してタスクを整理しましょう
              </p>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {projects.map((project) => (
              <div
                key={project.project_id}
                className="bg-white border border-gray-200 rounded-lg p-6 hover:shadow-lg transition-shadow cursor-pointer"
              >
                <div className="flex items-start gap-3">
                  <FolderKanban className="w-6 h-6 text-blue-600 flex-shrink-0 mt-1" />
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-gray-900 truncate">
                      {project.name}
                    </h3>
                    {project.description && (
                      <p className="text-sm text-gray-600 mt-2 line-clamp-2">
                        {project.description}
                      </p>
                    )}
                    <p className="text-xs text-gray-400 mt-3">
                      作成:{" "}
                      {format(new Date(project.created_at), "M月d日", {
                        locale: ja,
                      })}
                    </p>
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
