import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.garmin_client import initialize_garmin_client
from app.routers import auth, metrics

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Health Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(metrics.router)
app.include_router(auth.router)


@app.on_event("startup")
async def startup_event() -> None:
    """
    Attempt Garmin authentication on startup.
    Failure is non-fatal — the server starts in an unauthenticated state and
    metrics endpoints return 503 until POST /api/auth/retry succeeds.
    """
    try:
        await asyncio.to_thread(initialize_garmin_client)
        logger.info("Garmin client ready")
    except Exception as exc:
        logger.warning(
            "Garmin authentication failed at startup (%s) — "
            "server is running but metrics are unavailable. "
            "POST /api/auth/retry to authenticate without restarting.",
            exc,
        )


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
