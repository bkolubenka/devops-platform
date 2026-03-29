from sqlalchemy import Column, Integer, String, Text, Boolean
from .database import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    technologies = Column(Text, nullable=False)  # JSON string of technologies
    github_url = Column(String(500))
    demo_url = Column(String(500))
    image_url = Column(String(500))
    is_active = Column(Boolean, default=True)

class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    level = Column(Integer, nullable=False)  # 1-5
    category = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)