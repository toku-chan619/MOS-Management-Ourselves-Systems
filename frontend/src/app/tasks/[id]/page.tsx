"use client";

import { use, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import { Task, TaskStatus, TaskPriority } from "@/types";
import TaskActions from "@/components/TaskActions";

export default function TaskDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const resolvedParams = use(params);
  const router = useRouter();
  const queryClient = useQueryClient();
  const [isEditing, setIsEditing] = useState(false);
  const [editForm, setEditForm] = useState<Partial<Task>>({});

  // Fetch task details
  const {
    data: task,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["task", resolvedParams.id],
    queryFn: () => apiClient.getTask(parseInt(resolvedParams.id)),
  });

  // Update task mutation
  const updateMutation = useMutation({
    mutationFn: (updates: Partial<Task>) =>
      apiClient.patchTask(parseInt(resolvedParams.id), updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["task", resolvedParams.id] });
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
      setIsEditing(false);
    },
  });

  // Delete task mutation
  const deleteMutation = useMutation({
    mutationFn: () => apiClient.deleteTask(parseInt(resolvedParams.id)),
    onSuccess: () => {
      router.push("/tasks");
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-lg">Loading task...</div>
      </div>
    );
  }

  if (error || !task) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-lg text-red-500">
          Error loading task: {error?.message || "Task not found"}
        </div>
      </div>
    );
  }

  const handleEdit = () => {
    setEditForm({
      title: task.title,
      description: task.description,
      status: task.status,
      priority: task.priority,
      due_date: task.due_date,
      due_time: task.due_time,
    });
    setIsEditing(true);
  };

  const handleSave = () => {
    updateMutation.mutate(editForm);
  };

  const handleDelete = () => {
    if (confirm("Are you sure you want to delete this task?")) {
      deleteMutation.mutate();
    }
  };

  const getStatusColor = (status: TaskStatus) => {
    switch (status) {
      case TaskStatus.TODO:
        return "bg-gray-100 text-gray-800";
      case TaskStatus.IN_PROGRESS:
        return "bg-blue-100 text-blue-800";
      case TaskStatus.DONE:
        return "bg-green-100 text-green-800";
      case TaskStatus.ON_HOLD:
        return "bg-yellow-100 text-yellow-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  const getPriorityColor = (priority: TaskPriority) => {
    switch (priority) {
      case TaskPriority.LOW:
        return "bg-gray-100 text-gray-600";
      case TaskPriority.MEDIUM:
        return "bg-blue-100 text-blue-600";
      case TaskPriority.HIGH:
        return "bg-orange-100 text-orange-600";
      case TaskPriority.URGENT:
        return "bg-red-100 text-red-600";
      default:
        return "bg-gray-100 text-gray-600";
    }
  };

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex justify-between items-start mb-6">
        <button
          onClick={() => router.back()}
          className="text-gray-600 hover:text-gray-900"
        >
          ← Back
        </button>
        <div className="flex gap-2">
          {!isEditing ? (
            <>
              <button
                onClick={handleEdit}
                className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
              >
                Edit
              </button>
              <button
                onClick={handleDelete}
                className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
              >
                Delete
              </button>
            </>
          ) : (
            <>
              <button
                onClick={handleSave}
                disabled={updateMutation.isPending}
                className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-50"
              >
                Save
              </button>
              <button
                onClick={() => setIsEditing(false)}
                className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600"
              >
                Cancel
              </button>
            </>
          )}
        </div>
      </div>

      {/* Task Details */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        {/* Title */}
        {!isEditing ? (
          <h1 className="text-3xl font-bold mb-4">{task.title}</h1>
        ) : (
          <input
            type="text"
            value={editForm.title || ""}
            onChange={(e) =>
              setEditForm({ ...editForm, title: e.target.value })
            }
            className="text-3xl font-bold mb-4 w-full border-b-2 border-gray-300 focus:border-blue-500 outline-none"
          />
        )}

        {/* Status and Priority */}
        <div className="flex gap-4 mb-4">
          {!isEditing ? (
            <>
              <span
                className={`px-3 py-1 rounded-full text-sm font-semibold ${getStatusColor(
                  task.status
                )}`}
              >
                {task.status}
              </span>
              <span
                className={`px-3 py-1 rounded-full text-sm font-semibold ${getPriorityColor(
                  task.priority
                )}`}
              >
                {task.priority}
              </span>
            </>
          ) : (
            <>
              <select
                value={editForm.status || task.status}
                onChange={(e) =>
                  setEditForm({
                    ...editForm,
                    status: e.target.value as TaskStatus,
                  })
                }
                className="px-3 py-1 rounded border border-gray-300"
              >
                {Object.values(TaskStatus).map((status) => (
                  <option key={status} value={status}>
                    {status}
                  </option>
                ))}
              </select>
              <select
                value={editForm.priority || task.priority}
                onChange={(e) =>
                  setEditForm({
                    ...editForm,
                    priority: e.target.value as TaskPriority,
                  })
                }
                className="px-3 py-1 rounded border border-gray-300"
              >
                {Object.values(TaskPriority).map((priority) => (
                  <option key={priority} value={priority}>
                    {priority}
                  </option>
                ))}
              </select>
            </>
          )}
        </div>

        {/* Due Date */}
        {(task.due_date || isEditing) && (
          <div className="mb-4">
            <span className="text-gray-600 font-semibold">Due: </span>
            {!isEditing ? (
              <span>{task.due_date || "Not set"}</span>
            ) : (
              <input
                type="date"
                value={editForm.due_date || ""}
                onChange={(e) =>
                  setEditForm({ ...editForm, due_date: e.target.value })
                }
                className="px-2 py-1 border border-gray-300 rounded"
              />
            )}
          </div>
        )}

        {/* Description */}
        <div className="mb-4">
          <h2 className="text-xl font-semibold mb-2">Description</h2>
          {!isEditing ? (
            <p className="text-gray-700 whitespace-pre-wrap">
              {task.description || "No description"}
            </p>
          ) : (
            <textarea
              value={editForm.description || ""}
              onChange={(e) =>
                setEditForm({ ...editForm, description: e.target.value })
              }
              rows={5}
              className="w-full p-2 border border-gray-300 rounded focus:border-blue-500 outline-none"
            />
          )}
        </div>

        {/* Timestamps */}
        <div className="text-sm text-gray-500 space-y-1">
          <div>Created: {new Date(task.created_at).toLocaleString()}</div>
          <div>Updated: {new Date(task.updated_at).toLocaleString()}</div>
          {task.completed_at && (
            <div>
              Completed: {new Date(task.completed_at).toLocaleString()}
            </div>
          )}
        </div>
      </div>

      {/* Task Actions Section */}
      <TaskActions taskId={resolvedParams.id} task={task} />
    </div>
  );
}
