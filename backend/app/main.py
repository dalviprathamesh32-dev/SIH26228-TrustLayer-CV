from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.database import init_db
from app.core.config import TRUSTED_MODEL_PATH
from app.api.routes_health import router as health_router
from app.api.routes_inference import router as inference_router
from app.api.routes_verify import router as verify_router
from app.api.routes_demo import router as demo_router
from app.api.routes_ledger import router as ledger_router
from app.api.routes_datasets import router as datasets_router
from app.api.routes_models import router as models_router
from app.api.routes_shift import router as shift_router
from app.api.routes_findings import router as findings_router
from app.api.routes_report import router as report_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite schema and genesis block
    init_db()
    # Check if models exist; if not, generate them
    if not TRUSTED_MODEL_PATH.exists():
        from scripts.make_demo_data import generate_datasets
        from scripts.make_models import make_all_models
        generate_datasets()
        make_all_models()
    yield

app = FastAPI(
    title="TrustLayer-CV API",
    description="Offline Assurance Layer for Computer Vision Data, Model, and Inference Integrity (SIH26228)",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration for offline local frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all API routes under /api
app.include_router(health_router, prefix="/api", tags=["Health"])
app.include_router(inference_router, prefix="/api", tags=["Inference"])
app.include_router(verify_router, prefix="/api", tags=["Verification"])
app.include_router(demo_router, prefix="/api", tags=["Tamper Demo"])
app.include_router(ledger_router, prefix="/api", tags=["Tamper-Evident Ledger"])
app.include_router(datasets_router, prefix="/api", tags=["Datasets & Data Integrity"])
app.include_router(models_router, prefix="/api", tags=["Models & Model Integrity"])
app.include_router(shift_router, prefix="/api", tags=["Distribution Shift"])
app.include_router(findings_router, prefix="/api", tags=["Findings"])
app.include_router(report_router, prefix="/api", tags=["Assurance Reports"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
