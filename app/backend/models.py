from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from .database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    technologies = Column(Text, nullable=False)
    github_url = Column(String(500))
    demo_url = Column(String(500))
    image_url = Column(String(500))
    category = Column(String(100), default="Platform")
    status = Column(String(50), default="active")
    owner = Column(String(100))
    featured = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    level = Column(Integer, nullable=False)
    category = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)


class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    service_type = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    url = Column(String(500))
    port = Column(Integer)
    health_endpoint = Column(String(500))
    environment = Column(String(50), default="dev")
    status = Column(String(50), default="running")
    owner = Column(String(100))
    runtime_target = Column(String(120))
    control_mode = Column(String(50), default="observe")
    is_active = Column(Boolean, default=True)


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    affected_service_id = Column(Integer)
    severity = Column(String(50), nullable=False, default="medium")
    summary = Column(Text, nullable=False)
    symptoms = Column(Text, nullable=False)
    recent_changes = Column(Text)
    status = Column(String(50), nullable=False, default="open")
    source = Column(String(100), default="manual")
    event_type = Column(String(100), default="incident")
    overview_snapshot = Column(Text)
    analysis = Column(Text)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
