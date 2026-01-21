import axios, { AxiosInstance } from "axios";
import type {
  Task,
  TaskTree,
  TaskCreate,
  TaskUpdate,
  Project,
  ProjectCreate,
  ProjectUpdate,
  TaskDraft,
  Message,
  MessageCreate,
  FollowupRun,
  PaginatedResponse,
} from "@/types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class APIClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: `${API_BASE_URL}/api`,
      headers: {
        "Content-Type": "application/json",
      },
    });
  }

  // Tasks API
  async getTasks(params?: {
    status?: string;
    priority?: string;
    project_id?: number;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<Task>> {
    const { data } = await this.client.get("/tasks", { params });
    return data;
  }

  async getTask(taskId: number): Promise<Task> {
    const { data } = await this.client.get(`/tasks/${taskId}`);
    return data;
  }

  async getTaskTree(taskId: number): Promise<TaskTree> {
    const { data } = await this.client.get(`/tasks/${taskId}/tree`);
    return data;
  }

  async createTask(task: TaskCreate): Promise<Task> {
    const { data } = await this.client.post("/tasks", task);
    return data;
  }

  async updateTask(taskId: number, task: TaskUpdate): Promise<Task> {
    const { data } = await this.client.put(`/tasks/${taskId}`, task);
    return data;
  }

  async patchTask(taskId: number, task: Partial<TaskUpdate>): Promise<Task> {
    const { data } = await this.client.patch(`/tasks/${taskId}`, task);
    return data;
  }

  async deleteTask(taskId: number): Promise<void> {
    await this.client.delete(`/tasks/${taskId}`);
  }

  // Projects API
  async getProjects(params?: {
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<Project>> {
    const { data } = await this.client.get("/projects", { params });
    return data;
  }

  async getProject(projectId: number): Promise<Project> {
    const { data } = await this.client.get(`/projects/${projectId}`);
    return data;
  }

  async getProjectTasks(
    projectId: number,
    params?: { page?: number; page_size?: number }
  ): Promise<PaginatedResponse<Task>> {
    const { data } = await this.client.get(`/projects/${projectId}/tasks`, {
      params,
    });
    return data;
  }

  async createProject(project: ProjectCreate): Promise<Project> {
    const { data } = await this.client.post("/projects", project);
    return data;
  }

  async updateProject(
    projectId: number,
    project: ProjectUpdate
  ): Promise<Project> {
    const { data } = await this.client.put(`/projects/${projectId}`, project);
    return data;
  }

  async deleteProject(projectId: number, force: boolean = false): Promise<void> {
    await this.client.delete(`/projects/${projectId}`, {
      params: { force },
    });
  }

  // Drafts API
  async getDrafts(params?: {
    status?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<TaskDraft>> {
    const { data } = await this.client.get("/drafts", { params });
    return data;
  }

  async getDraft(draftId: number): Promise<TaskDraft> {
    const { data } = await this.client.get(`/drafts/${draftId}`);
    return data;
  }

  async acceptDraft(draftId: number): Promise<Task> {
    const { data } = await this.client.post(`/drafts/${draftId}/accept`);
    return data;
  }

  async rejectDraft(draftId: number): Promise<TaskDraft> {
    const { data } = await this.client.post(`/drafts/${draftId}/reject`);
    return data;
  }

  // Chat API
  async getMessages(params?: {
    role?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<Message>> {
    const { data } = await this.client.get("/chat/messages", { params });
    return data;
  }

  async getMessage(messageId: number): Promise<Message> {
    const { data } = await this.client.get(`/chat/messages/${messageId}`);
    return data;
  }

  async sendMessage(message: MessageCreate): Promise<{
    message: Message;
    drafts: TaskDraft[];
  }> {
    const { data } = await this.client.post("/chat/messages", message);
    return data;
  }

  // Followup API
  async getFollowups(params?: {
    period?: string;
    start_date?: string;
    end_date?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<FollowupRun>> {
    const { data } = await this.client.get("/followup", { params });
    return data;
  }

  async getFollowup(runId: number): Promise<FollowupRun> {
    const { data } = await this.client.get(`/followup/${runId}`);
    return data;
  }

  async triggerFollowup(period: string): Promise<FollowupRun> {
    const { data } = await this.client.post("/followup/trigger", { period });
    return data;
  }
}

// Export singleton instance
export const apiClient = new APIClient();
