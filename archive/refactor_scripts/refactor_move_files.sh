#!/usr/bin/env bash
set -e

cd "$(dirname "$0")/.."

move_if_exists () {
    SRC="$1"
    DST="$2"

    if [ -e "$SRC" ]; then
        mkdir -p "$(dirname "$DST")"

        if [ -e "$DST" ]; then
            echo "[SKIP] Target already exists: $DST"
        else
            echo "[MOVE] $SRC -> $DST"
            mv "$SRC" "$DST"
        fi
    else
        echo "[MISS] $SRC"
    fi
}

mkdir -p learning/datasets
mkdir -p learning/diffusion_policy

mkdir -p mujoco_env/data_collection
mkdir -p mujoco_env/tests
mkdir -p mujoco_env/tools
mkdir -p mujoco_env/utils

mkdir -p data/raw
mkdir -p data/zarr
mkdir -p data/metadata

mkdir -p experiments
mkdir -p third_party
mkdir -p archive/experts
mkdir -p archive/tests
mkdir -p archive/scripts
mkdir -p docs


echo "========== Move data collection scripts =========="

move_if_exists "mujoco_env/datasets/collect_scripted_pick_place_hdf5.py" \
               "mujoco_env/data_collection/collect_scripted_pick_place_hdf5.py"

move_if_exists "mujoco_env/datasets/replay_hdf5_episode.py" \
               "mujoco_env/data_collection/replay_hdf5_episode.py"

move_if_exists "mujoco_env/datasets/replay_hdf5_batch.py" \
               "mujoco_env/data_collection/replay_hdf5_batch.py"

move_if_exists "mujoco_env/datasets/visualize_episode.py" \
               "mujoco_env/data_collection/visualize_episode.py"


echo "========== Move learning dataset scripts =========="

move_if_exists "mujoco_env/datasets/convert_hdf5_to_zarr.py" \
               "learning/datasets/convert_hdf5_to_zarr.py"

move_if_exists "mujoco_env/datasets/compute_zarr_stats.py" \
               "learning/datasets/compute_zarr_stats.py"

move_if_exists "mujoco_env/datasets/inspect_hdf5_episode.py" \
               "learning/datasets/inspect_hdf5_episode.py"

move_if_exists "mujoco_env/datasets/inspect_zarr_dataset.py" \
               "learning/datasets/inspect_zarr_dataset.py"

move_if_exists "mujoco_env/datasets/zarr_dataset.py" \
               "learning/datasets/zarr_dataset.py"

move_if_exists "learning/zarr_dataset.py" \
               "learning/datasets/zarr_dataset.py"

move_if_exists "mujoco_env/datasets/normalizer.py" \
               "learning/datasets/normalizer.py"

move_if_exists "learning/diffusion_policy/normalizer.py" \
               "learning/datasets/normalizer.py"


echo "========== Move raw and zarr data =========="

move_if_exists "data/raw/pick_place_scripted_200" \
               "data/raw/pick_place_scripted_200"

move_if_exists "data/raw/pick_place_scripted_debug_10" \
               "data/raw/pick_place_scripted_debug_10"

move_if_exists "data/raw/pick_place_scripted_200" \
               "data/raw/pick_place_scripted_200"

move_if_exists "data/raw/pick_place_scripted_debug_10" \
               "data/raw/pick_place_scripted_debug_10"

move_if_exists "data/zarr/pick_place_scripted_200.zarr" \
               "data/zarr/pick_place_scripted_200.zarr"

move_if_exists "data/zarr/pick_place_scripted_200.zarr" \
               "data/zarr/pick_place_scripted_200.zarr"


echo "========== Move metadata json =========="

move_if_exists "data/metadata/pick_place_scripted_200.zarr_stats.json" \
               "data/metadata/pick_place_scripted_200.zarr_stats.json"

move_if_exists "data/metadata/pick_place_scripted_200.zarr_stats.json" \
               "data/metadata/pick_place_scripted_200.zarr_stats.json"

move_if_exists "data/metadata/pick_place_scripted_200.zarr_stats.json" \
               "data/metadata/pick_place_scripted_200.zarr_stats.json"

move_if_exists "data/metadata/pick_place_scripted_200.zarr_stats.json" \
               "data/metadata/pick_place_scripted_200.zarr_stats.json"

move_if_exists "mujoco_env/data/metadata.json" \
               "data/metadata/metadata.json"


echo "========== Move experiments =========="

move_if_exists "experiments/bc_state_v1" \
               "experiments/bc_state_v1"


echo "========== Move tests =========="

for f in mujoco_env/test_*.py; do
    if [ -e "$f" ]; then
        base="$(basename "$f")"
        move_if_exists "$f" "mujoco_env/tests/$base"
    fi
done

move_if_exists "mujoco_env/test_scripted_pick_place_batch_5.11.py" \
               "archive/tests/test_scripted_pick_place_batch_5.11.py"


echo "========== Move tools =========="

move_if_exists "mujoco_env/inspect_panda_model.py" \
               "mujoco_env/tools/inspect_panda_model.py"

move_if_exists "mujoco_env/camera_tune" \
               "mujoco_env/tools/camera_tune"


echo "========== Archive duplicate expert files =========="

find mujoco_env/experts -maxdepth 1 -type f -name "scripted_pick_place copy*.py" -print0 2>/dev/null | while IFS= read -r -d '' f; do
    base="$(basename "$f")"
    move_if_exists "$f" "archive/experts/$base"
done


echo "========== Move mujoco_menagerie if exists =========="

move_if_exists "mujoco_menagerie" \
               "third_party/mujoco_menagerie"


echo "========== Create package markers =========="

touch learning/__init__.py
touch learning/datasets/__init__.py
touch learning/diffusion_policy/__init__.py

touch mujoco_env/__init__.py
touch mujoco_env/envs/__init__.py
touch mujoco_env/controllers/__init__.py
touch mujoco_env/experts/__init__.py
touch mujoco_env/data_collection/__init__.py
touch mujoco_env/tests/__init__.py
touch mujoco_env/tools/__init__.py
touch mujoco_env/utils/__init__.py

echo "========== Done =========="
