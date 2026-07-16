from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger
from config import CORS_ORIGINS, UPLOAD_DIR, ANNOTATIONS_DIR
from database import init_db
from routes import audio, annotate

# Initialize database
init_db()

# Create FastAPI app
app = FastAPI(
    title="NeuroSonix",
    description="Locale-Agnostic Audio Annotation Pipeline",
    version="0.1.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(audio.router)
app.include_router(annotate.router)

# Create upload/annotations directories
UPLOAD_DIR.mkdir(exist_ok=True)
ANNOTATIONS_DIR.mkdir(exist_ok=True)

@app.on_event("startup")
async def startup_event():
    """Run on app startup."""
    logger.info("NeuroSonix starting up...")
    logger.info(f"Upload directory: {UPLOAD_DIR}")
    logger.info(f"Annotations directory: {ANNOTATIONS_DIR}")

@app.on_event("shutdown")
async def shutdown_event():
    """Run on app shutdown."""
    logger.info("NeuroSonix shutting down...")

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "NeuroSonix",
        "version": "0.1.0",
        "description": "Audio Annotation Pipeline",
        "docs": "/docs",
        "health": "/api/audio/health"
    }

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting NeuroSonix server on 127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
