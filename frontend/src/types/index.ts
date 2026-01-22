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

// Action-related types
export enum ActionStatus {
  PROPOSED = "proposed",
  APPROVED = "approved",
  EXECUTING = "executing",
  COMPLETED = "completed",
  FAILED = "failed",
  CANCELLED = "cancelled",
}

export enum ActionType {
  SEND_EMAIL = "send_email",
  FETCH_WEB_INFO = "fetch_web_info",
  SEARCH_WEB = "search_web",
  SET_REMINDER = "set_reminder",
  CALCULATE = "calculate",
  CREATE_CALENDAR_EVENT = "create_calendar_event",
}

export interface TaskAction {
  action_id: string;
  task_id: string;
  action_type: ActionType;
  status: ActionStatus;
  parameters: Record<string, any>;
  reasoning: string;
  confidence: number;
  result: Record<string, any> | null;
  created_at: string;
  approved_at: string | null;
  executed_at: string | null;
  completed_at: string | null;
}

export interface ActionProposal {
  action_type: ActionType;
  parameters: Record<string, any>;
  reasoning: string;
  confidence: number;
}

export interface ProposeActionsRequest {
  task_title: string;
  task_description?: string | null;
  task_metadata?: Record<string, any>;
}

export interface CreateActionRequest {
  action_type: string;
  parameters: Record<string, any>;
  reasoning: string;
  confidence?: number;
}

export interface ExecuteActionRequest {
  dry_run?: boolean;
}

export interface ExecuteActionResponse {
  success: boolean;
  data?: Record<string, any> | null;
  error?: string | null;
}

// API Response types
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
