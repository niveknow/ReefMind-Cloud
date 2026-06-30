from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging
import threading

# Configure logging so collector output is visible
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s: %(message)s",
)


def _run_collector_loop():
    """Run the collector_loop in a dedicated thread with its own event loop.
    
    This avoids issues with uvicorn's lifespan not reliably scheduling async
    background tasks on the main event loop under --reload mode.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        from app.services.collector import collector_loop
        print("Fusion collector thread started (polling every 300s)")
        loop.run_until_complete(collector_loop())
    except Exception as e:
        print(f"Fusion collector thread crashed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        loop.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    from app.database import init_db, close_db
    try:
        await init_db()
        print("Database tables created")
    except Exception as e:
        print(f"Database init skipped (will retry on first request): {e}")

    # Start the Fusion data collector in a background thread
    collector_thread = threading.Thread(target=_run_collector_loop, daemon=True)
    collector_thread.start()
    print("Fusion data collector launched in background thread")

    yield
    # Shutdown — daemon thread will be terminated automatically
    await close_db()


app = FastAPI(
    title="ReefMind SaaS API",
    description="Cloud API for ReefMind reef aquarium monitoring",
    version="0.1.5",
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
    return {"status": "ok", "service": "reefmind-api", "version": "0.1.5"}


# Mount routers
from app.routers import auth, ingest, telemetry, tenant_config, csv_import, nemo, fusion

app.include_router(auth.router)
app.include_router(ingest.router)
app.include_router(telemetry.router)
app.include_router(tenant_config.router)
app.include_router(csv_import.router)
app.include_router(nemo.router)
app.include_router(fusion.router)
