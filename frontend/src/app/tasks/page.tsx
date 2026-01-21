"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import { Task, TaskStatus, TaskPriority } from "@/types";
import { format } from "date-fns";
import { ja } from "date-fns/locale";
import { Plus, Loader2, CheckCircle2, Circle, Clock, AlertCircle } from "lucide-react";
import { clsx } from "clsx";
import Link from "next/link";

const statusIcons = {
  [TaskStatus.TODO]: Circle,
  [TaskStatus.IN_PROGRESS]: Clock,
  [TaskStatus.DONE]: CheckCircle2,
  [TaskStatus.ON_HOLD]: AlertCircle,
};

const statusColors = {
  [TaskStatus.TODO]: "text-gray-400",
  [TaskStatus.IN_PROGRESS]: "text-blue-500",
  [TaskStatus.DONE]: "text-green-500",
  [TaskStatus.ON_HOLD]: "text-yellow-500",
};

const priorityColors = {
  [TaskPriority.LOW]: "bg-gray-100 text-gray-700",
  [TaskPriority.MEDIUM]: "bg-blue-100 text-blue-700",
  [TaskPriority.HIGH]: "bg-orange-100 text-orange-700",
  [TaskPriority.URGENT]: "bg-red-100 text-red-700",
};

export default function TasksPage() {
  const queryClient = useQueryClient();

  const { data: tasksData, isLoading } = useQuery({
    queryKey: ["tasks"],
    queryFn: () => apiClient.getTasks({ page: 1, page_size: 100 }),
  });

  const updateTaskMutation = useMutation({
    mutationFn: ({ taskId, status }: { taskId: number; status: TaskStatus }) =>
      apiClient.patchTask(taskId, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
  });

  const tasks = tasksData?.items || [];
  const todoTasks = tasks.filter((t) => t.status === TaskStatus.TODO);
  const inProgressTasks = tasks.filter((t) => t.status === TaskStatus.IN_PROGRESS);
  const doneTasks = tasks.filter((t) => t.status === TaskStatus.DONE);

  const handleStatusChange = (task: Task, newStatus: TaskStatus) => {
    updateTaskMutation.mutate({ taskId: task.task_id, status: newStatus });
  };

  const renderTask = (task: Task) => {
    const StatusIcon = statusIcons[task.status];

    return (
      <div
        key={task.task_id}
        className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
      >
        <div className="flex items-start gap-3">
          <button
            onClick={() => {
              const nextStatus =
                task.status === TaskStatus.TODO
                  ? TaskStatus.IN_PROGRESS
                  : task.status === TaskStatus.IN_PROGRESS
                  ? TaskStatus.DONE
                  : TaskStatus.TODO;
              handleStatusChange(task, nextStatus);
            }}
            className={clsx(
              "mt-1 flex-shrink-0",
              statusColors[task.status],
              "hover:opacity-70 transition-opacity"
            )}
          >
            <StatusIcon className="w-5 h-5" />
          </button>

          <div className="flex-1 min-w-0">
            <h3 className={clsx(
              "font-medium text-gray-900",
              task.status === TaskStatus.DONE && "line-through text-gray-500"
            )}>
              {task.title}
            </h3>

            {task.description && (
              <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                {task.description}
              </p>
            )}

            <div className="flex flex-wrap items-center gap-2 mt-3">
              <span
                className={clsx(
                  "px-2 py-1 text-xs font-medium rounded",
                  priorityColors[task.priority]
                )}
              >
                {task.priority}
              </span>

              {task.due_date && (
                <span className="text-xs text-gray-500">
                  期限: {format(new Date(task.due_date), "M月d日", { locale: ja })}
                </span>
              )}

              {task.parent_task_id && (
                <span className="text-xs text-gray-500">サブタスク</span>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  };

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
          <h2 className="text-xl font-semibold text-gray-900">タスク</h2>
          <p className="text-sm text-gray-500 mt-1">
            {tasks.length}件のタスク
          </p>
        </div>
        <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2">
          <Plus className="w-4 h-4" />
          新規タスク
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-6 py-6">
        {tasks.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <p className="text-gray-500">タスクはありません</p>
              <p className="text-sm text-gray-400 mt-2">
                チャットからタスクを作成してください
              </p>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* TODO Column */}
            <div>
              <h3 className="font-semibold text-gray-700 mb-4 flex items-center gap-2">
                <Circle className="w-4 h-4 text-gray-400" />
                TODO ({todoTasks.length})
              </h3>
              <div className="space-y-3">
                {todoTasks.map(renderTask)}
              </div>
            </div>

            {/* In Progress Column */}
            <div>
              <h3 className="font-semibold text-gray-700 mb-4 flex items-center gap-2">
                <Clock className="w-4 h-4 text-blue-500" />
                進行中 ({inProgressTasks.length})
              </h3>
              <div className="space-y-3">
                {inProgressTasks.map(renderTask)}
              </div>
            </div>

            {/* Done Column */}
            <div>
              <h3 className="font-semibold text-gray-700 mb-4 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-green-500" />
                完了 ({doneTasks.length})
              </h3>
              <div className="space-y-3">
                {doneTasks.map(renderTask)}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
