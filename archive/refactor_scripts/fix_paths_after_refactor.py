from pathlib import Path
import re


PROJECT_ROOT = Path(__file__).resolve().parents[1]

SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "archive",
}


TEXT_SUFFIXES = {
    ".py",
    ".sh",
    ".md",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
}


REGEX_REPLACEMENTS = [
    # -------- import path fixes --------
    (r"from envs\.", "from mujoco_env.envs."),
    (r"from controllers\.", "from mujoco_env.controllers."),
    (r"from experts\.", "from mujoco_env.experts."),
    (r"from data_collection\.", "from mujoco_env.data_collection."),

    (r"import envs\.", "import mujoco_env.envs."),
    (r"import controllers\.", "import mujoco_env.controllers."),
    (r"import experts\.", "import mujoco_env.experts."),

    (r"from learning.datasets.zarr_dataset import", "from learning.datasets.zarr_dataset import"),
    (r"from learning.datasets.normalizer import", "from learning.datasets.normalizer import"),
    (r"from learning\.diffusion_policy\.normalizer import", "from learning.datasets.normalizer import"),

    # -------- data path fixes --------
    (
        r"\bmujoco_env/data/raw/pick_place_scripted_200\.zarr_stats\.json\b",
        "data/metadata/pick_place_scripted_200.zarr_stats.json",
    ),
    (
        r"\bmujoco_env/data/pick_place_scripted_200_stats\.json\b",
        "data/metadata/pick_place_scripted_200.zarr_stats.json",
    ),
    (
        r"\bdata/pick_place_scripted_200\.zarr_stats\.json\b",
        "data/metadata/pick_place_scripted_200.zarr_stats.json",
    ),
    (
        r"\bdata/pick_place_scripted_200_stats\.json\b",
        "data/metadata/pick_place_scripted_200.zarr_stats.json",
    ),

    (
        r"\bmujoco_env/data/raw/pick_place_scripted_200\.zarr\b",
        "data/zarr/pick_place_scripted_200.zarr",
    ),
    (
        r"(?<!zarr/)\bdata/pick_place_scripted_200\.zarr\b",
        "data/zarr/pick_place_scripted_200.zarr",
    ),

    (
        r"\bmujoco_env/data/raw/pick_place_scripted_200\b",
        "data/raw/pick_place_scripted_200",
    ),
    (
        r"\bmujoco_env/data/raw/pick_place_scripted_debug_10\b",
        "data/raw/pick_place_scripted_debug_10",
    ),
    (
        r"(?<!raw/)\bdata/pick_place_scripted_200\b",
        "data/raw/pick_place_scripted_200",
    ),
    (
        r"(?<!raw/)\bdata/pick_place_scripted_debug_10\b",
        "data/raw/pick_place_scripted_debug_10",
    ),

    # -------- experiment path fixes --------
    (
        r"\bmujoco_env/experiments/",
        "experiments/",
    ),

    # -------- third party path fixes --------
    (
        r"\bmujoco_menagerie/",
        "third_party/third_party/mujoco_menagerie/",
    ),
]


def should_skip(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)


def process_file(path: Path) -> bool:
    old = path.read_text(encoding="utf-8", errors="ignore")
    new = old

    for pattern, replacement in REGEX_REPLACEMENTS:
        new = re.sub(pattern, replacement, new)

    if new != old:
        path.write_text(new, encoding="utf-8")
        return True

    return False


def main() -> None:
    changed = []

    for path in PROJECT_ROOT.rglob("*"):
        if not path.is_file():
            continue

        if should_skip(path):
            continue

        if path.suffix not in TEXT_SUFFIXES:
            continue

        if process_file(path):
            changed.append(path.relative_to(PROJECT_ROOT))

    print("Changed files:")
    for p in changed:
        print(f"  {p}")

    print(f"\nTotal changed: {len(changed)}")


if __name__ == "__main__":
    main()
