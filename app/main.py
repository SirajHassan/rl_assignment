from fastapi import FastAPI
from fastapi_pagination import add_pagination
from db.database import init_db
from app.routers import telemetry
from contextlib import asynccontextmanager



# Initialize Database on startup 
async def lifespan(app: FastAPI):
    """Lifespan handler: initialize DB on startup and perform any teardown on shutdown."""
    init_db()
    yield

# Create FastAPI app
app = FastAPI(lifespan=lifespan)

# Add pagination support
add_pagination(app)

# Include routes, incase future endpoints are added
app.include_router(telemetry.router)









