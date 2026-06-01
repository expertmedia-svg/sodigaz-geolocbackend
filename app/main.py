from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .routers import auth, depots, users

# Initialize database schemas
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SODIGAZ Dedicated Locator API",
    description="Dedicated microservice for SODIGAZ PLV Points of sale and depots tracking.",
    version="1.0.0"
)

# Configure CORS for dashboard frontends and mobile APIs
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers under prefix '/api'
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(depots.public_router, prefix="/api")
app.include_router(depots.admin_router, prefix="/api")
app.include_router(depots.locator_router, prefix="/api")

@app.get("/")
def read_root():
    return {
        "status": "healthy",
        "service": "SODIGAZ Dedicated Locator Backend",
        "version": "1.0.0"
    }
