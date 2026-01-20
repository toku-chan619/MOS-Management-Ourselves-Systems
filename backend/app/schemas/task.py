"""Task-related schemas"""

from datetime import date, time, datetime
from uuid import UUID
from typing import Optional
from pydantic import BaseModel, Field

from app.core.enums import TaskStatus, TaskPriority


class TaskBase(BaseModel):
    """Base task schema"""
    title: str = Field(min_length=1, max_length=500)
    description: str = Field(default="", max_length=5000)
    status: TaskStatus = Field(default=TaskStatus.BACKLOG)
    priority: TaskPriority = Field(default=TaskPriority.NORMAL)
    due_date: Optional[date] = None
    due_time: Optional[time] = None
    project_id: Optional[UUID] = None
    parent_task_id: Optional[UUID] = None
    sort_order: int = Field(default=0)


class TaskCreate(TaskBase):
    """Schema for creating a task"""
    pass


class TaskUpdate(BaseModel):
    """Schema for updating a task (all fields optional)"""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = Field(None, max_length=5000)
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[date] = None
    due_time: Optional[time] = None
    project_id: Optional[UUID] = None
    parent_task_id: Optional[UUID] = None
    sort_order: Optional[int] = None


class TaskResponse(TaskBase):
    """Schema for task response"""
    id: UUID
    source: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskTreeNode(TaskResponse):
    """Schema for task tree node with children"""
    children: list["TaskTreeNode"] = []

    class Config:
        from_attributes = True
