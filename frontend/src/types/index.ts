// Task-related types
export enum TaskStatus {
  TODO = "todo",
  IN_PROGRESS = "in_progress",
  DONE = "done",
  ON_HOLD = "on_hold",
}

export enum TaskPriority {
  LOW = "low",
  MEDIUM = "medium",
  HIGH = "high",
  URGENT = "urgent",
}

export interface Task {
  task_id: number;
  title: string;
  description: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  due_date: string | null;
  due_time: string | null;
  project_id: number | null;
  parent_task_id: number | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  is_deleted: boolean;
}

export interface TaskTree extends Task {
  subtasks: TaskTree[];
}

export interface TaskCreate {
  title: string;
  description?: string | null;
  status?: TaskStatus;
  priority?: TaskPriority;
  due_date?: string | null;
  due_time?: string | null;
  project_id?: number | null;
  parent_task_id?: number | null;
}

export interface TaskUpdate {
  title?: string;
  description?: string | null;
  status?: TaskStatus;
  priority?: TaskPriority;
  due_date?: string | null;
  due_time?: string | null;
  project_id?: number | null;
  parent_task_id?: number | null;
}

// Project-related types
export interface Project {
  project_id: number;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
  is_deleted: boolean;
}

export interface ProjectCreate {
  name: string;
  description?: string | null;
}

export interface ProjectUpdate {
  name?: string;
  description?: string | null;
}

// Draft-related types
export enum DraftStatus {
  PENDING = "pending",
  ACCEPTED = "accepted",
  REJECTED = "rejected",
}

export interface TaskDraft {
  draft_id: number;
  message_id: number;
  title: string;
  description: string | null;
  status: DraftStatus;
  priority: TaskPriority | null;
  due_date: string | null;
  due_time: string | null;
  project_id: number | null;
  parent_task_id: number | null;
  created_at: string;
  updated_at: string;
  accepted_at: string | null;
  rejected_at: string | null;
}

// Chat-related types
export enum MessageRole {
  USER = "user",
  ASSISTANT = "assistant",
}

export interface Message {
  message_id: number;
  role: MessageRole;
  content: string;
  created_at: string;
  agent_run_id: number | null;
}

export interface MessageCreate {
  content: string;
}

// Followup-related types
export enum FollowupPeriod {
  MORNING = "morning",
  NOON = "noon",
  EVENING = "evening",
}

export interface FollowupRun {
  run_id: number;
  period: FollowupPeriod;
  summary: string | null;
  created_at: string;
}

// API Response types
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
