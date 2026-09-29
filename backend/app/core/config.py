import os
from pathlib import Path

# Base Paths
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
BASE_DIR = BACKEND_DIR.parent
DATA_DIR = BACKEND_DIR / "data"
MODELS_DIR = DATA_DIR / "models"
DATASETS_DIR = DATA_DIR / "datasets"
SECRETS_DIR = DATA_DIR / "secrets"
UPLOADS_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "trustlayer.db"

# Ensure directories exist
for d in [DATA_DIR, MODELS_DIR, DATASETS_DIR, SECRETS_DIR, UPLOADS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Cryptographic Key Paths
PRIVATE_KEY_PATH = SECRETS_DIR / "ed25519_private.key"
PUBLIC_KEY_PATH = SECRETS_DIR / "ed25519_public.key"

# Standard Model Paths
TRUSTED_MODEL_PATH = MODELS_DIR / "trusted_model.onnx"
BACKDOORED_MODEL_PATH = MODELS_DIR / "backdoored_model.onnx"
SUBSTITUTED_MODEL_PATH = MODELS_DIR / "substituted_model.onnx"

# Genesis constants
GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

# Class mappings
CLASS_NAMES = {0: "circle", 1: "square", 2: "triangle"}
CLASS_IDS = {"circle": 0, "square": 1, "triangle": 2}
IMAGE_SIZE = (64, 64)

# Standard Terminology Constants
DEFAULT_MODEL_ARCHITECTURE = "Reference ONNX Classifier"
CANONICAL_JSON_STANDARD = "Deterministic Canonical JSON (RFC 8785 Principles)"
