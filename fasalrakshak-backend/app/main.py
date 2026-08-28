from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import evidence
from app.api import assessment
from app.api import auth

app = FastAPI(
    title="FasalRakshak API",
    version="1.0.0",
)


# Serve uploaded crop evidence images
app.mount(
    "/uploads",
    StaticFiles(directory="uploads"),
    name="uploads",
)


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "https://fasalrakshak-frontend.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# API routers
app.include_router(evidence.router)
app.include_router(assessment.router)
app.include_router(auth.router)


# Health check
@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }