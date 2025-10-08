from fastapi import FastAPI, APIRouter, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt
import os
import logging
from pathlib import Path
import uuid

# Database connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'badgecv')]

# Security
SECRET_KEY = os.environ.get('SECRET_KEY', 'badgecv-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="BadgeCV API", version="1.0.0")
api_router = APIRouter(prefix="/api")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class User(BaseModel):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    name: str
    plan: str = "free"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    industry: Optional[str] = None
    target_roles: List[str] = []

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    industry: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Badge(BaseModel):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str
    issuer: str
    description: str
    image_url: str
    issued_date: datetime
    expiry_date: Optional[datetime] = None
    skills: List[str] = []
    verification_url: str
    badge_class: str
    evidence: Optional[str] = None
    verified: bool = True
    verification_score: float = 1.0

# Security functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# API Routes
@api_router.post("/auth/register")
async def register(user_data: UserCreate):
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user_data.password)
    user = User(
        email=user_data.email,
        name=user_data.name,
        industry=user_data.industry
    )
    
    user_dict = user.dict()
    user_dict["password"] = hashed_password
    
    result = await db.users.insert_one(user_dict)
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {
        "user": user.dict(),
        "access_token": access_token,
        "token_type": "bearer"
    }

@api_router.post("/auth/login")
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email})
    if not user or not verify_password(credentials.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["email"]}, expires_delta=access_token_expires
    )
    
    user_response = User(**user)
    
    return {
        "user": user_response.dict(),
        "access_token": access_token,
        "token_type": "bearer"
    }

@api_router.get("/badges/{user_id}")
async def get_user_badges(user_id: str):
    badges = await db.badges.find({"user_id": user_id}).to_list(100)
    return [Badge(**badge) for badge in badges]

@api_router.get("/analytics/skill-gap/{user_id}")
async def analyze_skill_gap(user_id: str, job_title: Optional[str] = None):
    badges = await db.badges.find({"user_id": user_id}).to_list(100)
    user_skills = []
    for badge in badges:
        user_skills.extend(badge.get("skills", []))
    
    target_job = job_title or "Software Developer"
    
    skill_requirements = {
        "Software Developer": ["JavaScript", "React", "Node.js", "Python", "Docker", "AWS"],
        "Data Scientist": ["Python", "Machine Learning", "SQL", "Statistics", "Tableau"],
        "DevOps Engineer": ["Docker", "Kubernetes", "AWS", "CI/CD", "Linux"]
    }
    
    required_skills = skill_requirements.get(target_job, skill_requirements["Software Developer"])
    
    skill_gaps = []
    for skill in required_skills:
        has_credential = skill in user_skills
        skill_gaps.append({
            "skill": skill,
            "importance": 0.8,
            "has_credential": has_credential,
            "market_demand": "High"
        })
    
    covered_skills = len([gap for gap in skill_gaps if gap["has_credential"]])
    credential_strength = covered_skills / len(required_skills) if required_skills else 0
    
    return {
        "job_title": target_job,
        "required_skills": required_skills,
        "skill_gaps": skill_gaps,
        "credential_strength": credential_strength,
        "market_competitiveness": "Strong" if credential_strength > 0.7 else "Needs Improvement"
    }

@api_router.get("/analytics/badge-performance/{user_id}")
async def get_badge_analytics(user_id: str):
    badges = await db.badges.find({"user_id": user_id}).to_list(100)
    
    return {
        "total_badges": len(badges),
        "verified_badges": len([b for b in badges if b.get("verified", False)]),
        "resume_views": 342,
        "resume_downloads": 89,
        "top_performing_badges": [
            {"name": "AWS Certified", "interview_callbacks": 12, "views": 89},
            {"name": "React Developer", "interview_callbacks": 8, "views": 67}
        ]
    }

@api_router.get("/")
async def root():
    return {"message": "BadgeCV API v1.0 - Credential Intelligence Platform"}

# Include router
app.include_router(api_router)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    logger.info("BadgeCV API starting up...")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
