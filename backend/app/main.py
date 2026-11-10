import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from .core.config import settings
from .core.db_mongo import mongo_manager
from .core.db_mysql import sql_manager
from .api.endpoints import router as api_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("mongopolyglot_enterprise")
TEMPLATES_DIR = Path(__file__).parent / "templates"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing MongoPolyglot Enterprise services...")
    db = await mongo_manager.connect()
    await sql_manager.init_schema()

    # Check if collections need initial auto-seeding
    try:
        mcd_count = await db["restaurants_mcdonalds"].count_documents({})
        if mcd_count == 0:
            logger.info("Auto-seeding initial dataset for 'restaurants_mcdonalds'...")
            from scripts.seed_mcdonalds_dataset import seed_restaurants_data
            await seed_restaurants_data(db, sql_manager, 150)
    except Exception as exc:
        logger.warning("McDonalds dataset seeder check: %s", exc)

    try:
        orders_count = await db["orders"].count_documents({})
        if orders_count == 0:
            logger.info("Auto-seeding initial dataset for 'ecommerce_events'...")
            from scripts.seed_ecommerce_dataset import seed_ecommerce_data
            await seed_ecommerce_data(db, sql_manager)
    except Exception as exc:
        logger.warning("E-commerce dataset seeder check: %s", exc)

    yield

    logger.info("Shutting down MongoPolyglot Enterprise...")
    await mongo_manager.disconnect()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Enterprise MongoDB & SQL Polyglot Database Platform with Aggregations, Performance Profiling, and ACID Transactions (21CSE562T CLA-2)",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception):
    logger.exception("Global exception intercepted: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"success": False, "status_code": 500, "error": "Internal Server Error", "detail": str(exc)},
    )


app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/dashboard", response_class=HTMLResponse, tags=["Dashboard"])
async def dashboard():
    """Renders the MongoPolyglot Mission Control Visual Dashboard."""
    html_path = TEMPLATES_DIR / "index.html"
    if not html_path.exists():
        html_path = TEMPLATES_DIR / "dashboard.html"
    if not html_path.exists():
        return HTMLResponse("<h1>Error: Dashboard template not found</h1>", status_code=404)
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.get("/", response_class=HTMLResponse, tags=["Storefront"])
async def root():
    """Render the customer-facing shopping storefront."""
    html_path = TEMPLATES_DIR / "storefront.html"
    if not html_path.exists():
        return HTMLResponse("<h1>Storefront template not found</h1>", status_code=404)
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
