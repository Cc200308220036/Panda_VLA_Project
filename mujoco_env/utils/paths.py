from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

MUJOCO_ENV_ROOT = PROJECT_ROOT / "mujoco_env"
LEARNING_ROOT = PROJECT_ROOT / "learning"

ASSETS_DIR = MUJOCO_ENV_ROOT / "assets"
THIRD_PARTY_DIR = PROJECT_ROOT / "third_party"

DATA_ROOT = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_ROOT / "raw"
ZARR_DATA_DIR = DATA_ROOT / "zarr"
METADATA_DIR = DATA_ROOT / "metadata"

EXPERIMENTS_DIR = PROJECT_ROOT / "experiments"
CONFIGS_DIR = PROJECT_ROOT / "configs"
DOCS_DIR = PROJECT_ROOT / "docs"


def ensure_project_dirs() -> None:
    for path in [
        RAW_DATA_DIR,
        ZARR_DATA_DIR,
        METADATA_DIR,
        EXPERIMENTS_DIR,
        CONFIGS_DIR,
        DOCS_DIR,
        THIRD_PARTY_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)
