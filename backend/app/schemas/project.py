"""Project-related schemas"""

from datetime import datetime
from uuid import UUID
from typing import Optional
from pydantic import BaseModel, Field


class ProjectBase(BaseModel):
    """Base project schema"""
    name: str = Field(min_length=1, max_length=200)
    is_archived: bool = Field(default=False)


class ProjectCreate(ProjectBase):
    """Schema for creating a project"""
    pass


class ProjectUpdate(BaseModel):
    """Schema for updating a project"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    is_archived: Optional[bool] = None


class ProjectResponse(ProjectBase):
    """Schema for project response"""
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
