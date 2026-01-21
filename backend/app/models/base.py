from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB

class Base(DeclarativeBase):
    # Use JSON for SQLite compatibility (JSONB for PostgreSQL)
    type_annotation_map = {
        dict: JSON().with_variant(JSONB(), "postgresql")
    }
