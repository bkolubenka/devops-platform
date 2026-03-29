from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json
import os
from sqlalchemy.orm import Session
from .database import get_db, engine, Base
from .models import Project as DBProject, Skill as DBSkill

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="DevOps Platform API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for API
class Project(BaseModel):
    id: int
    title: str
    description: str
    technologies: List[str]
    github_url: Optional[str] = None
    demo_url: Optional[str] = None
    image_url: Optional[str] = None

    class Config:
        from_attributes = True

class Skill(BaseModel):
    id: int
    name: str
    level: int
    category: str

    class Config:
        from_attributes = True

class ProjectCreate(BaseModel):
    title: str
    description: str
    technologies: List[str]
    github_url: Optional[str] = None
    demo_url: Optional[str] = None
    image_url: Optional[str] = None

class SkillCreate(BaseModel):
    name: str
    level: int
    category: str

# AI/ML models
class TextGenerationRequest(BaseModel):
    prompt: str
    max_length: Optional[int] = 100

class TextGenerationResponse(BaseModel):
    generated_text: str

def initialize_sample_data(db: Session):
    """Initialize database with sample data if empty"""
    # Check if data already exists
    if db.query(DBProject).count() > 0:
        return

    # Sample projects
    projects_data = [
        {
            "title": "DevOps Platform",
            "description": "Full-cycle DevOps project with containerized fullstack application, Infrastructure as Code, and CI/CD automation.",
            "technologies": ["Python", "FastAPI", "Docker", "Nginx", "Ansible", "GitHub Actions"],
            "github_url": "https://github.com/yourusername/devops-platform",
            "demo_url": "https://yourdomain.com"
        },
        {
            "title": "ML Portfolio Predictor",
            "description": "Machine learning model for predicting portfolio performance using historical data and market indicators.",
            "technologies": ["Python", "TensorFlow", "Pandas", "Scikit-learn"],
            "github_url": "https://github.com/yourusername/ml-portfolio"
        }
    ]

    for project_data in projects_data:
        project = DBProject(
            title=project_data["title"],
            description=project_data["description"],
            technologies=json.dumps(project_data["technologies"]),
            github_url=project_data.get("github_url"),
            demo_url=project_data.get("demo_url")
        )
        db.add(project)

    # Sample skills
    skills_data = [
        {"name": "Python", "level": 5, "category": "Backend"},
        {"name": "FastAPI", "level": 4, "category": "Backend"},
        {"name": "Docker", "level": 4, "category": "DevOps"},
        {"name": "Kubernetes", "level": 3, "category": "DevOps"},
        {"name": "AWS", "level": 4, "category": "Cloud"},
        {"name": "Machine Learning", "level": 3, "category": "AI/ML"},
        {"name": "React", "level": 3, "category": "Frontend"},
        {"name": "Ansible", "level": 4, "category": "Infrastructure"}
    ]

    for skill_data in skills_data:
        skill = DBSkill(**skill_data)
        db.add(skill)

    db.commit()

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    db = next(get_db())
    try:
        initialize_sample_data(db)
    finally:
        db.close()

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

@app.get("/")
def root() -> dict[str, str]:
    return {"message": "DevOps Platform API running"}

# Portfolio endpoints
@app.get("/api/portfolio/projects")
def get_projects(db: Session = Depends(get_db)) -> List[Project]:
    projects = db.query(DBProject).filter(DBProject.is_active == True).all()
    result = []
    for project in projects:
        result.append(Project(
            id=project.id,
            title=project.title,
            description=project.description,
            technologies=json.loads(project.technologies),
            github_url=project.github_url,
            demo_url=project.demo_url,
            image_url=project.image_url
        ))
    return result

@app.get("/api/portfolio/projects/{project_id}")
def get_project(project_id: int, db: Session = Depends(get_db)) -> Project:
    project = db.query(DBProject).filter(DBProject.id == project_id, DBProject.is_active == True).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return Project(
        id=project.id,
        title=project.title,
        description=project.description,
        technologies=json.loads(project.technologies),
        github_url=project.github_url,
        demo_url=project.demo_url,
        image_url=project.image_url
    )

@app.post("/api/portfolio/projects")
def create_project(project: ProjectCreate, db: Session = Depends(get_db)) -> Project:
    db_project = DBProject(
        title=project.title,
        description=project.description,
        technologies=json.dumps(project.technologies),
        github_url=project.github_url,
        demo_url=project.demo_url,
        image_url=project.image_url
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)

    return Project(
        id=db_project.id,
        title=db_project.title,
        description=db_project.description,
        technologies=json.loads(db_project.technologies),
        github_url=db_project.github_url,
        demo_url=db_project.demo_url,
        image_url=db_project.image_url
    )

@app.get("/api/portfolio/skills")
def get_skills(db: Session = Depends(get_db)) -> List[Skill]:
    skills = db.query(DBSkill).filter(DBSkill.is_active == True).all()
    return [Skill.from_orm(skill) for skill in skills]

@app.post("/api/portfolio/skills")
def create_skill(skill: SkillCreate, db: Session = Depends(get_db)) -> Skill:
    db_skill = DBSkill(**skill.dict())
    db.add(db_skill)
    db.commit()
    db.refresh(db_skill)
    return Skill.from_orm(db_skill)

# AI/ML endpoints
@app.post("/api/ai/generate-text")
def generate_text(request: TextGenerationRequest) -> TextGenerationResponse:
    """
    Simple text generation endpoint (placeholder for actual ML model)
    In a real implementation, this would use a pre-trained model like GPT
    """
    # Placeholder implementation - in real scenario, load a model
    prompt = request.prompt.lower()

    if "hello" in prompt:
        generated = "Hello! I'm an AI assistant powered by this DevOps platform. How can I help you today?"
    elif "portfolio" in prompt:
        generated = "This platform showcases various projects including DevOps automation, machine learning models, and web applications."
    elif "devops" in prompt:
        generated = "DevOps combines development and operations to improve software delivery. This platform demonstrates CI/CD, containerization, and infrastructure automation."
    else:
        generated = f"Thank you for your input: '{request.prompt}'. This is a demo AI response. In production, this would use advanced language models."

    return TextGenerationResponse(generated_text=generated[:request.max_length])

@app.get("/api/ai/models")
def get_available_models() -> dict:
    """
    Return information about available AI models
    """
    return {
        "models": [
            {
                "name": "text-generator-v1",
                "type": "text-generation",
                "description": "Basic text generation model for demo purposes"
            }
        ],
        "status": "demo"
    }
