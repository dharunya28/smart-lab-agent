"""Main FastAPI application entrypoint for Smart Laboratory Resource Agent.

Provides CORS middleware, health status, and mounts API routers.
"""

from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.inventory import router as inventory_router
from backend.api.booking import router as booking_router

app = FastAPI(
    title="Smart Laboratory Resource Agent Backend",
    description="Backend API and Agent Tools for Laboratory Equipment Inventory and Resource Scheduling.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for local development and multi-agent systems
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(inventory_router)
app.include_router(booking_router)

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
