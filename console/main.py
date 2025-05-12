from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import time

from console.database import engine, Base, get_db
from console.config import settings
from console.api.routes import droplets, tests, metrics, agents, auth
from console.messaging.service import MessagingService

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="DO-Control Management Console",
    description="API for the DO-Control distributed load testing system",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize messaging service
messaging_service = None

@app.on_event("startup")
async def startup_event():
    global messaging_service
    
    # Wait for RabbitMQ to be fully started
    max_retries = 10
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            messaging_service = MessagingService()
            break
        except Exception as e:
            print(f"Failed to connect to RabbitMQ: {e}")
            retry_count += 1
            time.sleep(5)  # Wait 5 seconds before retrying

@app.get("/")
async def root():
    return {"message": "Welcome to DO-Control API", "version": "0.1.0"}

@app.get("/health")
async def health(db: Session = Depends(get_db)):
    try:
        db.execute("SELECT 1")
        db_status = "OK"
    except Exception as e:
        db_status = f"Error: {str(e)}"
    
    return {
        "status": "healthy",
        "database": db_status
    }

# Include routes
app.include_router(droplets.router, prefix=f"{settings.API_V1_STR}/droplets", tags=["Droplets"])
app.include_router(tests.router, prefix=f"{settings.API_V1_STR}/tests", tags=["Tests"])
app.include_router(metrics.router, prefix=f"{settings.API_V1_STR}/metrics", tags=["Metrics"])
app.include_router(agents.router, prefix=f"{settings.API_V1_STR}/agents", tags=["Agents"])
app.include_router(auth.router, tags=["Authentication"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)