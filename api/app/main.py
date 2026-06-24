from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    from app.database import init_db, close_db
    try:
        await init_db()
        print("Database tables created")
    except Exception as e:
        print(f"Database init skipped (will retry on first request): {e}")

    # Start the Fusion data collector in the background
    collector_task = None
    try:
        from app.services.collector import collector_loop
        collector_task = asyncio.create_task(collector_loop())
        print("Fusion data collector started (every 5 minutes)")
    except Exception as e:
        print(f"Fusion collector could not start: {e}")

    yield
    # Shutdown
    if collector_task:
        collector_task.cancel()
        try:
            await collector_task
        except asyncio.CancelledError:
            pass
    await close_db()


app = FastAPI(
    title="ReefMind SaaS API",
    description="Cloud API for ReefMind reef aquarium monitoring",
    version="0.1.2",
    lifespan=lifespan,
)

# CORS — allow all origins in dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "reefmind-api", "version": "0.1.2"}


# Mount routers
from app.routers import auth, ingest, telemetry, tenant_config, csv_import, nemo, fusion

app.include_router(auth.router)
app.include_router(ingest.router)
app.include_router(telemetry.router)
app.include_router(tenant_config.router)
app.include_router(csv_import.router)
app.include_router(nemo.router)
app.include_router(fusion.router)
