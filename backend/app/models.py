import uuid
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from .database import Base



class Upload(Base):
    __tablename__ = "uploads"

    pk = Column(Integer, primary_key=True, autoincrement=True)   # ⭐ internal row identity

    id = Column(UUID(as_uuid=True))   # ⭐ upload batch id (same for file)

    original_filename = Column(String, nullable=False)

    first_name = Column(String)
    last_name = Column(String)
    state = Column(String)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))



class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    status = Column(String, default="processing")
    input_file = Column(String)
    output_file = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)

    
class Output(Base):
    __tablename__ = "outputs"

    pk = Column(Integer, primary_key=True, autoincrement=True)   # internal row identity

    id = Column(UUID(as_uuid=True))   # ⭐ batch id (same per file)

    output_file = Column(String)

    first_name = Column(String)
    last_name = Column(String)
    state = Column(String)

    found_first_name = Column(String)
    found_last_name = Column(String)
    found_state = Column(String)

    full_name = Column(String)
    npi = Column(String)

    mailing_address = Column(String)
    primary_practice_address = Column(String)
    secondary_practice_address = Column(String)

    taxonomy = Column(String)
    specialty = Column(String)
    license = Column(String)

    status = Column(String)
    ai_confidence = Column(String)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))