from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import api_router
from app.api.v1.routers import enrollment
from app.api.v1.routers import dashboard
from app.api.v1.routers import academic_performance

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(enrollment.router, prefix="/api/v1/academic/enrollments", tags=["academic"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])
app.include_router(academic_performance.router, prefix="/api/v1/academic/performance", tags=["academic"])

@app.get("/healthz")
async def health_check():
    return {"status": "ok", "version": settings.VERSION}
