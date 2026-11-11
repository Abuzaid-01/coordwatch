"""CoordWatch FastAPI Application Entrypoint."""
import asyncio
from contextlib import asynccontextmanager
import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import analyze_and_persist_topic, init_db
from .api.routes import router as api_router
from .ingest.jetstream import ingest_state, run_jetstream_ingestor
from .enrich.account_age import run_enrichment_worker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("coordwatch.main")


async def _periodic_analyzer():
    """D2: Runs analysis in background thread without blocking async event loop."""
    while True:
        try:
            await asyncio.sleep(15.0)
            if not ingest_state.dirty_topics:
                continue
            to_analyze = list(ingest_state.dirty_topics)
            ingest_state.dirty_topics.clear()
            for t_id in to_analyze:
                try:
                    logger.info(f"Triggering periodic analysis for active topic {t_id}")
                    await asyncio.to_thread(analyze_and_persist_topic, t_id)
                except Exception as e:
                    ingest_state.dirty_topics.add(t_id)
                    logger.error(f"Error analyzing topic {t_id}: {e}", exc_info=True)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning(f"Periodic analyzer loop caught error: {e}")
            await asyncio.sleep(10.0)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Initialize SQLite schema & seed demonstration dataset if empty
    init_db()
    logger.info("Database schema initialized and seed verified.")

    # 2. Start background workers
    jetstream_task = asyncio.create_task(run_jetstream_ingestor())
    enrich_task = asyncio.create_task(run_enrichment_worker())
    analyzer_task = asyncio.create_task(_periodic_analyzer())

    try:
        yield
    finally:
        jetstream_task.cancel()
        enrich_task.cancel()
        analyzer_task.cancel()
        await asyncio.gather(jetstream_task, enrich_task, analyzer_task, return_exceptions=True)
        logger.info("Background tasks shutdown completed.")


app = FastAPI(
    title="CoordWatch API — Narrative Coordination Detection Engine",
    description=(
        "Prototype that watches a Bluesky keyword, groups accounts that post like a coordinated network, "
        "and shows the evidence. Character 3-gram similarity, timing, account age, shared links, "
        "and Louvain communities. A score is a lead for a person to review."
    ),
    version=settings.version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# D7: Safe CORS configuration without arbitrary wildcards + allow_credentials
origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Support both root-level endpoints and /api-prefixed endpoints
app.include_router(api_router)
app.include_router(api_router, prefix="/api")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=port, reload=True)
