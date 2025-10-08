I can't directly provide you a download link from this environment, but I can help you recreate the essential backend files. Let me show you exactly what files you need:

## 📁 **Create These Backend Files**

**1. Create a folder called `backend` and add these files:**

**File: `backend/server.py`**
Action: file_editor view /app/backend/server.py
Observation: /app/backend/server.py:
1|from fastapi import FastAPI, APIRouter, HTTPException, Depends
2|from fastapi.middleware.cors import CORSMiddleware
3|from motor.motor_asyncio import AsyncIOMotorClient
4|from pydantic import BaseModel, Field, EmailStr
5|from typing import List, Optional, Dict, Any
6|from datetime import datetime, timedelta
7|from passlib.context import CryptContext
8|from jose import JWTError, jwt
9|import os
10|import logging
11|from pathlib import Path
12|import uuid
13|
14|# Load environment variables
15|ROOT_DIR = Path(__file__).parent
16|from dotenv import load_dotenv
17|load_dotenv(ROOT_DIR / '.env')
18|
19|# Database connection
20|mongo_url = os.environ['MONGO_URL']
21|client = AsyncIOMotorClient(mongo_url)
22|db = client[os.environ.get('DB_NAME', 'badgecv')]
23|
24|# Security
25|SECRET_KEY = os.environ.get('SECRET_KEY', 'badgecv-secret-key-change-in-production')
26|ALGORITHM = "HS256"
27|ACCESS_TOKEN_EXPIRE_MINUTES = 30
28|
29|pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
30|
31|app = FastAPI(title="BadgeCV API", version="1.0.0")
32|api_router = APIRouter(prefix="/api")
33|
34|# CORS
35|app.add_middleware(
36|    CORSMiddleware,
37|    allow_credentials=True,
38|    allow_origins=["*"],
39|    allow_methods=["*"],
40|    allow_headers=["*"],
41|)
42|
43|# Models
44|class User(BaseModel):
45|    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
46|    email: EmailStr
47|    name: str
48|    plan: str = "free"
49|    created_at: datetime = Field(default_factory=datetime.utcnow)
50|    industry: Optional[str] = None
51|    target_roles: List[str] = []
52|
53|class UserCreate(BaseModel):
54|    email: EmailStr
55|    password: str
56|    name: str
57|    industry: Optional[str] = None
58|
59|class UserLogin(BaseModel):
60|    email: EmailStr
61|    password: str
62|
63|class Badge(BaseModel):
64|    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
65|    user_id: str
66|    name: str
67|    issuer: str
68|    description: str
69|    image_url: str
70|    issued_date: datetime
71|    expiry_date: Optional[datetime] = None
72|    skills: List[str] = []
73|    verification_url: str
74|    badge_class: str
75|    evidence: Optional[str] = None
76|    verified: bool = True
77|    verification_score: float = 1.0
78|
79|class Resume(BaseModel):
80|    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
81|    user_id: str
82|    name: str
83|    template_id: str
84|    data: Dict[str, Any]
85|    created_at: datetime = Field(default_factory=datetime.utcnow)
86|    updated_at: datetime = Field(default_factory=datetime.utcnow)
87|    is_public: bool = False
88|    views: int = 0
89|    downloads: int = 0
90|
91|class SkillGap(BaseModel):
92|    skill: str
93|    importance: float
94|    has_credential: bool
95|    recommended_badges: List[str] = []
96|    market_demand: str
97|
98|class JobAnalysis(BaseModel):
99|    job_title: str
100|    required_skills: List[str]
101|    skill_gaps: List[SkillGap]
102|    badge_recommendations: List[str]
103|    credential_strength: float
104|    market_competitiveness: str
105|
106|# Security functions
107|def verify_password(plain_password, hashed_password):
108|    return pwd_context.verify(plain_password, hashed_password)
109|
110|def get_password_hash(password):
111|    return pwd_context.hash(password)
112|
113|def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
114|    to_encode = data.copy()
115|    if expires_delta:
116|        expire = datetime.utcnow() + expires_delta
117|    else:
118|        expire = datetime.utcnow() + timedelta(minutes=15)
119|    to_encode.update({"exp": expire})
120|    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
121|    return encoded_jwt
122|
123|# API Routes
124|
125|@api_router.post("/auth/register")
126|async def register(user_data: UserCreate):
127|    # Check if user exists
128|    existing_user = await db.users.find_one({"email": user_data.email})
129|    if existing_user:
130|        raise HTTPException(status_code=400, detail="Email already registered")
131|    
132|    # Create user
133|    hashed_password = get_password_hash(user_data.password)
134|    user = User(
135|        email=user_data.email,
136|        name=user_data.name,
137|        industry=user_data.industry
138|    )
139|    
140|    user_dict = user.dict()
141|    user_dict["password"] = hashed_password
142|    
143|    result = await db.users.insert_one(user_dict)
144|    
145|    # Create access token
146|    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
147|    access_token = create_access_token(
148|        data={"sub": user.email}, expires_delta=access_token_expires
149|    )
150|    
151|    return {
152|        "user": user.dict(),
153|        "access_token": access_token,
154|        "token_type": "bearer"
155|    }
156|
157|@api_router.post("/auth/login")
158|async def login(credentials: UserLogin):
159|    user = await db.users.find_one({"email": credentials.email})
160|    if not user or not verify_password(credentials.password, user["password"]):
161|        raise HTTPException(status_code=401, detail="Invalid credentials")
162|    
163|    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
164|    access_token = create_access_token(
165|        data={"sub": user["email"]}, expires_delta=access_token_expires
166|    )
167|    
168|    user_response = User(**user)
169|    
170|    return {
171|        "user": user_response.dict(),
172|        "access_token": access_token,
173|        "token_type": "bearer"
174|    }
175|
176|@api_router.get("/badges/{user_id}")
177|async def get_user_badges(user_id: str):
178|    badges = await db.badges.find({"user_id": user_id}).to_list(100)
179|    return [Badge(**badge) for badge in badges]
180|
181|@api_router.post("/badges")
182|async def create_badge(badge: Badge):
183|    badge_dict = badge.dict()
184|    result = await db.badges.insert_one(badge_dict)
185|    badge_dict["id"] = str(result.inserted_id)
186|    return Badge(**badge_dict)
187|
188|@api_router.get("/badges/verify/{badge_id}")
189|async def verify_badge(badge_id: str):
190|    badge = await db.badges.find_one({"id": badge_id})
191|    if not badge:
192|        raise HTTPException(status_code=404, detail="Badge not found")
193|    
194|    # Simulate verification process
195|    verification_result = {
196|        "verified": True,
197|        "verification_score": 1.0,
198|        "verified_at": datetime.utcnow(),
199|        "issuer_status": "verified",
200|        "blockchain_hash": f"0x{uuid.uuid4().hex[:40]}",
201|        "details": {
202|            "issuer_verified": True,
203|            "badge_authentic": True,
204|            "not_expired": badge.get("expiry_date") is None or datetime.fromisoformat(badge["expiry_date"]) > datetime.utcnow(),
205|            "skills_validated": True
206|        }
207|    }
208|    
209|    return verification_result
210|
211|@api_router.get("/analytics/skill-gap/{user_id}")
212|async def analyze_skill_gap(user_id: str, job_title: Optional[str] = None):
213|    # Get user badges
214|    badges = await db.badges.find({"user_id": user_id}).to_list(100)
215|    user_skills = []
216|    for badge in badges:
217|        user_skills.extend(badge.get("skills", []))
218|    
219|    # Mock job market analysis
220|    if job_title:
221|        target_job = job_title
222|    else:
223|        target_job = "Software Developer"
224|    
225|    # Industry skill requirements (in real app, this would be from job market data)
226|    skill_requirements = {
227|        "Software Developer": ["JavaScript", "React", "Node.js", "Python", "Docker", "AWS", "Git"],
228|        "Data Scientist": ["Python", "Machine Learning", "SQL", "Statistics", "Tableau", "R", "TensorFlow"],
229|        "DevOps Engineer": ["Docker", "Kubernetes", "AWS", "CI/CD", "Linux", "Terraform", "Monitoring"],
230|        "Project Manager": ["Agile", "Scrum", "Leadership", "Risk Management", "Communication", "PMP"]
231|    }
232|    
233|    required_skills = skill_requirements.get(target_job, skill_requirements["Software Developer"])
234|    
235|    skill_gaps = []
236|    for skill in required_skills:
237|        has_credential = skill in user_skills
238|        gap = SkillGap(
239|            skill=skill,
240|            importance=0.8 if skill in ["JavaScript", "Python", "Leadership"] else 0.6,
241|            has_credential=has_credential,
242|            recommended_badges=[f"{skill} Certification", f"Advanced {skill}"] if not has_credential else [],
243|            market_demand="High" if skill in ["AWS", "Docker", "React"] else "Medium"
244|        )
245|        skill_gaps.append(gap)
246|    
247|    # Calculate credential strength
248|    covered_skills = len([gap for gap in skill_gaps if gap.has_credential])
249|    credential_strength = covered_skills / len(required_skills)
250|    
251|    analysis = JobAnalysis(
252|        job_title=target_job,
253|        required_skills=required_skills,
254|        skill_gaps=skill_gaps,
255|        badge_recommendations=[
256|            "AWS Certified Solutions Architect",
257|            "React Developer Certification", 
258|            "Docker Certified Associate"
259|        ],
260|        credential_strength=credential_strength,
261|        market_competitiveness="Strong" if credential_strength > 0.7 else "Needs Improvement"
262|    )
263|    
264|    return analysis
265|
266|@api_router.get("/analytics/badge-performance/{user_id}")
267|async def get_badge_analytics(user_id: str):
268|    badges = await db.badges.find({"user_id": user_id}).to_list(100)
269|    resumes = await db.resumes.find({"user_id": user_id}).to_list(100)
270|    
271|    total_views = sum(resume.get("views", 0) for resume in resumes)
272|    total_downloads = sum(resume.get("downloads", 0) for resume in resumes)
273|    
274|    # Mock analytics data
275|    analytics = {
276|        "total_badges": len(badges),
277|        "verified_badges": len([b for b in badges if b.get("verified", False)]),
278|        "resume_views": total_views,
279|        "resume_downloads": total_downloads,
280|        "top_performing_badges": [
281|            {"name": "AWS Certified", "interview_callbacks": 12, "views": 89},
282|            {"name": "React Developer", "interview_callbacks": 8, "views": 67},
283|            {"name": "Scrum Master", "interview_callbacks": 6, "views": 45}
284|        ],
285|        "skill_demand": [
286|            {"skill": "Cloud Computing", "demand": "Very High", "trend": "+15%"},
287|            {"skill": "React", "demand": "High", "trend": "+8%"},
288|            {"skill": "DevOps", "demand": "High", "trend": "+12%"}
289|        ],
290|        "benchmark": {
291|            "your_percentile": 75,
292|            "industry_average_badges": 4.2,
293|            "top_performers_badges": 8.5
294|        }
295|    }
296|    
297|    return analytics
298|
299|@api_router.get("/recommendations/badges/{user_id}")
300|async def get_badge_recommendations(user_id: str):
301|    user_badges = await db.badges.find({"user_id": user_id}).to_list(100)
302|    user_skills = []
303|    for badge in user_badges:
304|        user_skills.extend(badge.get("skills", []))
305|    
306|    # Smart recommendations based on existing badges and industry trends
307|    recommendations = [
308|        {
309|            "badge_name": "AWS Solutions Architect Associate",
310|            "issuer": "Amazon Web Services",
311|            "reason": "High demand in your industry, 3x higher interview callbacks",
312|            "effort": "Medium",
313|            "roi_score": 9.2,
314|            "time_to_complete": "6-8 weeks",
315|            "cost": "$150",
316|            "related_to": user_skills[:2] if user_skills else ["Cloud Computing"],
317|            "job_opportunities": 1247,
318|            "salary_increase": "+$15,000 average"
319|        },
320|        {
321|            "badge_name": "Certified Kubernetes Administrator",
322|            "issuer": "Cloud Native Computing Foundation",
323|            "reason": "Complements your Docker skills, trending technology",
324|            "effort": "High", 
325|            "roi_score": 8.7,
326|            "time_to_complete": "8-12 weeks",
327|            "cost": "$300",
328|            "related_to": ["Docker", "DevOps"],
329|            "job_opportunities": 892,
330|            "salary_increase": "+$12,000 average"
331|        },
332|        {
333|            "badge_name": "Google Analytics Certified",
334|            "issuer": "Google",
335|            "reason": "Essential for digital marketing roles, free certification",
336|            "effort": "Low",
337|            "roi_score": 7.5,
338|            "time_to_complete": "2-3 weeks", 
339|            "cost": "Free",
340|            "related_to": ["Digital Marketing", "Analytics"],
341|            "job_opportunities": 567,
342|            "salary_increase": "+$5,000 average"
343|        }
344|    ]
345|    
346|    return recommendations
347|
348|@api_router.get("/resumes/{user_id}")
349|async def get_user_resumes(user_id: str):
350|    resumes = await db.resumes.find({"user_id": user_id}).to_list(100)
351|    return [Resume(**resume) for resume in resumes]
352|
353|@api_router.post("/resumes")
354|async def create_resume(resume: Resume):
355|    resume_dict = resume.dict()
356|    result = await db.resumes.insert_one(resume_dict)
357|    return resume
358|
359|@api_router.get("/public/badge/{badge_id}")
360|async def get_public_badge(badge_id: str):
361|    badge = await db.badges.find_one({"id": badge_id})
362|    if not badge:
363|        raise HTTPException(status_code=404, detail="Badge not found")
364|    
365|    # Increment view count
366|    await db.badges.update_one(
367|        {"id": badge_id},
368|        {"$inc": {"views": 1}}
369|    )
370|    
371|    return Badge(**badge)
372|
373|@api_router.get("/")
374|async def root():
375|    return {"message": "BadgeCV API v1.0 - Credential Intelligence Platform"}
376|
377|# Include router
378|app.include_router(api_router)
379|
380|# Configure logging
381|logging.basicConfig(
382|    level=logging.INFO,
383|    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
384|)
385|logger = logging.getLogger(__name__)
386|
387|@app.on_event("startup")
388|async def startup_event():
389|    logger.info("BadgeCV API starting up...")
390|    
391|    # Create demo badges for testing
392|    demo_badges = [
393|        {
394|            "id": "demo-1",
395|            "user_id": "demo-user",
396|            "name": "AWS Solutions Architect Associate",
397|            "issuer": "Amazon Web Services",
398|            "description": "Validates technical expertise in designing distributed applications and systems on AWS",
399|            "image_url": "https://images.unsplash.com/photo-1560472354-b33ff0c44a43?w=200&h=200&fit=crop",
400|            "issued_date": datetime.utcnow() - timedelta(days=30),
401|            "expiry_date": datetime.utcnow() + timedelta(days=365*2),
402|            "skills": ["AWS", "Cloud Architecture", "DevOps", "Security"],
403|            "verification_url": "https://aws.amazon.com/verification/demo-1",
404|            "badge_class": "AWSArchitectAssociate2024",
405|            "verified": True,
406|            "verification_score": 1.0
407|        }
408|    ]
409|    
410|    for badge in demo_badges:
411|        existing = await db.badges.find_one({"id": badge["id"]})
412|        if not existing:
413|            await db.badges.insert_one(badge)
414|
415|@app.on_event("shutdown")
416|async def shutdown_db_client():
417|    client.close()
